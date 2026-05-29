#!/usr/bin/env python3
"""SCP Volume Worm - scrapes product pages for sale dates and volume data.

Parses actual sale dates from SCP product pages to compute real velocity.
A card needs 2+ sales in the current year to be considered "liquid."
SCP's volume label is kept as a sanity check but NOT the primary signal.

Usage:
    python3 worm_scp_volume.py --limit 100
    nohup python3 worm_scp_volume.py --limit 500 > /tmp/scp_volume.log 2>&1 &
"""
import sys, os, json, re, time, argparse
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from backend.utils.database import SessionLocal
from sqlalchemy import text
import shutil


def extract_volume_from_page(driver, url):
    """Load SCP product page and extract volume label + dated sold records."""
    try:
        driver.get(url)
        time.sleep(2)
    except:
        pass  # timeout OK, page may have partially loaded

    volume = ''
    sales = []  # list of {date, title, price}

    try:
        body = driver.find_element(By.TAG_NAME, 'body').text
        # Volume label (SCP's own estimate - keep as sanity check)
        m = re.search(r'volume:\s*(.+?)(?:\s*volume:|$)', body.lower())
        if m:
            volume = m.group(1).strip()

        # Parse sold listings: date line followed by title+price line
        lines = body.split('\n')
        current_date = None
        in_sold_section = False

        for line in lines:
            line = line.strip()
            if 'Sale Date' in line:
                in_sold_section = True
                continue
            if not in_sold_section:
                continue
            if 'See an incorrect' in line:
                break

            # Date line: YYYY-MM-DD
            date_m = re.match(r'^(\d{4}-\d{2}-\d{2})$', line)
            if date_m:
                current_date = date_m.group(1)
                continue

            # Sold listing line: title [eBay] $price
            if '[eBay]' in line and current_date:
                price_m = re.search(r'\$(\d[\d,]*\.\d{2})', line)
                price = float(price_m.group(1).replace(',', '')) if price_m else 0
                title = re.sub(r'\s*\[eBay\].*$', '', line).strip()
                if title and len(title) > 10:
                    sales.append({'date': current_date, 'title': title, 'price': price})
                current_date = None
    except:
        pass

    # Compute real velocity from dates
    now = datetime.now()
    current_year = now.year
    sales_this_year = [s for s in sales if s['date'].startswith(str(current_year))]
    sales_last_90d = [s for s in sales
                      if (now - datetime.strptime(s['date'], '%Y-%m-%d')).days <= 90]

    # Median price from this year's sales (or all if none this year)
    price_source = sales_this_year or sales
    prices = sorted(s['price'] for s in price_source if s['price'] > 0)
    median_price = 0
    if prices:
        mid = len(prices) // 2
        median_price = prices[mid] if len(prices) % 2 else (prices[mid-1] + prices[mid]) / 2

    # Common keywords from sold titles
    keywords = {}
    for s in sales:
        words = set(w.lower() for w in re.split(r'[^a-zA-Z0-9]+', s['title']) if len(w) >= 3)
        for w in words:
            keywords[w] = keywords.get(w, 0) + 1
    threshold = max(len(sales) * 0.5, 2)
    common_keywords = [kw for kw, cnt in sorted(keywords.items(), key=lambda x: -x[1])
                       if cnt >= threshold]

    return {
        'volume': volume,
        'sales': sales[:30],
        'sales_this_year': len(sales_this_year),
        'sales_last_90d': len(sales_last_90d),
        'sold_count': len(sales),
        'median_price': median_price,
        'common_keywords': common_keywords[:15],
        'newest_sale': sales[0]['date'] if sales else None,
        'oldest_sale': sales[-1]['date'] if sales else None,
    }


def main():
    parser = argparse.ArgumentParser(description='SCP Volume Worm')
    parser.add_argument('--limit', type=int, default=500, help='Max pages to scrape')
    parser.add_argument('--stale-days', type=int, default=7,
                        help='Only scrape cards not updated in N days')
    args = parser.parse_args()

    db = SessionLocal()

    # Load stale 2020-2026 cache entries and extract variant URLs
    print("Loading targets from SCP cache (2020-2026, stale)...")
    rows = db.execute(text(
        "SELECT id, player_name, card_year, card_number, variants FROM scp_cache "
        "WHERE card_year BETWEEN 2020 AND 2026 "
        "AND LENGTH(player_name) < 40 AND position(',' in player_name) = 0 "
        "AND created_at < NOW() - INTERVAL '" + str(args.stale_days) + " days' "
        "ORDER BY player_name"
    )).fetchall()
    print(f"  Loaded {len(rows)} cache rows")

    # Extract variant URLs grouped by player
    from collections import defaultdict
    from itertools import zip_longest

    by_player = defaultdict(list)
    seen_urls = set()
    for row in rows:
        v = row.variants
        if isinstance(v, str): v = json.loads(v)
        if not isinstance(v, list): continue
        player = row.player_name.strip()
        for x in v:
            url = x.get('url') or ''
            if url and 'sportscardspro.com' in url and url not in seen_urls:
                seen_urls.add(url)
                by_player[player].append({
                    'cache_id': row.id, 'url': url,
                    'player': player, 'year': row.card_year,
                    'number': row.card_number, 'parallel': x.get('parallel', 'Base'),
                    'price': float(x.get('ungraded') or 0),
                })

    # Interleave players (one card per player per round)
    players_list = sorted(by_player.keys(), key=lambda p: -len(by_player[p]))
    player_iters = [iter(by_player[p]) for p in players_list]
    unique = []
    while player_iters:
        next_round = []
        for it in player_iters:
            card = next(it, None)
            if card:
                unique.append(card)
                next_round.append(it)
        player_iters = next_round

    del rows, by_player, seen_urls  # free memory

    print(f"SCP Volume Worm")
    print(f"  Targets: {len(unique)} cards (stale > {args.stale_days} days)")
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
    current_year = datetime.now().year

    for entry in unique[:args.limit]:
        result = extract_volume_from_page(driver, entry['url'])
        scraped += 1

        sales_count = result['sold_count']
        sales_yr = result['sales_this_year']

        if sales_count > 0:
            found_volume += 1

            # Update the SCP cache with real sale data
            try:
                cache_row = db.execute(text(
                    "SELECT id, variants FROM scp_cache WHERE id = :id"
                ), {"id": entry['cache_id']}).fetchone()
                if cache_row:
                    variants = cache_row.variants
                    if isinstance(variants, str): variants = json.loads(variants)
                    for vv in variants:
                        if vv.get('url') == entry['url']:
                            vv['volume'] = result['volume']
                            vv['common_keywords'] = result['common_keywords']
                            vv['sold_count_scp'] = sales_count
                            vv['sales_this_year'] = sales_yr
                            vv['sales_last_90d'] = result['sales_last_90d']
                            vv['newest_sale'] = result['newest_sale']
                            vv['oldest_sale'] = result['oldest_sale']
                            # Store the actual sale records (dates + prices)
                            vv['sold_history'] = [
                                {'date': s['date'], 'price': s['price']}
                                for s in result['sales'][:20]
                            ]
                            # Update price from median of this year's sales
                            if result['median_price'] > 0:
                                old_price = float(vv.get('ungraded') or 0)
                                vv['ungraded'] = round(result['median_price'], 2)
                                if old_price > 0 and abs(old_price - result['median_price']) / old_price > 0.3:
                                    print(f"           PRICE UPDATE: ${old_price:.2f} -> ${result['median_price']:.2f}")
                            break
                    db.execute(text(
                        "UPDATE scp_cache SET variants = :v, created_at = NOW() WHERE id = :id"
                    ), {"v": json.dumps(variants), "id": entry['cache_id']})
                    db.commit()
            except Exception as e:
                errors += 1

            # Liquid = 2+ sales this year
            is_liquid = sales_yr >= 2
            if is_liquid:
                liquid += 1
                kws = ', '.join(result['common_keywords'][:5])
                print(f"  [{scraped}] LIQUID ({sales_yr} sales {current_year}): ${entry['price']:.2f} {entry['player']} #{entry['number']} [{entry['parallel']}]")
                print(f"           vol_label=\"{result['volume']}\" | median=${result['median_price']:.2f} | keywords: {kws}")
            elif scraped <= 20 or scraped % 50 == 0:
                print(f"  [{scraped}] {sales_yr} sales {current_year} (total={sales_count}): ${entry['price']:.2f} {entry['player']} #{entry['number']}")
        elif scraped <= 10 or scraped % 100 == 0:
            print(f"  [{scraped}] no sales: {entry['player']} #{entry['number']} [{entry['parallel']}]")

    driver.quit()
    db.close()

    print(f"\n{'=' * 60}")
    print(f"SCP Volume Worm Complete")
    print(f"  Scraped: {scraped}")
    print(f"  Has sold data: {found_volume}")
    print(f"  Liquid (2+ sales {current_year}): {liquid}")
    print(f"  Errors: {errors}")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
