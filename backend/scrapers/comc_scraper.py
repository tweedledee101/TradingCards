"""
COMC (CheckOutMyCards) scraper for trading card price comparison.

COMC has fixed-price listings with structured data (player, year, set, card number,
parallel, condition, price). Useful for:
- Cross-platform arbitrage: COMC price vs eBay/SCP price
- Price discovery for cards without SCP data
- Inventory sourcing (20% seller fee but 5% buyer fee)

Requires Playwright (Chromium) to bypass Cloudflare challenge.
Install: python -m pip install playwright && python -m playwright install chromium

URL patterns:
- Search: https://www.comc.com/Cards/Baseball?search=aaron+judge+2024+topps+chrome
- Card:   https://www.comc.com/Cards/Baseball/2024/Topps_Chrome/1/Aaron_Judge/12345678
- Browse: https://www.comc.com/Cards/Baseball/2025/Topps_Chrome,sc,Physical,i100
"""
from __future__ import annotations

import re
import time
from typing import List, Dict, Optional


COMC_BASE = 'https://www.comc.com'
COMC_FEE_BUYER = 0.05   # 5% buyer fee
COMC_FEE_SELLER = 0.20  # 20% seller fee


def search_comc(query: str, sport: str = 'Baseball', max_results: int = 50,
                headless: bool = True) -> List[Dict]:
    """Search COMC for cards matching query. Returns structured listing data.

    Each result dict has: title, price, player_name, card_year, card_set,
    card_number, parallel, condition, url, image_url.
    """
    from playwright.sync_api import sync_playwright

    url = f'{COMC_BASE}/Cards/{sport}?search={query.replace(" ", "+")}'
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.set_default_timeout(30000)

        try:
            page.goto(url, wait_until='networkidle', timeout=60000)
            # Wait for Cloudflare challenge to resolve
            page.wait_for_selector('.cardResult, .noResults, #searchResults', timeout=30000)

            cards = page.query_selector_all('.cardResult')
            for card in cards[:max_results]:
                try:
                    result = _parse_card_element(card)
                    if result:
                        results.append(result)
                except Exception:
                    continue
        except Exception as e:
            print(f'COMC search error: {e}')
        finally:
            browser.close()

    return results


def _parse_card_element(el) -> Optional[Dict]:
    """Parse a COMC card result element into structured data."""
    title_el = el.query_selector('.cardTitle, .title, a[href*="/Cards/"]')
    price_el = el.query_selector('.price, .cardPrice')
    img_el = el.query_selector('img')

    if not title_el:
        return None

    title = (title_el.inner_text() or '').strip()
    href = title_el.get_attribute('href') or ''
    price_text = (price_el.inner_text() if price_el else '').strip()
    image_url = (img_el.get_attribute('src') if img_el else '') or ''

    price = _parse_price(price_text)
    card_url = f'{COMC_BASE}{href}' if href.startswith('/') else href

    # Parse identity from URL path: /Cards/Baseball/2024/Topps_Chrome/1/Aaron_Judge/...
    identity = _parse_comc_url(href)

    return {
        'title': title,
        'price': price,
        'url': card_url,
        'image_url': image_url,
        'source': 'comc',
        **identity,
    }


def _parse_price(text: str) -> Optional[float]:
    """Extract price from COMC price text like '$12.99' or '12.99'."""
    if not text:
        return None
    m = re.search(r'\$?([\d,]+\.?\d*)', text.replace(',', ''))
    return float(m.group(1)) if m else None


def _parse_comc_url(url: str) -> Dict:
    """Extract card identity from COMC URL path."""
    result = {
        'player_name': None,
        'card_year': None,
        'card_set': None,
        'card_number': None,
        'parallel': None,
    }
    if not url:
        return result

    # URL pattern: /Cards/Baseball/2024/Topps_Chrome/1/Aaron_Judge/...
    parts = url.strip('/').split('/')
    if len(parts) < 4:
        return result

    # Find year (4-digit number)
    for i, part in enumerate(parts):
        if re.match(r'^(19|20)\d{2}$', part):
            result['card_year'] = int(part)
            if i + 1 < len(parts):
                result['card_set'] = parts[i + 1].replace('_', ' ')
            if i + 2 < len(parts):
                result['card_number'] = parts[i + 2]
            # Player name is usually after card number
            if i + 3 < len(parts):
                result['player_name'] = parts[i + 3].replace('_', ' ')
            break

    return result


def compare_comc_to_scp(comc_results: List[Dict], scp_cache_db) -> List[Dict]:
    """Cross-reference COMC listings against SCP prices to find arbitrage.

    Returns opportunities where COMC price + buyer fee < SCP price * (1 - eBay seller fee).
    """
    from sqlalchemy import text

    opportunities = []
    for listing in comc_results:
        if not listing.get('price') or not listing.get('player_name'):
            continue

        player = listing['player_name']
        year = listing.get('card_year')
        number = listing.get('card_number')

        if not year or not number:
            continue

        # Look up SCP price
        row = scp_cache_db.execute(text("""
            SELECT v->>'ungraded' as price, v->>'parallel' as parallel, v->>'volume' as volume
            FROM scp_cache sc, jsonb_array_elements(sc.variants) v
            WHERE sc.player_name ILIKE :player
              AND sc.card_year = :year
              AND sc.card_number ILIKE :number
              AND (v->>'ungraded')::numeric > 0
            ORDER BY (v->>'ungraded')::numeric DESC
            LIMIT 1
        """), {'player': player, 'year': year, 'number': str(number)}).first()

        if not row:
            continue

        scp_price = float(row.price)
        comc_total = listing['price'] * (1 + COMC_FEE_BUYER)  # What you'd pay on COMC
        ebay_net = scp_price * (1 - 0.13)  # What you'd net selling on eBay
        profit = ebay_net - comc_total

        if profit > 5:  # Minimum $5 profit
            opportunities.append({
                **listing,
                'scp_price': scp_price,
                'scp_volume': row.volume,
                'comc_total_cost': round(comc_total, 2),
                'ebay_net_after_fees': round(ebay_net, 2),
                'profit': round(profit, 2),
                'roi': round((profit / comc_total) * 100, 1),
            })

    return sorted(opportunities, key=lambda x: x['profit'], reverse=True)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='COMC card scraper')
    parser.add_argument('query', help='Search query (e.g. "aaron judge 2024 topps chrome")')
    parser.add_argument('--sport', default='Baseball')
    parser.add_argument('--max-results', type=int, default=20)
    parser.add_argument('--headed', action='store_true', help='Show browser window')
    parser.add_argument('--compare-scp', action='store_true', help='Cross-reference with SCP prices')
    args = parser.parse_args()

    print(f'Searching COMC for: {args.query}')
    results = search_comc(args.query, sport=args.sport, max_results=args.max_results,
                          headless=not args.headed)

    print(f'\nFound {len(results)} results:')
    for r in results:
        price = f"${r['price']:.2f}" if r.get('price') else '?'
        print(f"  {price} | {r['title'][:80]}")
        if r.get('url'):
            print(f"         {r['url']}")

    if args.compare_scp and results:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend', '.env'))
        from contextlib import closing
        from backend.utils.database import SessionLocal

        with closing(SessionLocal()) as db:
            opps = compare_comc_to_scp(results, db)

        if opps:
            print(f'\n{len(opps)} arbitrage opportunities (COMC -> eBay):')
            for o in opps:
                print(f"  ${o['price']:.2f} COMC -> ${o['scp_price']:.2f} SCP = ${o['profit']:.2f} profit ({o['roi']}% ROI)")
                print(f"    {o['title'][:80]}")
        else:
            print('\nNo arbitrage opportunities found.')
