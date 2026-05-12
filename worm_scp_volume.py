#!/usr/bin/env python3
"""SCP Volume Worm - scrapes product pages for volume data.

Targets $20-$200 cards (sweet spot for arbitrage).
Stores volume in scp_cache variants JSONB.
No rate limit from SCP.

Usage:
    python3 worm_scp_volume.py --limit 100
    nohup python3 worm_scp_volume.py --limit 500 > /tmp/scp_volume.log 2>&1 &
"""
import sys, os, json, re, time, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from backend.utils.database import SessionLocal
from sqlalchemy import text
import shutil

def extract_volume_from_page(driver, url):
    """Load SCP product page and extract ungraded volume + sold title keywords."""
    try:
        driver.get(url)
        time.sleep(2)
    except:
        pass  # timeout OK, page may have partially loaded

    volume = ''
    sold_titles = []
    sold_prices = []

    try:
        body = driver.find_element(By.TAG_NAME, 'body').text
        # Volume: first value is ungraded
        m = re.search(r'volume:\s*(.+?)(?:\s*volume:|$)', body.lower())
        if m:
            volume = m.group(1).strip()

        # Sold titles: lines that end with [eBay] and have a price
        for line in body.split('\n'):
            line = line.strip()
            if '[eBay]' in line:
                # Extract title (everything before the card number reference)
                title = re.sub(r'\s*#\d+\s*\[eBay\]\s*$', '', line).strip()
                if title and len(title) > 10:
                    sold_titles.append(title)
            # Extract sold prices
            price_m = re.match(r'^\$([\d,]+\.\d{2})\s*$', line)
            if price_m:
                sold_prices.append(float(price_m.group(1).replace(',', '')))
    except:
        pass

    # Extract common keywords from sold titles
    keywords = {}
    for title in sold_titles:
        words = set(w.lower() for w in re.split(r'[^a-zA-Z0-9]+', title) if len(w) >= 3)
        for w in words:
            keywords[w] = keywords.get(w, 0) + 1

    # Keywords that appear in 50%+ of sold titles are reliable search terms
    threshold = max(len(sold_titles) * 0.5, 2)
    common_keywords = [kw for kw, cnt in sorted(keywords.items(), key=lambda x: -x[1])
                       if cnt >= threshold]

    avg_price = 0
    if sold_prices:
        # Use median to avoid outliers
        sorted_prices = sorted(sold_prices)
        mid = len(sorted_prices) // 2
        avg_price = sorted_prices[mid] if len(sorted_prices) % 2 else (sorted_prices[mid-1] + sorted_prices[mid]) / 2

    return {
        'volume': volume,
        'sold_titles': sold_titles[:20],
        'sold_prices': sold_prices[:20],
        'avg_price': avg_price,
        'common_keywords': common_keywords[:15],
        'sold_count': len(sold_titles),
    }


def main():
    parser = argparse.ArgumentParser(description='SCP Volume Worm')
    parser.add_argument('--limit', type=int, default=100, help='Max pages to scrape')
    parser.add_argument('--min-price', type=float, default=20)
    parser.add_argument('--max-price', type=float, default=200)
    parser.add_argument('--refresh', action='store_true',
                        help='Refresh existing liquid cards (update prices + volume). '
                             'Without this flag, only discovers NEW volume.')
    parser.add_argument('--stale-days', type=int, default=7,
                        help='In refresh mode, only update cards older than N days')
    args = parser.parse_args()

    db = SessionLocal()

    # Get SCP cache entries
    if args.refresh:
        # Refresh mode: target cards that already have volume but are stale
        rows = db.execute(text(
            "SELECT id, player_name, card_year, card_number, variants, created_at FROM scp_cache "
            "WHERE LENGTH(player_name) < 40 AND position(',' in player_name) = 0 "
            "AND created_at < NOW() - INTERVAL '" + str(args.stale_days) + " days'"
        )).fetchall()
    else:
        # Discovery mode: target cards with no volume yet
        rows = db.execute(text(
            "SELECT id, player_name, card_year, card_number, variants FROM scp_cache "
            "WHERE LENGTH(player_name) < 40 AND position(',' in player_name) = 0"
        )).fetchall()

    # Extract URLs for cards in price range
    targets = []
    for row in rows:
        v = row.variants
        if isinstance(v, str): v = json.loads(v)
        if not isinstance(v, list): continue
        for i, x in enumerate(v):
            price = x.get('ungraded') or 0
            url = x.get('url') or ''
            vol = x.get('volume') or ''
            if not (price and url and 'sportscardspro.com' in url):
                continue
            if args.refresh:
                # Refresh mode: only cards with existing volume (liquid cards)
                if vol and any(kw in vol for kw in ['per day', 'per week', 'per month']):
                    targets.append({
                        'cache_id': row.id, 'variant_idx': i, 'url': url,
                        'player': row.player_name.strip(), 'year': row.card_year,
                        'number': row.card_number, 'parallel': x.get('parallel', 'Base'),
                        'price': float(price), 'old_volume': vol,
                    })
            else:
                # Discovery mode: only cards with no volume
                if not vol and args.min_price <= float(price) <= args.max_price:
                    targets.append({
                        'cache_id': row.id, 'variant_idx': i, 'url': url,
                        'player': row.player_name.strip(), 'year': row.card_year,
                        'number': row.card_number, 'parallel': x.get('parallel', 'Base'),
                        'price': float(price),
                    })

    # Dedupe by URL
    seen = set()
    unique = []
    for t in targets:
        if t['url'] not in seen:
            seen.add(t['url'])
            unique.append(t)

    # Round-robin across players so we don't exhaust one player before touching others
    from collections import defaultdict
    by_player = defaultdict(list)
    for t in unique:
        by_player[t['player']].append(t)
    
    # Sort each player's cards by price (mid-range first)
    for p in by_player:
        by_player[p].sort(key=lambda x: abs(x['price'] - 75))
    
    # Round-robin: take 1 card from each player, repeat
    players_list = sorted(by_player.keys(), key=lambda p: -len(by_player[p]))
    round_robin = []
    idx = 0
    while len(round_robin) < len(unique):
        added = False
        for p in players_list:
            cards = by_player[p]
            if idx < len(cards):
                round_robin.append(cards[idx])
                added = True
        if not added:
            break
        idx += 1
    unique = round_robin

    mode = 'REFRESH' if args.refresh else 'DISCOVERY'
    print(f"SCP Volume Worm ({mode})")
    print(f"  Targets: {len(unique)} cards")
    if args.refresh:
        print(f"  Stale threshold: {args.stale_days} days")
    else:
        print(f"  Price range: ${args.min_price}-${args.max_price}")
    print(f"  Limit: {args.limit}")
    print()

    # Start browser
    opts = Options()
    opts.add_argument('--headless')
    for fp in ['/usr/bin/firefox', '/usr/lib/firefox/firefox', '/usr/bin/firefox-esr']:
        if os.path.exists(fp):
            opts.binary_location = fp
            break
    service = Service(executable_path=shutil.which('geckodriver') or '/usr/local/bin/geckodriver')
    driver = webdriver.Firefox(options=opts, service=service)
    driver.set_page_load_timeout(45)

    scraped = 0
    found_volume = 0
    liquid = 0
    errors = 0

    for entry in unique[:args.limit]:
        result = extract_volume_from_page(driver, entry['url'])
        scraped += 1
        vol = result['volume']

        if vol:
            found_volume += 1
            entry['volume'] = vol
            entry['common_keywords'] = result['common_keywords']
            entry['sold_count_scp'] = result['sold_count']

            # Update the SCP cache with volume + keywords
            try:
                cache_row = db.execute(text(
                    "SELECT id, variants FROM scp_cache WHERE id = :id"
                ), {"id": entry['cache_id']}).fetchone()
                if cache_row:
                    variants = cache_row.variants
                    if isinstance(variants, str): variants = json.loads(variants)
                    for vv in variants:
                        if vv.get('url') == entry['url']:
                            vv['volume'] = vol
                            vv['common_keywords'] = result['common_keywords']
                            vv['sold_titles_sample'] = result['sold_titles'][:5]
                            vv['sold_count_scp'] = result['sold_count']
                            # Update price if we got sold data
                            if result.get('avg_price') and result['avg_price'] > 0:
                                old_price = float(vv.get('ungraded') or 0)
                                vv['ungraded'] = round(result['avg_price'], 2)
                                if old_price > 0 and abs(old_price - result['avg_price']) / old_price > 0.3:
                                    print(f"           PRICE UPDATE: ${old_price:.2f} -> ${result['avg_price']:.2f}")
                            break
                    db.execute(text(
                        "UPDATE scp_cache SET variants = :v, created_at = NOW() WHERE id = :id"
                    ), {"v": json.dumps(variants), "id": entry['cache_id']})
                    db.commit()
            except Exception as e:
                errors += 1

            is_liquid = any(kw in vol for kw in ['per day', 'per week'])
            if is_liquid:
                liquid += 1
                kws = ', '.join(result['common_keywords'][:5])
                print(f"  [{scraped}] LIQUID: ${entry['price']:.2f} {entry['player']} #{entry['number']} [{entry['parallel']}] | {vol}")
                print(f"           Keywords: {kws}")
            elif scraped <= 20 or scraped % 25 == 0:
                print(f"  [{scraped}] {vol}: ${entry['price']:.2f} {entry['player']} #{entry['number']}")

    driver.quit()
    db.close()

    print(f"\n{'=' * 60}")
    print(f"SCP Volume Worm Complete")
    print(f"  Scraped: {scraped}")
    print(f"  Volume found: {found_volume}")
    print(f"  Liquid (daily/weekly): {liquid}")
    print(f"  Errors: {errors}")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
