#!/usr/bin/env python3
"""Liquidity-first opportunity pipeline.

Architecture:
1. SCP cache -> card universe (what exists, what it's worth)
2. 130point -> liquidity filter (what actually sells, how often, at what price)
3. eBay -> targeted search (find listings for liquid cards only)
4. CE -> identity verification (confirm the listing matches the card)

This inverts the current pipeline which starts from eBay and hopes to match SCP.
Instead, we start from KNOWN liquid cards and find them on eBay.

Zero wasted eBay API calls -- every search is for a card we know sells.
"""
import sys, os, json, re, time, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.utils.database import SessionLocal
from backend.scrapers.oneThirtyPoint_scraper import OneThirtyPointScraper
from backend.utils.logger import get_logger
from sqlalchemy import text

log = get_logger('liquidity_pipeline')

FEE_RATE = 0.13
GRADED = ['psa ', 'bgs ', 'sgc ', 'cgc ', 'fcgs ', 'gem mint',
          'mint 10', 'mint 9', ' graded ', 'psa10', 'psa 10',
          'bgs 10', 'sgc 10', 'cgc 10']
JUNK = ['you pick', 'pick your', 'complete your set', 'pick a card',
        'lot of', 'mystery', 'repack', 'break', 'digital', 'bunt',
        'replica', 'reprint', 'project 2020', 'custom card', 'aceo']


def step1_build_card_universe(db, min_price=20, max_price=1000):
    """Get all SCP cards in our price range with their variants."""
    print("Step 1: Building card universe from SCP cache...")
    rows = db.execute(text(
        "SELECT player_name, card_year, card_number, variants FROM scp_cache "
        "WHERE LENGTH(player_name) < 40 AND position(',' in player_name) = 0"
    )).fetchall()

    cards = []
    for row in rows:
        v = row.variants
        if isinstance(v, str): v = json.loads(v)
        if not isinstance(v, list): continue
        for x in v:
            price = x.get('ungraded') or 0
            if not price or float(price) < min_price or float(price) > max_price:
                continue
            cards.append({
                'player': row.player_name.strip(),
                'year': row.card_year,
                'number': (row.card_number or '').strip(),
                'parallel': x.get('parallel', 'Base'),
                'scp_price': float(price),
                'scp_url': x.get('url', ''),
                'raw_title': x.get('raw_title', ''),
            })

    # Dedupe by (player, year, number, parallel)
    seen = set()
    unique = []
    for c in cards:
        key = (c['player'].lower(), c['year'], c['number'].lower(), c['parallel'].lower())
        if key not in seen:
            seen.add(key)
            unique.append(c)

    print(f"  {len(unique)} unique cards in ${min_price}-${max_price} range")
    return unique


def step2_check_liquidity(cards, scraper, min_sales=3, max_cards=500, delay=7.5):
    """Check 130point for actual sold data. Filter to liquid cards only."""
    print(f"\nStep 2: Checking liquidity via 130point ({len(cards)} candidates, max {max_cards})...")

    # Sort by SCP price descending (higher value = more worth checking)
    cards.sort(key=lambda c: -c['scp_price'])

    liquid = []
    checked = 0
    rate_limited = False

    for card in cards[:max_cards]:
        if rate_limited:
            break

        # Build 130point query
        query_parts = [card['player'], str(card['year'])]
        if card['number']:
            query_parts.append(f"#{card['number']}")
        if card['parallel'] and card['parallel'] != 'Base':
            query_parts.append(card['parallel'])
        query = ' '.join(query_parts)

        try:
            time.sleep(delay)
            sales = scraper.search(query)
            checked += 1
        except Exception as e:
            if '429' in str(e):
                print(f"  130point rate limited after {checked} queries")
                rate_limited = True
                break
            continue

        if not sales or len(sales) < min_sales:
            continue

        median = scraper.median_price(sales)
        if median < 15:  # too cheap after fees
            continue

        card['sold_median'] = median
        card['sold_count'] = len(sales)
        card['sold_query'] = query
        liquid.append(card)

        if checked % 25 == 0:
            print(f"  Checked {checked}, found {len(liquid)} liquid cards...")

    print(f"  Checked {checked} cards, {len(liquid)} are liquid ({min_sales}+ sales)")
    return liquid


def step3_find_ebay_listings(liquid_cards, db, min_profit=10):
    """Search eBay cache for listings of liquid cards below market value."""
    print(f"\nStep 3: Finding eBay listings for {len(liquid_cards)} liquid cards...")

    # Load eBay cache
    cache_rows = db.execute(text(
        "SELECT results FROM ebay_search_cache WHERE result_count > 0"
    )).fetchall()

    all_listings = {}  # iid -> listing
    for cr in cache_rows:
        results = cr.results
        if isinstance(results, str): results = json.loads(results)
        for listing in (results or []):
            iid = listing.get('ebay_item_id', '')
            if iid and iid not in all_listings:
                price = float(listing.get('price', 0) or 0)
                title = listing.get('title', '')
                tl = title.lower()
                if price <= 0 or price > 200: continue
                if any(j in tl for j in JUNK): continue
                if any(g in tl for g in GRADED): continue
                all_listings[iid] = {
                    'iid': iid, 'price': price, 'title': title, 'tl': tl,
                    'lt': listing.get('listing_type', 'buy_it_now'),
                    'image_url': listing.get('image_url'),
                    'image_urls': listing.get('image_urls', []),
                }

    print(f"  {len(all_listings)} eBay listings in cache")

    opportunities = []
    for card in liquid_cards:
        player_lower = card['player'].lower()
        year_str = str(card['year'])
        number = card['number']

        for iid, listing in all_listings.items():
            tl = listing['tl']

            # Player in title?
            if player_lower.split()[0] not in tl:
                continue
            # Year in title?
            if year_str not in listing['title']:
                continue
            # Card number in title?
            if number:
                nc = number.replace('#', '').strip()
                if nc and f'#{nc}' not in listing['title'] and f'# {nc}' not in listing['title'] and nc not in tl:
                    continue

            buy = listing['price']
            # Use 130point sold median as the reference price (actual market value)
            ref_price = card['sold_median']
            profit = ref_price - buy - (buy * FEE_RATE)

            if profit < min_profit:
                continue

            roi = (profit / buy * 100) if buy > 0 else 0

            # Sanity: buy price should be at least 30% of sold median
            # (below that, it's probably a different card)
            if buy < ref_price * 0.30:
                continue

            opportunities.append({
                'player': card['player'],
                'year': card['year'],
                'number': card['number'],
                'parallel': card['parallel'],
                'scp_price': card['scp_price'],
                'sold_median': card['sold_median'],
                'sold_count': card['sold_count'],
                'buy_price': buy,
                'profit': round(profit, 2),
                'roi': round(roi, 1),
                'ebay_title': listing['title'],
                'ebay_item_id': iid,
                'listing_type': listing['lt'],
                'image_url': listing.get('image_url'),
                'image_urls': listing.get('image_urls', []),
            })

    # Dedupe by eBay item ID
    seen = set()
    unique = []
    for o in opportunities:
        if o['ebay_item_id'] not in seen:
            seen.add(o['ebay_item_id'])
            unique.append(o)

    unique.sort(key=lambda x: -x['profit'])
    print(f"  Found {len(unique)} opportunities backed by sold data")
    return unique


def main():
    parser = argparse.ArgumentParser(description='Liquidity-first opportunity pipeline')
    parser.add_argument('--min-price', type=float, default=20)
    parser.add_argument('--max-price', type=float, default=1000)
    parser.add_argument('--min-profit', type=float, default=10)
    parser.add_argument('--min-sales', type=int, default=3, help='Min 130point sales for liquidity')
    parser.add_argument('--max-cards', type=int, default=200, help='Max cards to check on 130point')
    parser.add_argument('--delay', type=float, default=7.5, help='Seconds between 130point queries')
    args = parser.parse_args()

    db = SessionLocal()
    scraper = OneThirtyPointScraper()

    print("=" * 70)
    print("LIQUIDITY-FIRST OPPORTUNITY PIPELINE")
    print("=" * 70)

    # Step 1: Card universe from SCP
    cards = step1_build_card_universe(db, args.min_price, args.max_price)

    # Step 2: Liquidity check via 130point
    liquid = step2_check_liquidity(cards, scraper, args.min_sales, args.max_cards, args.delay)

    # Step 3: Find eBay listings
    opportunities = step3_find_ebay_listings(liquid, db, args.min_profit)

    # Results
    print(f"\n{'=' * 70}")
    print(f"RESULTS")
    print(f"{'=' * 70}")
    print(f"Cards checked on 130point: {args.max_cards}")
    print(f"Liquid cards found: {len(liquid)}")
    print(f"Opportunities (backed by sold data): {len(opportunities)}")
    print(f"eBay API calls used: 0 (used cache)")
    print()

    for o in opportunities[:20]:
        tag = 'AUC' if o['listing_type'] == 'auction' else 'BIN'
        print(f"  [{tag}] {o['player']} {o['year']} #{o['number']} [{o['parallel']}]")
        print(f"       Buy ${o['buy_price']:.2f} | Sold ${o['sold_median']:.2f} ({o['sold_count']} sales) | Profit ${o['profit']:.2f} ({o['roi']:.0f}%)")
        print(f"       {o['ebay_title'][:75]}")

    db.close()


if __name__ == '__main__':
    main()
