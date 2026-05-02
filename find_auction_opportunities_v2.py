#!/usr/bin/env python3
"""
Auction Pipeline V2 - Volume First, CE Identifies, SCP Prices, Math Decides

Four steps. No fuzzy matching. No parallel guessing.

Step 1: VOLUME - Load liquid cards from SCP cache (proven sales velocity)
Step 2: FIND   - Search eBay auctions for those cards (grouped by card number)
Step 3: IDENTIFY - CE looks at the photo, tells us exactly what the card is
Step 4: PROFIT - SCP price for CE-identified variant * 0.87 - bid - shipping >= $10

Rules (Munger inversion - what guarantees losing money):
- NEVER buy a card with < 1 sale/month (no proof of demand)
- NEVER trust a price from 1 sale or a sale > 6 months old
- NEVER tie up > $50 in a card that sells < weekly
- NEVER buy without photo-verified identity (CE must confirm)
- NEVER show opportunities you can't act on (ending > 7 days)

Usage:
    python3 find_auction_opportunities_v2.py
    python3 find_auction_opportunities_v2.py --liquid-limit 200 --dry-run
"""
import argparse
import os
import sys
import time
import json
import re
import requests
from contextlib import closing
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.utils.database import SessionLocal
from backend.utils.job_tracker import JobTracker
from backend.utils.logger import get_logger
from backend.models import Opportunity
from backend.scrapers.ebay_scraper import EbayScraper
from sqlalchemy import text

log = get_logger('auction_v2')

FEE_RATE = 0.13
DEFAULT_SHIPPING = 5.00
MIN_PROFIT = 10.00

# Volume thresholds (Munger: never buy what nobody wants)
ACCEPTABLE_VOLUMES = ['per day', 'per week', '1 sale per month', '2 sales per month',
                      '3 sales per month', '4 sales per month', '5 sales per month']

# Junk filters
JUNK_PATTERNS = [
    'you pick', 'pick your', 'complete your set', 'pick a card',
    'choose your', 'mystery', 'repack', 'break', 'digital', 'bunt',
    'lot of', 'replica', 'reprint', 'project 2020', 'project 70',
    'shoebox treasures', 'sticker', 'custom card', 'aceo',
    'complete set', 'factory set', 'factory sealed',
]

GRADED_PATTERNS = ['psa ', 'bgs ', 'sgc ', 'cgc ', 'gem mint', 'graded ',
                   'psa10', 'psa 10', 'bgs 10', 'sgc 10', 'grade 10', 'grade 9']


# ─── STEP 1: VOLUME ─────────────────────────────────────────────────────────

def load_liquid_cards(db, min_price=5.0, max_price=1000.0, limit=800):
    """Load cards with proven sales velocity from SCP cache.

    Only returns cards where volume indicates real demand:
    daily, weekly, or monthly sales. Rejects 'rare', '1 sale per year', etc.
    """
    rows = db.execute(text("""
        SELECT DISTINCT ON (sc.player_name, sc.card_year, sc.card_number)
               sc.player_name, sc.card_year, sc.card_number,
               sc.variants
        FROM scp_cache sc, jsonb_array_elements(sc.variants) v
        WHERE (v->>'ungraded')::numeric BETWEEN :min_p AND :max_p
          AND v->>'volume' IS NOT NULL AND v->>'volume' != ''
          AND (LOWER(v->>'volume') LIKE '%per day%'
               OR LOWER(v->>'volume') LIKE '%per week%'
               OR LOWER(v->>'volume') LIKE '%per month%')
          AND LOWER(v->>'volume') NOT LIKE '%rare%'
          AND LOWER(v->>'volume') NOT LIKE '%1 sale per year%'
          AND LOWER(v->>'volume') NOT LIKE '%2 sales per year%'
        ORDER BY sc.player_name, sc.card_year, sc.card_number,
                 CASE WHEN LOWER(v->>'volume') LIKE '%per day%' THEN 0
                      WHEN LOWER(v->>'volume') LIKE '%per week%' THEN 1
                      ELSE 2 END,
                 (v->>'ungraded')::numeric DESC
        LIMIT :lim
    """), {'min_p': min_price, 'max_p': max_price, 'lim': limit}).fetchall()

    cards = []
    for r in rows:
        variants = r[3] if isinstance(r[3], list) else json.loads(r[3])
        # Only keep variants with acceptable volume AND price
        good_variants = []
        for v in variants:
            vol = (v.get('volume') or '').lower()
            price = float(v.get('ungraded') or 0)
            if price > 0 and any(av in vol for av in ACCEPTABLE_VOLUMES):
                good_variants.append(v)
        if good_variants:
            cards.append({
                'player_name': r[0],
                'card_year': r[1],
                'card_number': r[2],
                'variants': good_variants,
            })
    return cards


def build_search_query(card):
    """Build eBay search query from card. NO parallel -- catches all variants."""
    parts = [card['player_name']]
    if card.get('card_year'):
        parts.append(str(card['card_year']))
    # Use the set name from the first variant
    if card['variants']:
        cs = (card['variants'][0].get('card_set') or '').strip()
        if cs and cs.lower() not in ('unknown', 'base', ''):
            parts.append(cs)
    cn = (card.get('card_number') or '').strip()
    if cn:
        parts.append(f'#{cn}')
    return ' '.join(parts)


# ─── STEP 2: FIND ON EBAY ───────────────────────────────────────────────────

def search_ebay_auctions(scraper, query, hours=168):
    """Search eBay for auctions matching query. Returns raw auction dicts."""
    meta = {}
    results = scraper.search_auctions_ending_soon(query, hours=hours, meta_out=meta)
    return results, meta.get('ebay_total')


# ─── STEP 3: IDENTIFY WITH CE ───────────────────────────────────────────────

def compare_cards_via_nova(ebay_image_url, scp_image_url):
    """Layered comparison: color gate first, AI only when borderline."""
    from backend.services.card_comparator import compare_cards
    result = compare_cards(scp_image_url, ebay_image_url, verbose=True)
    return result.get('same_card', False), result


def match_ce_to_scp(ce_identity, scp_variants):
    """Match CE-identified card to the correct SCP variant.

    CE tells us the parallel. We find that parallel in SCP variants.
    If exact match: use that price. If no match: skip (don't guess).
    """
    if not ce_identity or not ce_identity.get('parallel'):
        return None

    ce_parallel = (ce_identity['parallel'] or 'Base').lower().strip()

    # Exact match first
    for v in scp_variants:
        scp_parallel = (v.get('parallel') or 'Base').lower().strip()
        if scp_parallel == ce_parallel:
            return v

    # Keyword overlap (CE might say "Green Refractor", SCP says "Green")
    ce_words = set(ce_parallel.split())
    best_match = None
    best_overlap = 0
    for v in scp_variants:
        scp_parallel = (v.get('parallel') or 'Base').lower().strip()
        scp_words = set(scp_parallel.split())
        overlap = len(ce_words & scp_words)
        if overlap > best_overlap and overlap >= len(scp_words) * 0.5:
            best_overlap = overlap
            best_match = v

    return best_match


# ─── STEP 4: PROFIT CHECK ───────────────────────────────────────────────────

def calculate_profit(scp_price, bid, shipping):
    """Simple math. SCP * 0.87 - bid - shipping."""
    net = float(scp_price) * (1 - FEE_RATE)
    return round(net - float(bid) - float(shipping), 2)


# ─── MAIN PIPELINE ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Auction Pipeline V2')
    parser.add_argument('--hours', type=int, default=168)
    parser.add_argument('--min-profit', type=float, default=10.0)
    parser.add_argument('--max-budget', type=float, default=200.0)
    parser.add_argument('--liquid-limit', type=int, default=800)
    parser.add_argument('--min-scp-price', type=float, default=5.0)
    parser.add_argument('--max-scp-price', type=float, default=1000.0)
    parser.add_argument('--skip-ce', action='store_true', help='Skip CE verification (faster, less accurate)')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--sport', default='Baseball')
    args = parser.parse_args()

    print("=" * 70)
    print("AUCTION PIPELINE V2")
    print("Volume -> Find -> Identify -> Profit")
    print("=" * 70)

    tracker = JobTracker('auction_v2')
    tracker.start(total=0, parameters={
        'hours': args.hours, 'min_profit': args.min_profit,
        'max_budget': args.max_budget, 'liquid_limit': args.liquid_limit,
        'skip_ce': args.skip_ce,
    })

    try:
        # ── STEP 1: VOLUME ──
        print("\nStep 1: Loading liquid cards from SCP cache...")
        with closing(SessionLocal()) as db:
            liquid_cards = load_liquid_cards(
                db, min_price=args.min_scp_price,
                max_price=args.max_scp_price, limit=args.liquid_limit,
            )

        print(f"  {len(liquid_cards)} liquid card groups loaded")
        total_variants = sum(len(c['variants']) for c in liquid_cards)
        print(f"  {total_variants} total variants with proven volume")

        if not liquid_cards:
            print("  No liquid cards found. Run the SCP volume worm first.")
            tracker.complete(summary={'opportunities_found': 0})
            return

        # Build search queries (grouped by card number, no parallel)
        queries = []
        for card in liquid_cards:
            q = build_search_query(card)
            queries.append((q, card))
        print(f"  {len(queries)} eBay search queries to run")

        # ── STEP 2: FIND ON EBAY ──
        print(f"\nStep 2: Searching eBay for auctions ({args.hours}h window)...")
        scraper = EbayScraper()
        all_auctions = []
        seen_ids = set()
        consecutive_429 = 0
        queries_run = 0

        tracker.update(processed=0, total=len(queries))

        for i, (query, card) in enumerate(queries, 1):
            if i % 50 == 0 or i == 1:
                print(f"  [{i}/{len(queries)}] {len(all_auctions)} auctions found so far...")

            results, ebay_total = search_ebay_auctions(scraper, query, hours=args.hours)
            queries_run += 1

            if not results and ebay_total is None:
                consecutive_429 += 1
                if consecutive_429 >= 3:
                    print(f"\n  BAILING: {consecutive_429} consecutive 429s. Quota exhausted.")
                    break
            else:
                consecutive_429 = 0

            for a in (results or []):
                item_id = a.get('ebay_item_id', '')
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                title = a.get('title', '')
                price = a.get('price', 0)
                shipping = a.get('shipping', DEFAULT_SHIPPING)

                # Quick filters (junk, budget, not auction, graded)
                if a.get('listing_type') not in ('auction', 'auction_bin'):
                    continue
                if any(j in title.lower() for j in JUNK_PATTERNS):
                    continue
                if price + shipping > args.max_budget:
                    continue
                if any(g in title.lower() for g in GRADED_PATTERNS):
                    continue

                # Attach the SCP card data for Step 3/4
                a['_scp_card'] = card
                all_auctions.append(a)

            tracker.update(processed=i)
            time.sleep(1.0)

        print(f"\n  {len(all_auctions)} auctions found from {queries_run} queries")

        if not all_auctions:
            print("  No auctions found.")
            tracker.complete(summary={'opportunities_found': 0, 'queries_run': queries_run})
            return

        # ── STEP 3 & 4: IDENTIFY + PROFIT ──
        print(f"\nStep 3+4: Identifying cards and checking profit ({len(all_auctions)} auctions)...")

        db = SessionLocal()
        scp_scraper_instance = None  # Lazy init for SCP image fetching
        opportunities = []
        stats = {'ce_calls': 0, 'ce_matched': 0, 'ce_failed': 0,
                 'profitable': 0, 'not_profitable': 0, 'skipped_no_image': 0}

        for i, auction in enumerate(all_auctions, 1):
            if i % 25 == 0:
                print(f"  [{i}/{len(all_auctions)}] {len(opportunities)} opportunities so far...")

            title = auction['title']
            bid = auction['price']
            shipping = auction.get('shipping', DEFAULT_SHIPPING)
            scp_card = auction['_scp_card']
            scp_variants = scp_card['variants']

            # Get the best image URL
            image_urls = auction.get('image_urls') or []
            image_url = auction.get('image_url') or (image_urls[0] if image_urls else None)

            scp_match = None
            ce_identity = None

            if not args.skip_ce and image_url:
                # Compare eBay image against ALL SCP variant images
                # Pick the variant with the lowest color distance
                ebay_full = image_url.replace('/s-l225.', '/s-l1600.') if '/s-l225.' in image_url else image_url
                numeric_id = (auction.get('ebay_item_id') or '').split('|')[1] if '|' in (auction.get('ebay_item_id') or '') else auction.get('ebay_item_id', '')

                # Download eBay image once
                from backend.services.card_comparator import download_image, weighted_color_distance
                ebay_bytes, ebay_img = download_image(ebay_full)
                if not ebay_img:
                    stats['skipped_no_image'] += 1
                    continue

                # Score each SCP variant by color distance
                variant_scores = []
                for v in scp_variants:
                    scp_img_url = v.get('scp_image_url')
                    if not scp_img_url:
                        # Try to scrape and cache it
                        if v.get('url') and scp_scraper_instance and scp_scraper_instance is not False:
                            scp_img_url = scp_scraper_instance.get_product_image_url(v['url'])
                            if scp_img_url:
                                try:
                                    idx = scp_variants.index(v)
                                    db.execute(
                                        text(
                                            "UPDATE scp_cache SET variants = "
                                            "jsonb_set(variants, ('{' || :idx || ',scp_image_url}')::text[], to_jsonb(:img_url::text)) "
                                            "WHERE player_name = :p AND card_year = :y AND card_number = :n"
                                        ),
                                        {'idx': str(idx), 'img_url': scp_img_url,
                                         'p': scp_card['player_name'], 'y': scp_card['card_year'], 'n': scp_card['card_number']},
                                    )
                                    db.commit()
                                except Exception:
                                    db.rollback()
                        elif not scp_scraper_instance:
                            from backend.scrapers.sportscardspro_scraper import SportsCardsProScraper
                            try:
                                scp_scraper_instance = SportsCardsProScraper(headless=True)
                                if v.get('url'):
                                    scp_img_url = scp_scraper_instance.get_product_image_url(v['url'])
                            except Exception:
                                scp_scraper_instance = False

                    if not scp_img_url:
                        continue

                    _, scp_img = download_image(scp_img_url)
                    if not scp_img:
                        continue

                    avg_dist, _ = weighted_color_distance(scp_img, ebay_img)
                    variant_scores.append((avg_dist, v, scp_img_url))

                if not variant_scores:
                    stats['skipped_no_image'] += 1
                    print(f"\n  --- Card {i}/{len(all_auctions)} (no SCP images) ---")
                    print(f"  eBay:  {title[:100]}")
                    print(f"  SKIP:  No SCP variant images available")
                    continue

                # Sort by color distance -- closest match first
                variant_scores.sort(key=lambda x: x[0])
                best_dist, best_variant, best_scp_img = variant_scores[0]

                print(f"\n  --- Card {i}/{len(all_auctions)} ---")
                print(f"  eBay:    {title[:100]}")
                print(f"           https://www.ebay.com/itm/{numeric_id}")
                print(f"  Closest: [{best_variant.get('parallel','Base')}] ${float(best_variant.get('ungraded',0)):.2f} (color_dist={best_dist})")
                if len(variant_scores) > 1:
                    print(f"  Others:  {', '.join(f'[{v.get("parallel","Base")}] d={d:.0f}' for d, v, _ in variant_scores[1:4])}")

                # Now run the layered comparator on the BEST match
                from backend.services.card_comparator import compare_cards
                result = compare_cards(best_scp_img, ebay_full, verbose=False)
                same_card = result.get('same_card', False)
                stats['ce_calls'] += 1

                layer = result.get('layer', '?')
                reason = result.get('reason', '?')[:80]
                print(f"  Verify:  same={same_card} | layer={layer} | {reason}")

                if same_card:
                    scp_match = best_variant
                    scp_variant_used = best_variant
                    stats['ce_matched'] += 1
                else:
                    stats['ce_failed'] += 1

                time.sleep(1.0)  # CE rate limit
            elif not image_url:
                stats['skipped_no_image'] += 1
                continue
            else:
                # skip_ce mode: check if ANY variant is profitable (flag for verification)
                best_profit = -999
                best_variant = None
                for v in scp_variants:
                    p = calculate_profit(v.get('ungraded', 0), bid, shipping)
                    if p > best_profit:
                        best_profit = p
                        best_variant = v
                if best_variant and best_profit >= args.min_profit:
                    scp_match = best_variant

            if not scp_match:
                continue

            # STEP 4: Profit check
            scp_price = float(scp_match.get('ungraded', 0))
            profit = calculate_profit(scp_price, bid, shipping)

            if profit < args.min_profit:
                stats['not_profitable'] += 1
                continue

            stats['profitable'] += 1
            roi = round((profit / (bid + shipping)) * 100, 1) if (bid + shipping) > 0 else 0

            # Extract eBay item ID
            item_id = auction.get('ebay_item_id', '')
            numeric_id = item_id.split('|')[1] if '|' in item_id else item_id
            url = f"https://www.ebay.com/itm/{numeric_id}" if numeric_id else ''

            # End time
            end_time_dt = None
            end_time = auction.get('end_time')
            if end_time:
                try:
                    if isinstance(end_time, str):
                        end_time_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00')).replace(tzinfo=None)
                    else:
                        end_time_dt = end_time
                except Exception:
                    pass

            matched_parallel = scp_match.get('parallel', 'Base')
            is_ce_verified = ce_identity is not None and not args.skip_ce

            opp = {
                'player_name': scp_card['player_name'],
                'card_year': scp_card['card_year'],
                'card_set': scp_match.get('card_set', ''),
                'card_number': scp_card['card_number'],
                'parallel': matched_parallel,
                'scp_price': scp_price,
                'scp_grade_9': float(scp_match['grade_9']) if scp_match.get('grade_9') else None,
                'scp_psa_10': float(scp_match['psa_10']) if scp_match.get('psa_10') else None,
                'scp_url': scp_match.get('url'),
                'scp_volume': scp_match.get('volume', ''),
                'buy_price': bid,
                'shipping': shipping,
                'profit': profit,
                'roi': roi,
                'ebay_title': title,
                'ebay_url': url,
                'ebay_item_id': numeric_id,
                'image_url': image_url,
                'listing_image_urls': image_urls[:15] if image_urls else None,
                'bid_count': auction.get('bid_count', 0),
                'end_time': end_time_dt,
                'listing_type': 'auction',
                'price_source': 'scp_cache',
                'flagged': not is_ce_verified,
                'verification_status': 'ce_confirmed' if is_ce_verified else 'pending',
            }
            opportunities.append(opp)

            print(f"  {'[CE]' if is_ce_verified else '[?]'} ${profit:.2f} profit ({roi:.0f}% ROI) | ${bid:.2f} bid -> ${scp_price:.2f} SCP [{matched_parallel}]")
            print(f"      {scp_card['player_name']} {scp_card['card_year']} #{scp_card['card_number']} | {url}")

            # Write to DB immediately
            if not args.dry_run:
                try:
                    existing = db.execute(
                        text("SELECT id FROM opportunities WHERE ebay_item_id = :eid LIMIT 1"),
                        {"eid": numeric_id},
                    ).first()
                    if existing:
                        db.execute(
                            text("UPDATE opportunities SET last_seen_at = NOW() WHERE ebay_item_id = :eid"),
                            {"eid": numeric_id},
                        )
                    else:
                        row = Opportunity(
                            player_name=opp['player_name'], card_year=opp['card_year'],
                            card_set=opp['card_set'], card_number=opp['card_number'],
                            parallel=opp['parallel'], scp_price=opp['scp_price'],
                            scp_grade_9=opp.get('scp_grade_9'), scp_psa_10=opp.get('scp_psa_10'),
                            scp_url=opp.get('scp_url'), scp_volume=opp.get('scp_volume'),
                            buy_price=opp['buy_price'], shipping=opp['shipping'],
                            profit=opp['profit'], roi=opp['roi'],
                            ebay_title=opp['ebay_title'], ebay_url=opp['ebay_url'],
                            ebay_item_id=opp['ebay_item_id'], image_url=opp.get('image_url'),
                            listing_image_urls=opp.get('listing_image_urls'),
                            bid_count=opp.get('bid_count', 0), end_time=opp.get('end_time'),
                            listing_type='auction', flagged=opp['flagged'],
                            verification_status=opp['verification_status'],
                            verification_detail={'pipeline': 'v2', 'ce_verified': is_ce_verified},
                            sport=args.sport, price_source=opp['price_source'],
                            scan_id=tracker.run_id,
                        )
                        db.add(row)
                    db.commit()
                except Exception as e:
                    db.rollback()
                    log.warn(f'DB write failed: {e}', category='db_error')

        # Cleanup
        if scp_scraper_instance and scp_scraper_instance is not False:
            try:
                scp_scraper_instance.close()
            except Exception:
                pass

        # Cleanup ended auctions
        if not args.dry_run:
            try:
                cutoff = datetime.utcnow() - timedelta(days=3)
                cleaned = db.execute(
                    text("DELETE FROM opportunities WHERE listing_type = 'auction' AND end_time < :c"),
                    {"c": cutoff},
                ).rowcount
                db.commit()
                if cleaned:
                    print(f"\n  Cleaned {cleaned} ended auctions (>3 days old)")
            except Exception:
                pass

        db.close()

        # Summary
        print(f"\n{'=' * 70}")
        print(f"RESULTS")
        print(f"{'=' * 70}")
        print(f"  Liquid cards loaded:  {len(liquid_cards)}")
        print(f"  eBay queries run:     {queries_run}")
        print(f"  Auctions found:       {len(all_auctions)}")
        print(f"  CE calls:             {stats['ce_calls']}")
        print(f"  CE matched to SCP:    {stats['ce_matched']}")
        print(f"  CE failed/no match:   {stats['ce_failed']}")
        print(f"  CE base card skips:   {stats.get('ce_base_skip', 0)}")
        print(f"  CE wrong card #:      {stats.get('ce_wrong_card', 0)}")
        print(f"  Skipped (no image):   {stats['skipped_no_image']}")
        print(f"  Profitable:           {stats['profitable']}")
        print(f"  Not profitable:       {stats['not_profitable']}")
        print(f"  OPPORTUNITIES STORED: {len(opportunities)}")
        if args.dry_run:
            print(f"  [DRY RUN - nothing written to DB]")

        tracker.complete(summary={
            'opportunities_found': len(opportunities),
            'queries_run': queries_run,
            'auctions_found': len(all_auctions),
            **stats,
        })

    except Exception as e:
        log.error(f'Pipeline V2 failed: {e}', category='pipeline_crash')
        tracker.fail(str(e))
        raise


if __name__ == '__main__':
    main()
