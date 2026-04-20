"""
ShopGoodwill scraper - online Goodwill auctions for donated card collections.

ShopGoodwill.com auctions donated items including trading card collections.
Sellers (Goodwill stores) have zero knowledge of card values -- they price
based on weight/quantity, not individual card worth.

No Cloudflare, no auth needed. HTML is accessible.
Auctions end daily. Nobody runs arbitrage bots against Goodwill.

Usage:
    python backend/scrapers/shopgoodwill_scraper.py "baseball cards"
    python backend/scrapers/shopgoodwill_scraper.py "topps chrome lot" --max-price 50
"""
from __future__ import annotations

import re
import requests
import json
import time
from typing import List, Dict, Optional
from datetime import datetime


SHOPGOODWILL_BASE = 'https://shopgoodwill.com'
SHOPGOODWILL_API = 'https://buyerapi.shopgoodwill.com/api'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'


def search_shopgoodwill(
    query: str,
    max_price: Optional[float] = None,
    max_results: int = 30,
    category: str = None,
) -> List[Dict]:
    """Search ShopGoodwill for trading card auctions.

    Tries the buyer API first (JSON), falls back to HTML scraping.
    """
    # Try API first
    results = _search_via_api(query, max_price, max_results)
    if results:
        return results

    # Fallback: HTML scraping
    return _search_via_html(query, max_price, max_results)


def _search_via_api(query: str, max_price: Optional[float], max_results: int) -> List[Dict]:
    """Search via ShopGoodwill buyer API."""
    try:
        payload = {
            'searchText': query,
            'searchDescriptions': True,
            'sortColumn': 'EndingDateTime',
            'sortDescending': False,  # Ending soonest first
            'page': 1,
            'pageSize': min(max_results, 40),
            'categoryId': -1,  # All categories
            'categoryLevelNo': 0,
            'lowPrice': 0,
            'highPrice': int(max_price) if max_price else 999999,
            'closedAuctions': False,
            'sellerIds': '',
        }

        resp = requests.post(
            f'{SHOPGOODWILL_API}/Search/ItemListing',
            headers={
                'User-Agent': UA,
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            json=payload,
            timeout=15,
        )

        if resp.status_code != 200:
            return []

        data = resp.json()
        items = data.get('searchResults', data.get('items', []))
        if isinstance(data, list):
            items = data

        return [_parse_api_item(item) for item in items[:max_results] if item]

    except Exception as e:
        print(f'ShopGoodwill API error: {e}')
        return []


def _search_via_html(query: str, max_price: Optional[float], max_results: int) -> List[Dict]:
    """Fallback: parse HTML search results."""
    params = {
        'st': query,
        'sg': '',
        'c': '',
        's': '',
        'lp': '0',
        'hp': str(int(max_price)) if max_price else '999999',
        'sbn': '',
        'spo': 'false',
        'snpo': 'false',
        'socs': 'false',
        'sd': 'false',
        'sca': 'false',
        'page': '1',
        'sc': '0',
        'sl': 'false',
        'ss': '0',
    }

    try:
        resp = requests.get(
            f'{SHOPGOODWILL_BASE}/categories/listing',
            params=params,
            headers={'User-Agent': UA},
            timeout=15,
        )

        if resp.status_code != 200:
            return []

        return _parse_html_results(resp.text, max_results)

    except Exception as e:
        print(f'ShopGoodwill HTML error: {e}')
        return []


def _parse_api_item(item: dict) -> Dict:
    """Parse a ShopGoodwill API result item."""
    item_id = item.get('itemId', item.get('id', ''))
    title = item.get('title', item.get('name', ''))
    current_price = float(item.get('currentPrice', item.get('price', 0)))
    num_bids = item.get('numberOfBids', item.get('bidCount', 0))
    end_time = item.get('endDateTime', item.get('endTime', ''))
    image_url = item.get('imageURL', item.get('imageUrl', item.get('thumbnailUrl', '')))
    seller = item.get('sellerName', item.get('seller', ''))

    return {
        'title': title[:200],
        'price': current_price,
        'num_bids': num_bids,
        'url': f'{SHOPGOODWILL_BASE}/item/{item_id}' if item_id else '',
        'item_id': str(item_id),
        'image_url': image_url,
        'end_time': end_time,
        'seller': seller,
        'source': 'shopgoodwill',
        'listing_type': 'lot' if _is_likely_lot(title) else 'single',
    }


def _parse_html_results(html: str, max_results: int) -> List[Dict]:
    """Parse ShopGoodwill HTML search results."""
    results = []

    # ShopGoodwill uses Angular/React -- data might be in JSON embedded in page
    # Look for __NEXT_DATA__ or inline JSON
    json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, re.S)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            items = data.get('search', {}).get('items', [])
            return [_parse_api_item(item) for item in items[:max_results]]
        except:
            pass

    # Try finding item cards in HTML
    items = re.findall(
        r'<div[^>]*class="[^"]*item-card[^"]*"[^>]*>(.*?)</div>\s*</div>',
        html, re.S
    )

    if not items:
        # Try finding any links with prices
        links = re.findall(r'href="(/item/\d+)"[^>]*>(.*?)</a>', html, re.S)
        for href, text in links[:max_results]:
            clean = re.sub(r'<[^>]+>', ' ', text).strip()
            if len(clean) > 10:
                price_match = re.search(r'\$?([\d,]+\.?\d*)', clean)
                results.append({
                    'title': clean[:200],
                    'price': float(price_match.group(1).replace(',', '')) if price_match else None,
                    'url': f'{SHOPGOODWILL_BASE}{href}',
                    'source': 'shopgoodwill',
                    'listing_type': 'lot' if _is_likely_lot(clean) else 'single',
                })

    return results


def _is_likely_lot(title: str) -> bool:
    """Detect if listing is a lot/collection."""
    t = title.lower()
    return bool(re.search(
        r'lot|collection|bundle|bulk|estate|box of|tub of|\d{2,}\s*cards?|assorted|mixed|misc',
        t
    ))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='ShopGoodwill card scraper')
    parser.add_argument('query', help='Search query')
    parser.add_argument('--max-price', type=float, default=100)
    parser.add_argument('--max-results', type=int, default=20)
    args = parser.parse_args()

    print(f'Searching ShopGoodwill for: {args.query} (max ${args.max_price})')
    results = search_shopgoodwill(args.query, max_price=args.max_price, max_results=args.max_results)

    print(f'\nFound {len(results)} results:')
    lots = [r for r in results if r.get('listing_type') == 'lot']
    singles = [r for r in results if r.get('listing_type') != 'lot']
    print(f'  Lots: {len(lots)} | Singles: {len(singles)}')

    for r in results[:15]:
        price = f"${r['price']:.2f}" if r.get('price') else '?'
        tag = '[LOT]' if r.get('listing_type') == 'lot' else '[SGL]'
        bids = f" ({r['num_bids']} bids)" if r.get('num_bids') else ''
        print(f"  {tag} {price:>8}{bids} | {r['title'][:70]}")
        if r.get('url'):
            print(f"         {r['url']}")
