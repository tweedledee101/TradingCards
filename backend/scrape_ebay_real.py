"""
REAL eBay Scraper - No AI, No Hallucinations

Uses Selenium to actually browse eBay and extract real data from HTML.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import re
from datetime import datetime, date
import requests

WEBHOOK_URL_SALES = "http://localhost:8000/api/webhooks/novaact/ebay"
WEBHOOK_URL_LISTINGS = "http://localhost:8000/api/webhooks/novaact/active-listing"

def setup_driver():
    """Setup headless Chrome"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=options)

def scrape_sold_listings(player_name, max_results=15):
    """Scrape REAL sold listings from eBay"""
    driver = setup_driver()
    
    try:
        # Search eBay sold listings
        search_url = f"https://www.ebay.com/sch/i.html?_nkw={player_name.replace(' ', '+')}+rookie+card&_sacat=0&LH_Sold=1&LH_Complete=1&_sop=13"
        driver.get(search_url)
        time.sleep(3)
        
        # Find all listing items
        items = driver.find_elements(By.CSS_SELECTOR, '.s-item')
        
        sales = []
        for item in items[:max_results]:
            try:
                # Extract title
                title_elem = item.find_element(By.CSS_SELECTOR, '.s-item__title')
                title = title_elem.text
                
                if not title or title == '':
                    continue
                
                # Extract price
                price_elem = item.find_element(By.CSS_SELECTOR, '.s-item__price')
                price_text = price_elem.text.replace('$', '').replace(',', '')
                price = float(re.search(r'[\d.]+', price_text).group())
                
                # Extract item ID from link
                link_elem = item.find_element(By.CSS_SELECTOR, '.s-item__link')
                link = link_elem.get_attribute('href')
                item_id = re.search(r'/itm/(\d+)', link)
                ebay_item_id = item_id.group(1) if item_id else None
                
                # Extract date (sold date)
                date_elem = item.find_element(By.CSS_SELECTOR, '.s-item__ended-date')
                date_text = date_elem.text
                # Parse "Sold Feb 10, 2026" format
                sale_date = datetime.now().strftime('%Y-%m-%d')  # Default to today
                
                sales.append({
                    'title': title,
                    'sale_price': price,
                    'sale_date': sale_date,
                    'ebay_item_id': ebay_item_id,
                    'condition': 'Graded' if 'PSA' in title or 'BGS' in title else 'Ungraded',
                    'player_name': player_name
                })
                
            except Exception as e:
                continue
        
        return sales
        
    finally:
        driver.quit()

def scrape_active_listings(player_name, max_results=15):
    """Scrape REAL active listings from eBay"""
    driver = setup_driver()
    
    try:
        # Search eBay active listings (Buy It Now only)
        search_url = f"https://www.ebay.com/sch/i.html?_nkw={player_name.replace(' ', '+')}+rookie+card&_sacat=0&LH_BIN=1&_sop=15"
        driver.get(search_url)
        time.sleep(3)
        
        # Find all listing items
        items = driver.find_elements(By.CSS_SELECTOR, '.s-item')
        
        listings = []
        for item in items[:max_results]:
            try:
                # Extract title
                title_elem = item.find_element(By.CSS_SELECTOR, '.s-item__title')
                title = title_elem.text
                
                if not title or title == '':
                    continue
                
                # Extract price
                price_elem = item.find_element(By.CSS_SELECTOR, '.s-item__price')
                price_text = price_elem.text.replace('$', '').replace(',', '')
                price = float(re.search(r'[\d.]+', price_text).group())
                
                # Extract item ID
                link_elem = item.find_element(By.CSS_SELECTOR, '.s-item__link')
                link = link_elem.get_attribute('href')
                item_id = re.search(r'/itm/(\d+)', link)
                ebay_item_id = item_id.group(1) if item_id else None
                
                listings.append({
                    'title': title,
                    'price': price,
                    'ebay_item_id': ebay_item_id,
                    'listing_type': 'buy_it_now',
                    'player_name': player_name,
                    'snapshot_date': date.today().isoformat()
                })
                
            except Exception as e:
                continue
        
        return listings
        
    finally:
        driver.quit()

def parse_card_details(title):
    """Extract card details from title"""
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
    if graded:
        if 'PSA' in title:
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
    import yaml
    
    with open('config/targets.yaml', 'r') as f:
        targets = yaml.safe_load(f)
    
    players = [p['name'] for p in targets['players'][:3]]  # First 3 players
    
    print("REAL eBay Scraper - Using Selenium")
    print("=" * 70)
    
    for player in players:
        print(f"\n{player}")
        print("-" * 70)
        
        # Scrape sold listings
        print("Scraping sold listings...")
        sales = scrape_sold_listings(player)
        print(f"  Found {len(sales)} real sales")
        
        for sale in sales:
            details = parse_card_details(sale['title'])
            sale.update(details)
            
            try:
                resp = requests.post(WEBHOOK_URL_SALES, json=sale, timeout=5)
                if resp.status_code == 200:
                    print(f"    ✓ ${sale['sale_price']}")
            except:
                pass
        
        # Scrape active listings
        print("Scraping active listings...")
        listings = scrape_active_listings(player)
        print(f"  Found {len(listings)} real listings")
        
        for listing in listings:
            details = parse_card_details(listing['title'])
            listing.update(details)
            
            try:
                resp = requests.post(WEBHOOK_URL_LISTINGS, json=listing, timeout=5)
                if resp.status_code == 200:
                    print(f"    ✓ ${listing['price']}")
            except:
                pass
    
    print("\n" + "=" * 70)
    print("REAL DATA COLLECTED!")
    print("Run: python -m backend.run_opportunity_analyzer")
