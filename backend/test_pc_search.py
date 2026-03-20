"""Test PriceCharting search to find sports card data"""
import requests
from bs4 import BeautifulSoup

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

# Try different URL patterns
urls = [
    'https://www.pricecharting.com/search-products?q=paul+skenes+%2387&type=prices',
    'https://www.pricecharting.com/search-products?q=paul+skenes+87+panini&type=prices',
    'https://www.pricecharting.com/search-products?q=paul+skenes+87+topps&type=prices',
]

for url in urls:
    print(f"\nURL: {url}")
    resp = session.get(url, timeout=10)
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    rows = soup.find_all('tr')
    found = 0
    for row in rows:
        cells = row.find_all(['td', 'th'])
        texts = [c.get_text(strip=True) for c in cells]
        full = ' '.join(texts)
        if 'skenes' in full.lower() or 'Title' in full:
            print(f"  {[t[:45] for t in texts]}")
            found += 1
            if found > 5:
                break
    
    if found == 0:
        # Check what categories exist
        links = soup.find_all('a')
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if 'baseball' in href.lower() or 'baseball' in text.lower():
                print(f"  Found link: {text} -> {href}")
