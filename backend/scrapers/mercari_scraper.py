"""
Mercari scraper for trading card price comparison and arbitrage.

Mercari has casual sellers who frequently misprice cards. 10% seller fee.
Unlike COMC, Mercari's search API is accessible without Cloudflare challenge
via their mobile API endpoint.

URL patterns:
- Search: https://www.mercari.com/search/?keyword=aaron+judge+2024+topps+chrome
- Item:   https://www.mercari.com/us/item/m12345678/
- API:    https://api.mercari.com/v2/entities:search (POST, JSON)
"""
from __future__ import annotations

import json
import re
import time
import requests
from typing import List, Dict, Optional


MERCARI_FEE_SELLER = 0.10  # 10% seller fee
MERCARI_SEARCH_URL = 'https://api.mercari.com/v2/entities:search'

# Mercari mobile API headers (public, no auth needed)
_HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'User-Agent': 'Mercari/1 CFNetwork/1568.200.51 Darwin/24.1.0',
    'X-Platform': 'web',
}


def search_mercari(
    query: str,
    max_results: int = 30,
    status: str = 'on_sale',
    sort: str = 'SORT_SCORE',
) -> List[Dict]:
    """Search Mercari for trading card listings.

    Args:
        query: Search text (e.g. "aaron judge 2024 topps chrome refractor")
        max_results: Max results to return
        status: 'on_sale' (active), 'sold_out' (completed sales), or 'all'
        sort: SORT_SCORE (relevance), SORT_PRICE_ASC, SORT_PRICE_DESC, SORT_CREATED_TIME

    Returns list of listing dicts with: title, price, url, image_url, status, etc.
    """
    payload = {
        'keyword': query,
        'limit': min(max_results, 120),
        'defaultDatasets': ['DATASET_TYPE_MERCARI'],
        'searchSessionId': '',
        'indexRouting': 'INDEX_ROUTING_UNSPECIFIED',
        'searchCondition': {
            'sort': sort,
            'order': 'ORDER_DESC',
            'status': [status] if status != 'all' else ['STATUS_ON_SALE', 'STATUS_SOLD_OUT'],
            'categoryId': [2536],  # Trading Cards category
        },
    }

    try:
        resp = requests.post(
            MERCARI_SEARCH_URL,
            headers=_HEADERS,
            json=payload,
            timeout=15,
        )

        if resp.status_code == 403:
            # Mercari may block datacenter IPs. Try alternate approach.
            return _search_mercari_web(query, max_results)

        if resp.status_code != 200:
            print(f'Mercari API HTTP {resp.status_code}: {resp.text[:200]}')
            return []

        data = resp.json()
        items = data.get('items', [])
        return [_parse_mercari_item(item) for item in items if item]

    except requests.exceptions.RequestException as e:
        print(f'Mercari search error: {e}')
        return []


def _search_mercari_web(query: str, max_results: int = 30) -> List[Dict]:
    """Fallback: scrape Mercari web search results via HTML."""
    url = f'https://www.mercari.com/search/?keyword={requests.utils.quote(query)}&categoryId=2536'
    try:
        resp = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }, timeout=15)
        if resp.status_code != 200:
            print(f'Mercari web HTTP {resp.status_code}')
            return []

        # Look for JSON data embedded in the page (Next.js __NEXT_DATA__)
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text)
        if not match:
            return []

        page_data = json.loads(match.group(1))
        # Navigate the Next.js data structure to find search results
        props = page_data.get('props', {}).get('pageProps', {})
        items = props.get('searchResults', props.get('items', []))

        results = []
        for item in items[:max_results]:
            parsed = _parse_mercari_web_item(item)
            if parsed:
                results.append(parsed)
        return results

    except Exception as e:
        print(f'Mercari web fallback error: {e}')
        return []


def _parse_mercari_item(item: dict) -> Dict:
    """Parse a Mercari API search result item."""
    item_id = item.get('id', '')
    price = 0
    price_obj = item.get('price') or {}
    if isinstance(price_obj, dict):
        price = float(price_obj.get('amount', 0)) / 100  # cents to dollars
    elif isinstance(price_obj, (int, float)):
        price = float(price_obj)

    thumbnails = item.get('thumbnails', [])
    image_url = thumbnails[0] if thumbnails else ''

    return {
        'title': item.get('name', ''),
        'price': price,
        'url': f'https://www.mercari.com/us/item/{item_id}/',
        'image_url': image_url,
        'status': item.get('status', ''),
        'item_id': item_id,
        'source': 'mercari',
        'seller': item.get('seller', {}).get('name', ''),
        'condition': item.get('itemCondition', {}).get('name', ''),
        'shipping_included': item.get('shippingPayer', {}).get('id') == 2,  # seller pays
    }


def _parse_mercari_web_item(item: dict) -> Optional[Dict]:
    """Parse a Mercari web/Next.js search result item."""
    if not item:
        return None
    item_id = item.get('id', item.get('itemId', ''))
    price = float(item.get('price', 0))
    image_url = ''
    photos = item.get('photos', item.get('thumbnails', []))
    if photos:
        if isinstance(photos[0], dict):
            image_url = photos[0].get('url', photos[0].get('imageUrl', ''))
        elif isinstance(photos[0], str):
            image_url = photos[0]

    return {
        'title': item.get('name', item.get('title', '')),
        'price': price,
        'url': f'https://www.mercari.com/us/item/{item_id}/',
        'image_url': image_url,
        'item_id': str(item_id),
        'source': 'mercari',
        'status': item.get('status', ''),
    }


def find_mercari_arbitrage(
    query: str,
    scp_db,
    min_profit: float = 10.0,
    max_buy_price: float = 200.0,
) -> List[Dict]:
    """Search Mercari and cross-reference with SCP for arbitrage opportunities.

    Buy on Mercari (10% fee to seller, free to buyer if shipping included),
    sell on eBay at SCP price minus 13% fees.
    """
    from sqlalchemy import text

    listings = search_mercari(query, max_results=50)
    if not listings:
        return []

    opportunities = []
    for listing in listings:
        price = listing.get('price', 0)
        if not price or price > max_buy_price or price < 1:
            continue

        title = listing.get('title', '')
        # Extract identity from title (reuse existing extraction logic)
        identity = _extract_card_identity_from_title(title)
        if not identity.get('player_name') or not identity.get('card_number'):
            continue

        # SCP lookup
        row = scp_db.execute(text("""
            SELECT v->>'ungraded' as price, v->>'parallel' as parallel, v->>'volume' as volume
            FROM scp_cache sc, jsonb_array_elements(sc.variants) v
            WHERE sc.player_name ILIKE :player
              AND sc.card_year = :year
              AND sc.card_number ILIKE :number
              AND (v->>'ungraded')::numeric > 0
            ORDER BY (v->>'ungraded')::numeric DESC
            LIMIT 1
        """), {
            'player': identity['player_name'],
            'year': identity.get('card_year'),
            'number': str(identity['card_number']),
        }).first()

        if not row:
            continue

        scp_price = float(row.price)
        # Mercari: buyer pays listing price (+ shipping if not included)
        buy_cost = price + (0 if listing.get('shipping_included') else 5.00)
        ebay_net = scp_price * (1 - 0.13)
        profit = ebay_net - buy_cost

        if profit >= min_profit:
            opportunities.append({
                **listing,
                **identity,
                'scp_price': scp_price,
                'scp_volume': row.volume,
                'buy_cost': round(buy_cost, 2),
                'ebay_net': round(ebay_net, 2),
                'profit': round(profit, 2),
                'roi': round((profit / buy_cost) * 100, 1),
                'arbitrage_path': 'mercari -> ebay',
            })

    return sorted(opportunities, key=lambda x: x['profit'], reverse=True)


def _extract_card_identity_from_title(title: str) -> Dict:
    """Best-effort card identity extraction from a Mercari listing title."""
    result = {'player_name': None, 'card_year': None, 'card_set': None,
              'card_number': None, 'parallel': None}

    if not title:
        return result

    # Year
    year_match = re.search(r'\b(19[89]\d|20\d{2})\b', title)
    if year_match:
        result['card_year'] = int(year_match.group(1))

    # Card number
    num_match = re.search(r'#([A-Za-z0-9-]+)', title)
    if num_match:
        result['card_number'] = num_match.group(1)

    # Player name is harder without a roster -- take the first capitalized
    # multi-word sequence that isn't a known set name
    _SET_WORDS = {'topps', 'bowman', 'chrome', 'prizm', 'select', 'mosaic',
                  'panini', 'heritage', 'stadium', 'club', 'finest', 'update',
                  'series', 'draft', 'optic', 'donruss', 'fleer', 'upper', 'deck'}
    words = title.split()
    name_parts = []
    for w in words:
        clean = re.sub(r'[^a-zA-Z]', '', w)
        if clean and clean[0].isupper() and clean.lower() not in _SET_WORDS:
            name_parts.append(w.strip(',').strip())
        elif name_parts and len(name_parts) >= 2:
            break
        elif name_parts:
            name_parts = []
    if len(name_parts) >= 2:
        result['player_name'] = ' '.join(name_parts[:4])

    return result


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Mercari trading card scraper')
    parser.add_argument('query', help='Search query')
    parser.add_argument('--max-results', type=int, default=20)
    parser.add_argument('--sold', action='store_true', help='Search sold listings')
    parser.add_argument('--compare-scp', action='store_true', help='Cross-reference with SCP')
    parser.add_argument('--min-profit', type=float, default=10.0)
    args = parser.parse_args()

    status = 'sold_out' if args.sold else 'on_sale'
    print(f'Searching Mercari for: {args.query} (status={status})')

    results = search_mercari(args.query, max_results=args.max_results, status=status)
    print(f'\nFound {len(results)} results:')
    for r in results[:20]:
        price = f"${r['price']:.2f}" if r.get('price') else '?'
        ship = ' (free ship)' if r.get('shipping_included') else ''
        print(f"  {price}{ship} | {r['title'][:80]}")

    if args.compare_scp and results:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend', '.env'))
        from contextlib import closing
        from backend.utils.database import SessionLocal

        with closing(SessionLocal()) as db:
            opps = find_mercari_arbitrage(args.query, db, min_profit=args.min_profit)

        if opps:
            print(f'\n{len(opps)} arbitrage opportunities (Mercari -> eBay):')
            for o in opps:
                print(f"  ${o['price']:.2f} Mercari -> ${o['scp_price']:.2f} SCP = ${o['profit']:.2f} profit ({o['roi']}% ROI)")
                print(f"    {o['title'][:80]}")
                print(f"    {o['url']}")
        else:
            print('\nNo arbitrage opportunities found.')
