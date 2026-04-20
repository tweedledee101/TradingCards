"""
Craigslist scraper for trading card lots and singles.

Plain HTML, no Cloudflare, no auth. Prices visible in search results.
Local pickup = no shipping cost = higher margin.

Searches multiple metro areas for card lots and underpriced singles.
Feeds results into the lot vision pipeline for value analysis.

Usage:
    python backend/scrapers/craigslist_scraper.py "baseball cards lot" --city newyork
    python backend/scrapers/craigslist_scraper.py "topps chrome" --city all --max-price 100
"""
from __future__ import annotations

import re
import requests
import time
from typing import List, Dict, Optional


# Major metro Craigslist subdomains
CITIES = [
    'newyork', 'losangeles', 'chicago', 'houston', 'phoenix',
    'philadelphia', 'sanantonio', 'sandiego', 'dallas', 'sfbay',
    'seattle', 'denver', 'boston', 'atlanta', 'miami',
    'detroit', 'minneapolis', 'tampa', 'stlouis', 'portland',
]

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'


def search_craigslist(
    query: str,
    city: str = 'newyork',
    max_price: Optional[float] = None,
    min_price: Optional[float] = None,
    max_results: int = 30,
) -> List[Dict]:
    """Search Craigslist for-sale listings.

    Args:
        query: Search text (e.g. "baseball cards lot", "topps chrome refractor")
        city: Craigslist subdomain (e.g. 'newyork', 'losangeles', 'sfbay')
        max_price: Max price filter
        min_price: Min price filter
        max_results: Max results to return

    Returns list of listing dicts with title, price, url, location, images.
    """
    params = {
        'query': query,
        'sort': 'date',
    }
    if max_price:
        params['max_price'] = int(max_price)
    if min_price:
        params['min_price'] = int(min_price)

    url = f'https://{city}.craigslist.org/search/sss'

    try:
        resp = requests.get(url, params=params, headers={'User-Agent': UA}, timeout=10)
        if resp.status_code != 200:
            print(f'Craigslist {city} HTTP {resp.status_code}')
            return []

        return _parse_search_results(resp.text, city, max_results)

    except Exception as e:
        print(f'Craigslist {city} error: {e}')
        return []


def search_multiple_cities(
    query: str,
    cities: List[str] = None,
    max_price: Optional[float] = None,
    max_per_city: int = 10,
) -> List[Dict]:
    """Search multiple Craigslist cities for the same query."""
    if cities is None:
        cities = CITIES[:10]  # Top 10 metros by default

    all_results = []
    for city in cities:
        results = search_craigslist(query, city=city, max_price=max_price, max_results=max_per_city)
        all_results.extend(results)
        time.sleep(1.5)  # Be polite

    return all_results


def _parse_search_results(html: str, city: str, max_results: int) -> List[Dict]:
    """Parse Craigslist search results HTML."""
    results = []

    # Craigslist result pattern: <li class="cl-static-search-result">
    # or older: <li class="result-row" data-pid="...">
    # Each has: title link, price, location, date

    # Try new format first
    items = re.findall(
        r'<li[^>]*class="[^"]*cl-static-search-result[^"]*"[^>]*>(.*?)</li>',
        html, re.S
    )

    if not items:
        # Try older format
        items = re.findall(
            r'<li[^>]*class="[^"]*result-row[^"]*"[^>]*>(.*?)</li>',
            html, re.S
        )

    if not items:
        # Try generic approach - find all links with prices
        links = re.findall(
            r'<a[^>]*href="(https?://[^"]*craigslist[^"]*)"[^>]*>(.*?)</a>',
            html, re.S
        )
        for href, text in links[:max_results]:
            clean_text = re.sub(r'<[^>]+>', '', text).strip()
            if len(clean_text) > 10:
                # Find price near this link
                price = None
                price_match = re.search(r'\$(\d[\d,]*)', clean_text)
                if price_match:
                    price = float(price_match.group(1).replace(',', ''))

                results.append({
                    'title': clean_text[:200],
                    'price': price,
                    'url': href,
                    'city': city,
                    'source': 'craigslist',
                    'image_urls': [],
                })
        return results

    for item_html in items[:max_results]:
        listing = _parse_single_result(item_html, city)
        if listing:
            results.append(listing)

    return results


def _parse_single_result(html: str, city: str) -> Optional[Dict]:
    """Parse a single Craigslist search result item."""
    # Title and URL
    title_match = re.search(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', html, re.S)
    if not title_match:
        return None

    url = title_match.group(1)
    title = re.sub(r'<[^>]+>', '', title_match.group(2)).strip()

    if not title or len(title) < 5:
        return None

    # Make URL absolute if relative
    if url.startswith('/'):
        url = f'https://{city}.craigslist.org{url}'

    # Price
    price = None
    price_match = re.search(r'\$(\d[\d,]*)', html)
    if price_match:
        price = float(price_match.group(1).replace(',', ''))

    # Location
    location = None
    loc_match = re.search(r'<span[^>]*class="[^"]*(?:nearby|hood|location)[^"]*"[^>]*>(.*?)</span>', html, re.S)
    if loc_match:
        location = re.sub(r'<[^>]+>', '', loc_match.group(1)).strip().strip('()')

    # Images
    image_urls = re.findall(r'src="(https://images\.craigslist\.org/[^"]+)"', html)

    # Date
    date = None
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', html)
    if date_match:
        date = date_match.group(1)

    return {
        'title': title[:200],
        'price': price,
        'url': url,
        'city': city,
        'location': location,
        'image_urls': image_urls[:5],
        'date': date,
        'source': 'craigslist',
        'listing_type': 'lot' if _is_likely_lot(title) else 'single',
    }


def _is_likely_lot(title: str) -> bool:
    """Detect if a listing is likely a lot/bundle."""
    t = title.lower()
    lot_signals = [
        'lot', 'collection', 'bundle', 'bulk', 'estate',
        'cards total', 'card lot', 'huge', 'massive',
        r'\d{2,}\s*cards', r'\d{2,}\s*card',
    ]
    for signal in lot_signals:
        if re.search(signal, t):
            return True
    return False


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Craigslist card scraper')
    parser.add_argument('query', help='Search query')
    parser.add_argument('--city', default='newyork', help='City or "all" for multi-city')
    parser.add_argument('--max-price', type=float, default=None)
    parser.add_argument('--max-results', type=int, default=20)
    args = parser.parse_args()

    if args.city == 'all':
        print(f'Searching {len(CITIES[:10])} cities for: {args.query}')
        results = search_multiple_cities(args.query, max_price=args.max_price, max_per_city=5)
    else:
        print(f'Searching Craigslist {args.city} for: {args.query}')
        results = search_craigslist(args.query, city=args.city, max_price=args.max_price, max_results=args.max_results)

    print(f'\nFound {len(results)} results:')
    lots = [r for r in results if r.get('listing_type') == 'lot']
    singles = [r for r in results if r.get('listing_type') != 'lot']
    print(f'  Lots: {len(lots)} | Singles: {len(singles)}')

    for r in results[:15]:
        price = f"${r['price']:.0f}" if r.get('price') else '?'
        tag = '[LOT]' if r.get('listing_type') == 'lot' else '[SGL]'
        city = r.get('city', '?')
        imgs = f" ({len(r.get('image_urls', []))} imgs)" if r.get('image_urls') else ''
        print(f"  {tag} {price:>6} | {city:12} | {r['title'][:70]}{imgs}")
        if r.get('url'):
            print(f"         {r['url'][:80]}")
