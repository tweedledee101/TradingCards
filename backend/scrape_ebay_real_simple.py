"""
REAL eBay Scraper - HTTP + BeautifulSoup

Scrapes eBay HTML directly. No browser, no AI, just real data.
"""

import requests
from bs4 import BeautifulSoup
import re
from datetime import date
import time

WEBHOOK_URL_SALES = "http://localhost:8000/api/webhooks/novaact/ebay"
WEBHOOK_URL_LISTINGS = "http://localhost:8000/api/webhooks/novaact/active-listing"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def scrape_sold_listings(player_name, max_results=15):
    """Scrape REAL sold listings"""
    search_url = f"https://www.ebay.com/sch/i.html?_nkw={player_name.replace(' ', '+')}+rookie+card&_sacat=0&LH_Sold=1&LH_Complete=1&_sop=13"
    
    print(f"  URL: {search_url}")
    response = requests.get(search_url, headers=HEADERS)
    print(f"  Status: {response.status_code}")
    
    # Save HTML for debugging
    with open(f'/tmp/ebay_{player_name.replace(" ", "_")}.html', 'w') as f:
        f.write(response.text[:5000])  # First 5000 chars
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    items = soup.find_all('li', class_='s-item', limit=max_results + 5)
    print(f"  Found {len(items)} raw items")
    print(f"  HTML saved to /tmp/ebay_{player_name.replace(' ', '_')}.html")
    
    # Try alternate selectors
    if len(items) == 0:
        items = soup.find_all('div', class_='s-item__wrapper')
        print(f"  Trying alternate selector: {len(items)} items")
    
    sales = []
    for item in items:
        try:
            # Skip header/ad items
            title_elem = item.find('div', class_='s-item__title')
            if not title_elem or 'Shop on eBay' in title_elem.text:
                continue
            
            title = title_elem.text.strip()
            
            # Extract price
            price_elem = item.find('span', class_='s-item__price')
            if not price_elem:
                continue
            
            price_text = price_elem.text.replace('$', '').replace(',', '')
            price_match = re.search(r'([\d.]+)', price_text)
            if not price_match:
                continue
            
            price = float(price_match.group(1))
            
            # Extract item ID
            link_elem = item.find('a', class_='s-item__link')
            if not link_elem:
                continue
            
            link = link_elem.get('href', '')
            item_id_match = re.search(r'/itm/(\d+)', link)
            ebay_item_id = item_id_match.group(1) if item_id_match else None
            
            if not ebay_item_id:
                continue
            
            sales.append({
                'title': title,
                'sale_price': price,
                'sale_date': date.today().isoformat(),
                'ebay_item_id': ebay_item_id,
                'condition': 'Graded' if 'PSA' in title or 'BGS' in title else 'Ungraded',
                'player_name': player_name
            })
            
            if len(sales) >= max_results:
                break
                
        except Exception as e:
            print(f"  Error parsing item: {e}")
            continue
    
    return sales

def scrape_active_listings(player_name, max_results=15):
    """Scrape REAL active listings"""
    search_url = f"https://www.ebay.com/sch/i.html?_nkw={player_name.replace(' ', '+')}+rookie+card&_sacat=0&LH_BIN=1&_sop=15"
    
    response = requests.get(search_url, headers=HEADERS)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    items = soup.find_all('li', class_='s-item', limit=max_results + 5)
    
    listings = []
    for item in items:
        try:
            # Skip header/ad items
            title_elem = item.find('div', class_='s-item__title')
            if not title_elem or 'Shop on eBay' in title_elem.text:
                continue
            
            title = title_elem.text.strip()
            
            # Extract price
            price_elem = item.find('span', class_='s-item__price')
            if not price_elem:
                continue
            
            price_text = price_elem.text.replace('$', '').replace(',', '')
            price_match = re.search(r'([\d.]+)', price_text)
            if not price_match:
                continue
            
            price = float(price_match.group(1))
            
            # Extract item ID
            link_elem = item.find('a', class_='s-item__link')
            if not link_elem:
                continue
            
            link = link_elem.get('href', '')
            item_id_match = re.search(r'/itm/(\d+)', link)
            ebay_item_id = item_id_match.group(1) if item_id_match else None
            
            if not ebay_item_id:
                continue
            
            listings.append({
                'title': title,
                'price': price,
                'ebay_item_id': ebay_item_id,
                'listing_type': 'buy_it_now',
                'player_name': player_name,
                'snapshot_date': date.today().isoformat()
            })
            
            if len(listings) >= max_results:
                break
                
        except Exception as e:
            continue
    
    return listings

def parse_card_details(title):
    """Extract card details"""
    year_match = re.search(r'\b(20\d{2})\b', title)
    card_year = int(year_match.group()) if year_match else 2023
    
    sets = ['Prizm', 'Select', 'Optic', 'Bowman', 'Topps']
    card_set = 'Unknown'
    for s in sets:
        if s.lower() in title.lower():
            card_set = s
            break
    
    is_rookie = bool(re.search(r'\brc\b|\brookie\b', title.lower()))
    graded = 'PSA' in title or 'BGS' in title or 'SGC' in title
    
    grade_company = None
    grade_value = None
    if graded and 'PSA' in title:
        grade_company = 'PSA'
        grade_match = re.search(r'PSA\s*(\d+)', title)
        if grade_match:
            grade_value = float(grade_match.group(1))
    
    return {
        'card_year': card_year,
        'card_set': card_set,
        'is_rookie': is_rookie,
        'graded': graded,
        'grade_company': grade_company,
        'grade_value': grade_value
    }

if __name__ == '__main__':
    # Hardcoded popular players - no database needed
    players = [
        'Victor Wembanyama',
        'Caitlin Clark',
        'Shohei Ohtani',
        'Paul Skenes',
        'Anthony Edwards',
        'Gunnar Henderson',
        'Bobby Witt Jr',
        'CJ Stroud',
        'Caleb Williams',
        'Jayden Daniels'
    ]
    
    print("REAL eBay Scraper - HTTP + BeautifulSoup")
    print("=" * 70)
    
    for player in players:
        print(f"\n{player}")
        print("-" * 70)
        
        # Scrape sold
        print("Scraping sold listings...")
        sales = scrape_sold_listings(player)
        print(f"  Found {len(sales)} REAL sales")
        
        for sale in sales:
            details = parse_card_details(sale['title'])
            sale.update(details)
            
            try:
                resp = requests.post(WEBHOOK_URL_SALES, json=sale, timeout=5)
                if resp.status_code == 200:
                    print(f"    ✓ ${sale['sale_price']:.2f} - {sale['title'][:50]}")
            except:
                pass
        
        time.sleep(2)  # Be nice to eBay
        
        # Scrape active
        print("Scraping active listings...")
        listings = scrape_active_listings(player)
        print(f"  Found {len(listings)} REAL listings")
        
        for listing in listings:
            details = parse_card_details(listing['title'])
            listing.update(details)
            
            try:
                resp = requests.post(WEBHOOK_URL_LISTINGS, json=listing, timeout=5)
                if resp.status_code == 200:
                    print(f"    ✓ ${listing['price']:.2f} - {listing['title'][:50]}")
            except:
                pass
        
        time.sleep(2)
    
    print("\n" + "=" * 70)
    print("REAL DATA COLLECTED FROM EBAY!")
    print("Run: python -m backend.run_opportunity_analyzer")
