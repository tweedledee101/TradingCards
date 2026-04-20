"""
Goldin Auctions scraper for high-end trading card price discovery.

Goldin uses Algolia for search (public API keys embedded in their frontend).
No Cloudflare, no Playwright needed -- plain HTTP POST to Algolia.

Goldin is primarily useful for:
- Price discovery on high-end cards ($100+)
- Auction sniping (weekly auctions with known end times)
- Market validation (what cards actually sell for at auction)

Note: Algolia host (74elo4kni1-dsn.algolia.net) may not resolve in WSL
due to DNS issues. Works fine from GitHub Actions / production servers.
"""
from __future__ import annotations

import requests
import re
from typing import List, Dict, Optional


ALGOLIA_APP_ID = '74ELO4KNI1'
ALGOLIA_API_KEY = '3e3e825e1bdc1e1ceab0e3e5d1a81cca'  # Public search-only key from frontend
ALGOLIA_INDEX = 'prod_goldin_lot'
ALGOLIA_URL = f'https://{ALGOLIA_APP_ID.lower()}-dsn.algolia.net/1/indexes/*/queries'

GOLDIN_FEE_BUYER = 0.20  # 20% buyer's premium


def search_goldin(
    query: str,
    max_results: int = 20,
    status: str = 'all',  # 'all', 'active', 'sold'
) -> List[Dict]:
    """Search Goldin auctions via Algolia API.

    Args:
        query: Search text (e.g. "aaron judge 2024 topps chrome")
        max_results: Max results to return
        status: 'all', 'active' (live auctions), 'sold' (completed)

    Returns list of auction lot dicts.
    """
    filters = ''
    if status == 'active':
        filters = 'lotStatus:Active'
    elif status == 'sold':
        filters = 'lotStatus:Sold'

    payload = {
        'requests': [{
            'indexName': ALGOLIA_INDEX,
            'params': f'query={query}&hitsPerPage={max_results}&filters={filters}',
        }]
    }

    try:
        resp = requests.post(
            ALGOLIA_URL,
            params={
                'x-algolia-agent': 'Algolia for JavaScript',
                'x-algolia-application-id': ALGOLIA_APP_ID,
                'x-algolia-api-key': ALGOLIA_API_KEY,
            },
            headers={'Content-Type': 'application/json'},
            json=payload,
            timeout=15,
        )

        if resp.status_code != 200:
            print(f'Goldin Algolia HTTP {resp.status_code}: {resp.text[:200]}')
            return []

        data = resp.json()
        hits = data.get('results', [{}])[0].get('hits', [])
        return [_parse_goldin_hit(h) for h in hits]

    except requests.exceptions.ConnectionError as e:
        # DNS resolution fails in some environments (WSL)
        print(f'Goldin DNS error (expected in WSL): {str(e)[:80]}')
        return []
    except Exception as e:
        print(f'Goldin search error: {e}')
        return []


def _parse_goldin_hit(hit: dict) -> Dict:
    """Parse an Algolia hit into a normalized listing dict."""
    lot_id = hit.get('objectID', hit.get('lotId', ''))
    title = hit.get('title', hit.get('lotTitle', ''))
    current_bid = hit.get('currentBid', hit.get('hammerPrice', 0))
    estimate_low = hit.get('estimateLow', 0)
    estimate_high = hit.get('estimateHigh', 0)
    status = hit.get('lotStatus', hit.get('status', ''))
    end_time = hit.get('endTime', hit.get('auctionEndDate', ''))
    image_url = hit.get('imageUrl', hit.get('thumbnailUrl', ''))
    category = hit.get('category', '')
    sport = hit.get('sport', '')

    # Extract card identity from title
    identity = _extract_identity_from_title(title)

    # Total cost includes buyer's premium
    total_with_premium = float(current_bid) * (1 + GOLDIN_FEE_BUYER) if current_bid else 0

    return {
        'title': title,
        'price': float(current_bid) if current_bid else 0,
        'total_with_premium': round(total_with_premium, 2),
        'estimate_low': float(estimate_low) if estimate_low else None,
        'estimate_high': float(estimate_high) if estimate_high else None,
        'url': f'https://goldin.co/item/{lot_id}' if lot_id else '',
        'item_id': str(lot_id),
        'image_url': image_url,
        'source': 'goldin',
        'status': status,
        'end_time': end_time,
        'category': category,
        'sport': sport,
        'listing_type': 'goldin',
        **identity,
    }


def _extract_identity_from_title(title: str) -> Dict:
    """Extract card identity from Goldin lot title."""
    result = {'player_name': None, 'card_year': None, 'card_set': None,
              'card_number': None, 'parallel': None, 'graded': False,
              'grade_company': None, 'grade_value': None}
    if not title:
        return result

    # Year
    year_match = re.search(r'\b(19[5-9]\d|20\d{2})\b', title)
    if year_match:
        result['card_year'] = int(year_match.group(1))

    # Card number
    num_match = re.search(r'#([A-Za-z0-9-]+)', title)
    if num_match:
        result['card_number'] = num_match.group(1)

    # Grading
    grade_match = re.search(r'(PSA|BGS|SGC|CGC)\s*(\d+(?:\.\d)?)', title, re.I)
    if grade_match:
        result['graded'] = True
        result['grade_company'] = grade_match.group(1).upper()
        result['grade_value'] = float(grade_match.group(2))

    return result


def find_goldin_arbitrage(
    query: str,
    scp_db,
    min_profit: float = 20.0,
) -> List[Dict]:
    """Find active Goldin auctions priced below SCP market value.

    Goldin has a 20% buyer's premium, so the math is:
    profit = SCP * 0.87 (eBay net) - (goldin_bid * 1.20) (total cost with premium)
    """
    from sqlalchemy import text

    listings = search_goldin(query, max_results=30, status='active')
    if not listings:
        return []

    opportunities = []
    for listing in listings:
        if not listing.get('price') or listing['price'] <= 0:
            continue
        if not listing.get('card_year') or not listing.get('card_number'):
            continue

        year = listing['card_year']
        number = listing['card_number']

        scp_row = scp_db.execute(text("""
            SELECT (v->>'ungraded')::numeric as price, v->>'volume' as volume
            FROM scp_cache sc, jsonb_array_elements(sc.variants) v
            WHERE sc.card_year = :y AND sc.card_number ILIKE :n
            AND (v->>'ungraded')::numeric > 0
            ORDER BY (v->>'ungraded')::numeric DESC LIMIT 1
        """), {'y': year, 'n': str(number)}).first()

        if not scp_row:
            continue

        scp_price = float(scp_row.price)
        total_cost = listing['total_with_premium']
        ebay_net = scp_price * 0.87
        profit = ebay_net - total_cost

        if profit >= min_profit:
            opportunities.append({
                **listing,
                'scp_price': scp_price,
                'scp_volume': scp_row.volume,
                'ebay_net': round(ebay_net, 2),
                'profit': round(profit, 2),
                'roi': round((profit / total_cost) * 100, 1) if total_cost > 0 else 0,
                'arbitrage_path': 'goldin -> ebay',
            })

    return sorted(opportunities, key=lambda x: x['profit'], reverse=True)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Goldin auction scraper')
    parser.add_argument('query', help='Search query')
    parser.add_argument('--max-results', type=int, default=20)
    parser.add_argument('--status', choices=['all', 'active', 'sold'], default='all')
    parser.add_argument('--compare-scp', action='store_true')
    args = parser.parse_args()

    print(f'Searching Goldin for: {args.query} (status={args.status})')
    results = search_goldin(args.query, max_results=args.max_results, status=args.status)

    print(f'\nFound {len(results)} results:')
    for r in results:
        bid = f"${r['price']:.0f}" if r.get('price') else '?'
        premium = f" (${r['total_with_premium']:.0f} w/ premium)" if r.get('total_with_premium') else ''
        status = f" [{r['status']}]" if r.get('status') else ''
        print(f"  {bid}{premium}{status} | {r['title'][:80]}")

    if args.compare_scp and results:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend', '.env'))
        from contextlib import closing
        from backend.utils.database import SessionLocal

        with closing(SessionLocal()) as db:
            opps = find_goldin_arbitrage(args.query, db)

        if opps:
            print(f'\n{len(opps)} arbitrage opportunities (Goldin -> eBay):')
            for o in opps:
                print(f"  ${o['price']:.0f} bid + 20% = ${o['total_with_premium']:.0f} -> ${o['scp_price']:.0f} SCP = ${o['profit']:.0f} profit")
                print(f"    {o['title'][:80]}")
        else:
            print('\nNo arbitrage opportunities found.')
