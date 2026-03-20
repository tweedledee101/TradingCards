"""Test: Can we find the actual eBay listing for a specific opportunity?"""
import json
import requests
from backend.scrapers.ebay_scraper import EbayScraper

s = EbayScraper()
s.headers['Authorization'] = f'Bearer {s.token_manager.get_token()}'

# Search exactly what the opportunity says: 2024 Leaf Aaron Judge Base Raw
queries = [
    '2024 Leaf Aaron Judge',
    '2024 Leaf Aaron Judge base',
]

for q in queries:
    print(f"\n{'='*70}")
    print(f"SEARCH: {q}")
    print(f"{'='*70}")
    
    resp = requests.get(
        s.base_url + '/item_summary/search',
        headers=s.headers,
        params={
            'q': q,
            'filter': 'buyingOptions:{FIXED_PRICE}',  # BIN only, skip auctions
            'sort': 'price',  # cheapest first
            'limit': 20
        },
        timeout=30
    )
    
    if resp.status_code != 200:
        print(f"Error: {resp.status_code}")
        continue
    
    data = resp.json()
    print(f"Total results: {data.get('total', '?')}")
    print()
    
    for item in data.get('itemSummaries', []):
        title = item.get('title', '')
        price = float(item.get('price', {}).get('value', 0))
        buying = item.get('buyingOptions', [])
        condition = item.get('condition', '')
        url = item.get('itemWebUrl', '')
        
        # Get image
        img = ''
        thumbs = item.get('thumbnailImages', [])
        if thumbs:
            img = thumbs[0].get('imageUrl', '')
        
        # Extract card info
        info = s._extract_card_info(title, condition)
        
        print(f"  ${price:.2f} | {title[:80]}")
        print(f"    Set: {info.get('card_set')} | Parallel: {info.get('parallel')} | Grade: {info.get('grade_company') or 'Raw'} {info.get('grade_value') or ''}")
        print(f"    Card#: {info.get('card_number')} | Buying: {buying}")
        print(f"    URL: {url[:100]}")
        print(f"    Image: {img[:100]}")
        print()
