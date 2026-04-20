"""
Mercari scraper for trading card price comparison and arbitrage.

Uses Playwright (Chromium) to bypass Cloudflare. Mercari has casual sellers
who frequently misprice cards. 10% seller fee, often free shipping.

Install: python -m pip install playwright && python -m playwright install chromium

Usage:
    python backend/scrapers/mercari_scraper.py "aaron judge 2024 topps chrome"
    python backend/scrapers/mercari_scraper.py "bobby witt jr refractor" --compare-scp
"""
from __future__ import annotations

import json
import re
import time
from typing import List, Dict, Optional


MERCARI_BASE = 'https://www.mercari.com'
MERCARI_FEE_SELLER = 0.10


def search_mercari(
    query: str,
    max_results: int = 30,
    headless: bool = True,
    status: str = 'on_sale',
) -> List[Dict]:
    """Search Mercari for trading card listings using Playwright."""
    from playwright.sync_api import sync_playwright

    url = f'{MERCARI_BASE}/search/?keyword={query.replace(" ", "+")}'
    if status == 'sold_out':
        url += '&status=sold_out'
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 720},
        )
        page = ctx.new_page()

        try:
            page.goto(url, wait_until='networkidle', timeout=30000)
            # Wait for search results to render
            page.wait_for_timeout(3000)

            # Try to extract from __NEXT_DATA__ first (fastest, most structured)
            next_data = _extract_next_data(page)
            if next_data:
                results = _parse_next_data_items(next_data, max_results)

            # Fallback: parse visible DOM elements
            if not results:
                results = _parse_dom_items(page, max_results)

        except Exception as e:
            print(f'Mercari search error: {e}')
        finally:
            browser.close()

    return results


def _extract_next_data(page) -> Optional[dict]:
    """Extract __NEXT_DATA__ JSON from the page if available."""
    try:
        el = page.query_selector('script#__NEXT_DATA__')
        if el:
            return json.loads(el.inner_text())
    except Exception:
        pass
    return None


def _parse_next_data_items(data: dict, max_results: int) -> List[Dict]:
    """Parse items from Mercari's Next.js page data."""
    results = []
    props = data.get('props', {}).get('pageProps', {})

    # Try multiple possible locations for search results
    items = []
    for key in ['searchResults', 'items', 'data', 'initialData', 'itemsList']:
        val = props.get(key)
        if isinstance(val, list) and val:
            items = val
            break
        elif isinstance(val, dict):
            for subkey in ['items', 'data', 'results']:
                subval = val.get(subkey)
                if isinstance(subval, list) and subval:
                    items = subval
                    break
            if items:
                break

    for item in items[:max_results]:
        parsed = _normalize_mercari_item(item)
        if parsed:
            results.append(parsed)

    return results


def _parse_dom_items(page, max_results: int) -> List[Dict]:
    """Parse items from visible DOM elements as fallback."""
    results = []

    # Mercari uses various selectors for item cards
    selectors = [
        '[data-testid="ItemCell"]',
        '[data-testid="SearchResults"] a',
        'a[href*="/item/"]',
        '.sc-bczRLJ',  # Mercari styled component
    ]

    items = []
    for sel in selectors:
        items = page.query_selector_all(sel)
        if items:
            break

    for el in items[:max_results]:
        try:
            href = el.get_attribute('href') or ''
            text = el.inner_text()
            lines = [l.strip() for l in text.split('\n') if l.strip()]

            # Extract price (usually has $ sign)
            price = None
            title = ''
            for line in lines:
                if '$' in line and not price:
                    m = re.search(r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)', line)
                    if m:
                        price = float(m.group(1).replace(',', ''))
                elif len(line) > 10 and not price:
                    title = line

            if not title and lines:
                title = lines[0]

            item_id = ''
            id_match = re.search(r'/item/([a-zA-Z0-9]+)', href)
            if id_match:
                item_id = id_match.group(1)

            if title and price and price > 0:
                results.append({
                    'title': title[:200],
                    'price': price,
                    'url': f'{MERCARI_BASE}{href}' if href.startswith('/') else href,
                    'item_id': item_id,
                    'image_url': '',
                    'source': 'mercari',
                })
        except Exception:
            continue

    return results


def _normalize_mercari_item(item: dict) -> Optional[Dict]:
    """Normalize a Mercari item from any data source into standard format."""
    if not item:
        return None

    # Handle various field names across API versions
    item_id = str(item.get('id', item.get('itemId', item.get('objectID', ''))))
    name = item.get('name', item.get('title', item.get('itemName', '')))

    price = 0
    price_val = item.get('price', item.get('itemPrice', 0))
    if isinstance(price_val, dict):
        price = float(price_val.get('amount', price_val.get('value', 0)))
        # Mercari sometimes returns cents
        if price > 10000:
            price = price / 100
    elif isinstance(price_val, (int, float)):
        price = float(price_val)

    if not name or price <= 0:
        return None

    # Image
    image_url = ''
    photos = item.get('photos', item.get('thumbnails', item.get('imageUrls', [])))
    if photos:
        if isinstance(photos[0], dict):
            image_url = photos[0].get('url', photos[0].get('imageUrl', ''))
        elif isinstance(photos[0], str):
            image_url = photos[0]
    if not image_url:
        image_url = item.get('imageUrl', item.get('thumbnailUrl', ''))

    # Shipping
    shipping_included = False
    ship = item.get('shippingPayer', item.get('shippingClass', {}))
    if isinstance(ship, dict):
        shipping_included = ship.get('id') == 2 or ship.get('name', '').lower() == 'seller'
    elif isinstance(ship, str):
        shipping_included = 'seller' in ship.lower()

    return {
        'title': name[:200],
        'price': price,
        'url': f'{MERCARI_BASE}/us/item/{item_id}/' if item_id else '',
        'item_id': item_id,
        'image_url': image_url,
        'source': 'mercari',
        'status': item.get('status', ''),
        'condition': item.get('itemCondition', {}).get('name', '') if isinstance(item.get('itemCondition'), dict) else str(item.get('itemCondition', '')),
        'shipping_included': shipping_included,
        'seller': item.get('seller', {}).get('name', '') if isinstance(item.get('seller'), dict) else '',
    }


def extract_card_identity(title: str) -> Dict:
    """Best-effort card identity extraction from a Mercari listing title."""
    result = {'player_name': None, 'card_year': None, 'card_set': None,
              'card_number': None, 'parallel': None}
    if not title:
        return result

    year_match = re.search(r'\b(19[89]\d|20\d{2})\b', title)
    if year_match:
        result['card_year'] = int(year_match.group(1))

    num_match = re.search(r'#([A-Za-z0-9-]+)', title)
    if num_match:
        result['card_number'] = num_match.group(1)

    return result


if __name__ == '__main__':
    import argparse, sys, os

    parser = argparse.ArgumentParser(description='Mercari trading card scraper')
    parser.add_argument('query', help='Search query')
    parser.add_argument('--max-results', type=int, default=20)
    parser.add_argument('--headed', action='store_true', help='Show browser')
    parser.add_argument('--sold', action='store_true', help='Search sold listings')
    parser.add_argument('--compare-scp', action='store_true')
    args = parser.parse_args()

    status = 'sold_out' if args.sold else 'on_sale'
    print(f'Searching Mercari for: {args.query} (status={status})')
    results = search_mercari(args.query, max_results=args.max_results,
                             headless=not args.headed, status=status)

    print(f'\nFound {len(results)} results:')
    for r in results:
        price = f"${r['price']:.2f}" if r.get('price') else '?'
        ship = ' (free ship)' if r.get('shipping_included') else ''
        print(f"  {price}{ship} | {r['title'][:80]}")
        if r.get('url'):
            print(f"         {r['url']}")

    if args.compare_scp and results:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend', '.env'))
        from contextlib import closing
        from backend.utils.database import SessionLocal
        from backend.services.marketplace_adapter import calculate_arbitrage

        with closing(SessionLocal()) as db:
            from sqlalchemy import text
            for r in results:
                identity = extract_card_identity(r['title'])
                if not identity.get('card_year') or not identity.get('card_number'):
                    continue
                # Quick SCP lookup
                scp = db.execute(text("""
                    SELECT (v->>'ungraded')::numeric as price
                    FROM scp_cache sc, jsonb_array_elements(sc.variants) v
                    WHERE sc.card_year = :y AND sc.card_number ILIKE :n
                    AND (v->>'ungraded')::numeric > 0
                    ORDER BY (v->>'ungraded')::numeric DESC LIMIT 1
                """), {'y': identity['card_year'], 'n': identity['card_number']}).first()
                if scp:
                    arb = calculate_arbitrage(r['price'], 'mercari', float(scp.price), 'ebay')
                    if arb['profit'] > 5:
                        print(f"  ** ARBITRAGE: buy ${r['price']:.2f} Mercari -> sell ${float(scp.price):.2f} eBay = ${arb['profit']:.2f} profit")
