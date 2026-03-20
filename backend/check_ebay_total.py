"""Check if eBay search returns total count"""
from backend.scrapers.ebay_scraper import EbayScraper
import requests

scraper = EbayScraper()
scraper.headers['Authorization'] = f'Bearer {scraper.token_manager.get_token()}'

params = {
    'q': 'Shohei Ohtani card',
    'filter': 'buyingOptions:{AUCTION|FIXED_PRICE}',
    'limit': 1
}

r = requests.get(
    scraper.base_url + '/item_summary/search',
    headers=scraper.headers,
    params=params,
    timeout=10
)

data = r.json()
print(f"total: {data.get('total')}")
print(f"top-level keys: {list(data.keys())}")
