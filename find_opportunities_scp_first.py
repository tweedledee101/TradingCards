#!/usr/bin/env python3
"""
SCP-First Opportunity Pipeline

Starts from what we KNOW sells (liquid SCP variants with worm data),
searches eBay WITH the variant name, confirms the match, checks profit.

7 Steps:
1. Load liquid SCP variants (2+ sales this year, proven velocity)
2. Build targeted eBay search queries from SCP variant + sold title keywords
3. Search eBay Browse API with those queries
4. Confirm variant match (title OR Item Specifics Parallel/Variety field)
5. Check volume (already confirmed — we only load liquid cards)
6. Check profitability (eBay price vs SCP price minus fees)
7. If volume + profit → mark as opportunity

Usage:
    python3 find_opportunities_scp_first.py --limit 100 --dry-run
    python3 find_opportunities_scp_first.py --min-profit 5 --listing-type both
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.utils.database import SessionLocal
from backend.utils.job_tracker import JobTracker
from backend.models import Opportunity
from backend.scrapers.ebay_scraper import EbayScraper, collect_browse_item_image_urls
from sqlalchemy import text

FEE_RATE = 0.13
DEFAULT_SHIPPING = 5.00

JUNK_PATTERNS = [
    'you pick', 'pick your', 'complete your set', 'pick a card',
    'choose your', 'mystery', 'repack', 'break', 'digital', 'bunt',
    'lot of', 'replica', 'reprint', 'project 2020', 'project 70',
    'sticker', 'custom card', 'aceo', 'complete set', 'factory set',
    'funko', 'figure', 'bobblehead', 'plush', 'pin ', 'patch ',
    'jumbo', 'oversized', 'mini-figure', 'card lot', '(2) card',
    '(3) card', '(4) card', '(5) card', 'multi card',
]

GRADED_PATTERNS = ['psa ', 'bgs ', 'sgc ', 'cgc ', 'gem mint', 'graded ',
                   'psa10', 'psa 10', 'bgs 10', 'sgc 10']


# ─── STEP 1: LOAD LIQUID VARIANTS ───────────────────────────────────────────

def load_liquid_variants(db, min_price=5.0, max_price=500.0, limit=500):
    """Load individual variants with proven velocity from SCP cache.

    Returns one entry per variant (not per card group). Each has the full
    SCP data needed to build a search query and confirm a match.
    """
    rows = db.execute(text("""
        SELECT sc.id, sc.player_name, sc.card_year, sc.card_number, sc.variants
        FROM scp_cache sc
        WHERE sc.card_year BETWEEN 2020 AND 2026
          AND EXISTS (
            SELECT 1 FROM jsonb_array_elements(sc.variants) v
            WHERE (v->>'sales_this_year')::int >= 2
              AND (v->>'ungraded')::numeric BETWEEN :min_p AND :max_p
          )
        ORDER BY sc.player_name, sc.card_year
    """), {'min_p': min_price, 'max_p': max_price}).fetchall()

    variants = []
    for row in rows:
        vlist = row.variants if isinstance(row.variants, list) else json.loads(row.variants)
        for v in vlist:
            price = float(v.get('ungraded') or 0)
            sales_yr = int(v.get('sales_this_year') or 0)
            if price < min_price or price > max_price or sales_yr < 2:
                continue
            variants.append({
                'cache_id': row.id,
                'player_name': row.player_name,
                'card_year': row.card_year,
                'card_number': row.card_number,
                'parallel': v.get('parallel', 'Base'),
                'card_set': v.get('card_set', ''),
                'scp_price': price,
                'scp_url': v.get('url', ''),
                'volume': v.get('volume', ''),
                'sales_this_year': sales_yr,
                'sales_last_90d': int(v.get('sales_last_90d') or 0),
                'common_keywords': v.get('common_keywords', []),
                'grade_9': v.get('grade_9'),
                'psa_10': v.get('psa_10'),
            })
        if len(variants) >= limit:
            break

    return variants[:limit]


# ─── STEP 2: BUILD SEARCH QUERIES ───────────────────────────────────────────

def build_queries_for_variant(variant):
    """Build primary + alternate eBay search queries for a variant.

    Primary: player year set parallel
    Alternate: uses common_keywords from sold titles to catch different terminology.
    """
    player = variant['player_name']
    year = str(variant['card_year']) if variant['card_year'] else ''
    card_set = (variant.get('card_set') or '').strip()
    parallel = (variant.get('parallel') or '').strip()
    card_number = (variant.get('card_number') or '').strip()

    # Primary query: player + year + parallel (+ card number if short)
    primary_parts = [player, year]
    if card_set and card_set.lower() not in ('unknown', 'base', ''):
        primary_parts.append(card_set)
    if parallel and parallel.lower() != 'base':
        primary_parts.append(parallel)
    primary = ' '.join(primary_parts)

    queries = [primary]

    # Alternate query from sold title keywords (catches different terminology)
    keywords = variant.get('common_keywords', [])
    if keywords:
        # Build an alternate using top keywords that aren't already in primary
        primary_lower = primary.lower()
        extra_kws = [kw for kw in keywords[:8]
                     if kw.lower() not in primary_lower and len(kw) >= 3]
        if extra_kws:
            alt_parts = [player, year]
            # Add up to 3 extra keywords from sold titles
            alt_parts.extend(extra_kws[:3])
            alt = ' '.join(alt_parts)
            if alt.lower() != primary.lower():
                queries.append(alt)

    return queries


# ─── STEP 3: SEARCH EBAY ────────────────────────────────────────────────────

def search_ebay(scraper, query, listing_type='both', hours=168):
    """Search eBay Browse API. Returns raw listing dicts."""
    if listing_type == 'auction':
        results = scraper.search_auctions_ending_soon(query, hours=hours)
        return results or []
    elif listing_type == 'bin':
        results = scraper.get_active_listings(query, max_total=200)
        return [r for r in (results or []) if r.get('listing_type') == 'buy_it_now']
    else:
        # Both: auctions + BIN
        auctions = scraper.search_auctions_ending_soon(query, hours=hours) or []
        bins = scraper.get_active_listings(query, max_total=200) or []
        bins = [r for r in bins if r.get('listing_type') == 'buy_it_now']
        # Dedupe by item ID
        seen = {a.get('ebay_item_id') for a in auctions}
        for b in bins:
            if b.get('ebay_item_id') not in seen:
                auctions.append(b)
                seen.add(b.get('ebay_item_id'))
        return auctions


# ─── STEP 4: CONFIRM VARIANT MATCH ──────────────────────────────────────────

def confirm_variant_from_title(title, variant):
    """Check if the eBay title contains the SCP parallel name.

    SCP parallels are like [Chrome Refractor], [Green Shimmer], [Aqua Refractor].
    We check if the words from the parallel appear in the title.
    """
    if not title:
        return False
    parallel = (variant.get('parallel') or '').strip()
    tl = title.lower()

    if not parallel or parallel.lower() == 'base':
        # For base cards: must NOT contain parallel/variation/insert/auto indicators
        reject_indicators = [
            'refractor', 'shimmer', 'prizm', 'foil', 'chrome refractor',
            'gold', 'silver', 'green', 'blue', 'red', 'orange',
            'purple', 'pink', 'aqua', 'sapphire', 'mojo',
            'speckle', 'wave', 'camo', 'atomic', 'hyper',
            'numbered', '/25', '/50', '/75', '/99', '/150',
            '/199', '/250', '/299', '/500', '/999',
            'variation', 'sp ', ' sp', 'ssp', 'short print',
            'parallel', 'insert', 'case hit',
            'autograph', 'auto ', ' auto', 'signed',
            'relic', 'patch', 'jersey', 'memorabilia',
            'exclusive', 'anniversary', 'retro', 'vintage',
            'cracked ice', 'lazer', 'laser', 'chrome',
            'image variation', 'photo variation',
            'border', 'logo ', 'flag ',
        ]
        if any(ind in tl for ind in reject_indicators):
            return False
        # If the SCP set is specific (not generic Topps/Bowman), require it in the title
        card_set = (variant.get('card_set') or '').strip().lower()
        if card_set and card_set not in ('unknown', 'base', ''):
            # Extract the distinguishing part of the set name (last 1-2 words)
            generic_prefixes = ['topps', 'bowman', 'panini', 'donruss', 'prizm']
            set_words = [w for w in card_set.split() if w not in generic_prefixes]
            if set_words:
                # At least the key set words must appear in title
                if not all(w in tl for w in set_words):
                    return False
        return True

    # For non-base: check if parallel words appear in title
    par_words = parallel.lower().split()

    # Single-word parallels (e.g. "Refractor") are dangerous — "Purple Speckle Refractor"
    # also contains "refractor". Reject if a color/modifier word precedes it.
    if len(par_words) == 1:
        word = par_words[0]
        if word not in tl:
            return False
        # Check that no color modifier immediately precedes our word
        color_mods = ['gold', 'silver', 'green', 'blue', 'red', 'orange', 'purple',
                      'pink', 'aqua', 'black', 'white', 'yellow', 'lime', 'sky',
                      'royal', 'navy', 'light', 'dark', 'neon', 'atomic',
                      'speckle', 'shimmer', 'sparkle', 'geometric', 'hyper',
                      'mega', 'super', 'cracked', 'wave', 'camo']
        # Find the word in title and check what's before it
        idx = tl.find(word)
        if idx > 0:
            before = tl[:idx].rstrip()
            last_word_before = before.split()[-1] if before.split() else ''
            if last_word_before in color_mods:
                return False
        return True

    return all(w in tl for w in par_words)


def confirm_variant_from_description(description, variant):
    """Check if the listing description mentions the parallel name."""
    if not description:
        return False
    parallel = (variant.get('parallel') or '').strip()
    if not parallel or parallel.lower() == 'base':
        return False
    dl = description.lower()
    par_words = parallel.lower().split()
    if all(w in dl for w in par_words):
        return True
    # Try alternate names from sold title keywords
    keywords = variant.get('common_keywords', [])
    if keywords:
        # If 3+ sold keywords appear in description, likely the same card
        kw_hits = sum(1 for kw in keywords if kw.lower() in dl)
        if kw_hits >= 3:
            return True
    return False


def confirm_variant_from_aspects(item_details, variant):
    """Check Item Specifics (Parallel/Variety, Card Number, Year) from getItem API.

    This is the definitive check — structured data from the listing.
    """
    if not item_details:
        return False, None

    ebay_parallel = (item_details.get('parallel') or 'Base').strip().lower()
    scp_parallel = (variant.get('parallel') or 'Base').strip().lower()

    # Check card number matches
    ebay_num = (item_details.get('card_number') or '').strip().lower()
    scp_num = (variant.get('card_number') or '').strip().lower()
    if ebay_num and scp_num and ebay_num != scp_num:
        # Card numbers don't match — wrong card
        return False, None

    # Check year matches
    ebay_year = item_details.get('card_year')
    if ebay_year and variant.get('card_year') and int(ebay_year) != int(variant['card_year']):
        return False, None

    # Check parallel match
    if ebay_parallel == scp_parallel:
        return True, ebay_parallel
    # Fuzzy: all words from shorter in longer
    ep_words = set(ebay_parallel.split())
    sp_words = set(scp_parallel.split())
    if sp_words and sp_words.issubset(ep_words):
        return True, ebay_parallel
    if ep_words and ep_words.issubset(sp_words):
        return True, ebay_parallel

    return False, ebay_parallel


# ─── STEP 6: PROFITABILITY ──────────────────────────────────────────────────

def check_profitability(scp_price, buy_price, shipping=0):
    """Calculate profit: SCP * (1 - fees) - buy - shipping."""
    net_sell = float(scp_price) * (1 - FEE_RATE)
    profit = net_sell - float(buy_price) - float(shipping)
    roi = (profit / (float(buy_price) + float(shipping))) * 100 if (buy_price + shipping) > 0 else 0
    return round(profit, 2), round(roi, 1)


# ─── MAIN PIPELINE ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='SCP-First Opportunity Pipeline')
    parser.add_argument('--limit', type=int, default=200, help='Max variants to process')
    parser.add_argument('--min-profit', type=float, default=5.0, help='Min profit threshold')
    parser.add_argument('--min-price', type=float, default=5.0, help='Min SCP price')
    parser.add_argument('--max-price', type=float, default=500.0, help='Max SCP price')
    parser.add_argument('--listing-type', choices=['auction', 'bin', 'both'], default='both')
    parser.add_argument('--hours', type=int, default=168, help='Auction window (hours)')
    parser.add_argument('--dry-run', action='store_true', help='Print only, no DB writes')
    parser.add_argument('--sport', default='Baseball')
    parser.add_argument('--skip-getitem', action='store_true',
                        help='Skip getItem API calls entirely (faster, may miss opportunities)')
    args = parser.parse_args()

    print("=" * 70)
    print("SCP-FIRST OPPORTUNITY PIPELINE")
    print("Known liquid → Targeted search → Confirm match → Profit check")
    print("=" * 70)

    tracker = JobTracker('scp_first_pipeline')
    tracker.start(total=0, parameters=vars(args))

    db = SessionLocal()

    # ── STEP 1: LOAD LIQUID VARIANTS ──
    print("\nStep 1: Loading liquid variants from SCP cache...")
    variants = load_liquid_variants(db, min_price=args.min_price,
                                    max_price=args.max_price, limit=args.limit)
    print(f"  {len(variants)} liquid variants loaded")
    db.close()  # Close DB — don't hold connection during long eBay API phase

    if not variants:
        print("  No liquid variants found. Run the worm first.")
        tracker.complete(summary={'opportunities_found': 0})
        return

    # ── STEP 2: BUILD QUERIES ──
    print("\nStep 2: Building targeted search queries...")
    search_plan = []  # (query, variant)
    for v in variants:
        queries = build_queries_for_variant(v)
        for q in queries:
            search_plan.append((q, v))
    print(f"  {len(search_plan)} search queries built ({len(variants)} variants)")

    # Dedupe queries (same query string → only search once, keep all variants)
    query_to_variants = {}
    for q, v in search_plan:
        q_key = q.lower().strip()
        if q_key not in query_to_variants:
            query_to_variants[q_key] = {'query': q, 'variants': []}
        query_to_variants[q_key]['variants'].append(v)

    unique_queries = list(query_to_variants.values())
    print(f"  {len(unique_queries)} unique queries after dedup")

    # ── STEP 3: SEARCH EBAY ──
    print(f"\nStep 3: Searching eBay ({args.listing_type})...")
    scraper = EbayScraper()
    all_listings = []  # (listing, variant)
    seen_ids = set()
    queries_run = 0
    consecutive_errors = 0

    tracker.update(processed=0, total=len(unique_queries))

    for i, entry in enumerate(unique_queries, 1):
        query = entry['query']
        entry_variants = entry['variants']

        if i % 25 == 0 or i == 1:
            print(f"  [{i}/{len(unique_queries)}] {len(all_listings)} listings found...")

        results = search_ebay(scraper, query, listing_type=args.listing_type, hours=args.hours)
        queries_run += 1

        if results is None or (not results and consecutive_errors > 0):
            consecutive_errors += 1
            if consecutive_errors >= 5:
                print(f"\n  BAILING: {consecutive_errors} consecutive failures. API quota likely exhausted.")
                break
        else:
            consecutive_errors = 0

        for listing in (results or []):
            item_id = listing.get('ebay_item_id', '')
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)

            title = listing.get('title', '')
            tl = title.lower()

            # Quick junk filter
            if any(j in tl for j in JUNK_PATTERNS):
                continue
            if any(g in tl for g in GRADED_PATTERNS):
                continue

            price = listing.get('price', 0)
            if price < 1:
                continue

            # Try to match this listing to one of the variants for this query
            for v in entry_variants:
                all_listings.append((listing, v))

        tracker.update(processed=i)
        time.sleep(1.0)  # Rate limit

    print(f"\n  {len(all_listings)} listing-variant pairs to evaluate from {queries_run} queries")

    # ── STEP 4 + 5 + 6 + 7: CONFIRM + VOLUME + PROFIT + MARK ──
    print(f"\nStep 4-7: Identifying cards, verifying comps, checking profitability...")
    from backend.services.comp_verifier import extract_card_identity, find_matching_scp_comp

    opportunities = []
    getitem_calls = 0
    title_matches = 0
    aspect_matches = 0
    no_match = 0
    comp_rejections = 0
    mismatch_recoveries = 0

    db = SessionLocal()

    for i, (listing, variant) in enumerate(all_listings, 1):
        title = listing.get('title', '')
        price = listing.get('price', 0)
        shipping = listing.get('shipping', DEFAULT_SHIPPING)
        item_id = listing.get('ebay_item_id', '')

        # Already found this item as an opportunity?
        numeric_id_check = item_id.split('|')[1] if '|' in item_id else item_id
        if any(o['ebay_item_id'] == numeric_id_check for o in opportunities):
            continue

        # ── STEP 4: Does this match the card we searched for? ──
        matched_target = False
        match_method = None
        item_specifics = None

        if confirm_variant_from_title(title, variant):
            matched_target = True
            match_method = 'title'
            title_matches += 1
        elif not args.skip_getitem:
            max_buy = float(variant['scp_price']) * (1 - FEE_RATE) - args.min_profit
            if (price + shipping) < max_buy:
                details = scraper.get_full_item_details(item_id)
                getitem_calls += 1
                if details:
                    item_specifics = details
                    confirmed, ebay_par = confirm_variant_from_aspects(details, variant)
                    if confirmed:
                        matched_target = True
                        match_method = 'item_specifics'
                        aspect_matches += 1
                    else:
                        desc = EbayScraper._item_description_plain_text(details)
                        if confirm_variant_from_description(desc, variant):
                            matched_target = True
                            match_method = 'description'
                            aspect_matches += 1
                time.sleep(0.5)

        if matched_target:
            # ── MATCH: use the search target's known SCP price ──
            scp_price = variant['scp_price']
            verified_parallel = variant['parallel']
            price_source = 'scp_cache'
        else:
            # ── MISMATCH: identify what this card actually is, look it up ──
            identity = extract_card_identity(title, item_specifics)
            if identity.confidence < 0.33:
                no_match += 1
                continue

            # Look up this card's actual SCP comp
            verified_comp = find_matching_scp_comp(identity, db, variant['player_name'])
            if not verified_comp or verified_comp['price'] <= 0:
                no_match += 1
                continue

            # Check if this different card is liquid enough
            if verified_comp.get('sales_this_year', 0) < 2:
                no_match += 1
                continue

            scp_price = verified_comp['price']
            verified_parallel = verified_comp.get('parallel', identity.parallel or 'Unknown')
            price_source = 'scp_verified_mismatch'
            match_method = 'mismatch_recovery'
            mismatch_recoveries += 1

        # ── STEP 5: Volume already confirmed (target match) or checked above (mismatch) ──

        # ── STEP 6: Profitability ──
        profit, roi = check_profitability(scp_price, price, shipping)
        if profit < args.min_profit:
            continue

        # ── STEP 7: Mark as opportunity ──
        # Build eBay URL
        numeric_id = item_id.split('|')[1] if '|' in item_id else item_id
        ebay_url = f"https://www.ebay.com/itm/{numeric_id}"

        # Parse end_time
        end_time_raw = listing.get('end_time')
        end_time_dt = None
        if end_time_raw:
            try:
                if isinstance(end_time_raw, str):
                    end_time_dt = datetime.fromisoformat(end_time_raw.replace('Z', '+00:00')).replace(tzinfo=None)
                else:
                    end_time_dt = end_time_raw
            except Exception:
                pass

        listing_type = listing.get('listing_type', 'buy_it_now')
        image_urls = listing.get('image_urls') or []
        image_url = listing.get('image_url') or (image_urls[0] if image_urls else None)

        opp = {
            'player_name': variant['player_name'],
            'card_year': variant['card_year'],
            'card_set': variant.get('card_set', ''),
            'card_number': variant['card_number'],
            'parallel': verified_parallel,
            'scp_price': scp_price,
            'scp_grade_9': float(variant['grade_9']) if variant.get('grade_9') else None,
            'scp_psa_10': float(variant['psa_10']) if variant.get('psa_10') else None,
            'scp_url': variant.get('scp_url', ''),
            'scp_volume': variant.get('volume', ''),
            'buy_price': price,
            'shipping': shipping,
            'profit': profit,
            'roi': roi,
            'ebay_title': title,
            'ebay_url': ebay_url,
            'ebay_item_id': numeric_id,
            'image_url': image_url,
            'listing_image_urls': image_urls[:15] if image_urls else None,
            'bid_count': listing.get('bid_count', 0),
            'end_time': end_time_dt,
            'listing_type': listing_type,
            'price_source': price_source,
            'flagged': False,
            'verification_status': f'scp_first_{match_method}_verified',
            'match_method': match_method,
        }
        opportunities.append(opp)

        print(f"\n  OPPORTUNITY #{len(opportunities)}: ${profit:.2f} profit ({roi:.0f}% ROI)")
        print(f"    {variant['player_name']} {variant['card_year']} [{verified_parallel}]")
        print(f"    eBay: ${price:.2f} + ${shipping:.2f} ship | SCP: ${scp_price:.2f} ({price_source})")
        print(f"    {title[:90]}")
        print(f"    {ebay_url}")
        print(f"    Matched via: {match_method} | Volume: {variant['sales_this_year']} sales/yr")

    # ── WRITE TO DB ──
    if not args.dry_run and opportunities:
        print(f"\nWriting {len(opportunities)} opportunities to database...")
        db = SessionLocal()
        written = 0
        for opp in opportunities:
            try:
                existing = db.execute(
                    text("SELECT id FROM opportunities WHERE ebay_item_id = :eid LIMIT 1"),
                    {"eid": opp['ebay_item_id']},
                ).first()
                if existing:
                    db.execute(
                        text("UPDATE opportunities SET last_seen_at = NOW() WHERE ebay_item_id = :eid"),
                        {"eid": opp['ebay_item_id']},
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
                        listing_type=opp['listing_type'], flagged=False,
                        verification_status=opp['verification_status'],
                        verification_detail={'pipeline': 'scp_first', 'matched_via': opp['match_method']},
                        sport=args.sport, price_source='scp_cache',
                        scan_id=tracker.run_id,
                    )
                    db.add(row)
                    written += 1
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"    DB error: {e}")
        print(f"  {written} new opportunities written")
        db.close()

    # ── SUMMARY ──
    print(f"\n{'=' * 70}")
    print(f"SCP-FIRST PIPELINE COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Liquid variants loaded:  {len(variants)}")
    print(f"  Unique queries run:      {queries_run}")
    print(f"  Listings evaluated:      {len(all_listings)}")
    print(f"  Title matches:           {title_matches}")
    print(f"  Item Specifics matches:  {aspect_matches}")
    print(f"  No match:                {no_match}")
    print(f"  getItem API calls:       {getitem_calls}")
    print(f"  OPPORTUNITIES FOUND:     {len(opportunities)}")
    if opportunities:
        avg_profit = sum(o['profit'] for o in opportunities) / len(opportunities)
        print(f"  Avg profit:              ${avg_profit:.2f}")
    print(f"{'=' * 70}")

    tracker.complete(summary={
        'opportunities_found': len(opportunities),
        'variants_loaded': len(variants),
        'queries_run': queries_run,
        'title_matches': title_matches,
        'aspect_matches': aspect_matches,
        'getitem_calls': getitem_calls,
    })


if __name__ == '__main__':
    main()
