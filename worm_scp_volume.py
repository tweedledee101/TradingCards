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

    return {
        'volume': volume,
        'sold_titles': sold_titles[:20],
        'sold_prices': sold_prices[:20],
        'common_keywords': common_keywords[:15],
        'sold_count': len(sold_titles),
    }


def main():
    parser = argparse.ArgumentParser(description='SCP Volume Worm')
    parser.add_argument('--limit', type=int, default=100, help='Max pages to scrape')
    parser.add_argument('--min-price', type=float, default=20)
    parser.add_argument('--max-price', type=float, default=200)
    args = parser.parse_args()

    db = SessionLocal()

    # Get SCP cache entries with URLs in the sweet spot, no volume yet
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
            if (price and args.min_price <= float(price) <= args.max_price
                    and url and 'sportscardspro.com' in url and not vol):
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

    # Sort: popular players first (more SCP entries = more likely to have liquid cards)
    from collections import Counter
    player_counts = Counter(t['player'] for t in unique)
    unique.sort(key=lambda x: (-player_counts[x['player']], abs(x['price'] - 75)))

    print(f"SCP Volume Worm")
    print(f"  Targets: {len(unique)} cards in ${args.min_price}-${args.max_price}")
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
                            break
                    db.execute(text(
                        "UPDATE scp_cache SET variants = :v WHERE id = :id"
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
