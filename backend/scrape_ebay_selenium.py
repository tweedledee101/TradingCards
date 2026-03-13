"""
Real eBay Scraper - Selenium (Browser Automation)

Uses Selenium to scrape eBay because results are JavaScript-rendered.
"""
import sys
sys.path.insert(0, '/app')

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
from datetime import date
import requests

WEBHOOK_URL_SALES = "http://localhost:8000/api/webhooks/novaact/ebay"
WEBHOOK_URL_LISTINGS = "http://localhost:8000/api/webhooks/novaact/active-listing"

def get_driver():
    """Setup headless Chrome"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    print("Initializing Chrome driver...")
    try:
        driver = webdriver.Chrome(options=options)
        print(f"✓ Chrome driver initialized successfully")
        return driver
    except Exception as e:
        print(f"✗ Chrome driver failed: {e}")
        print("\nTrying to check Chrome installation...")
        import subprocess
        try:
            result = subprocess.run(['google-chrome', '--version'], capture_output=True, text=True)
            print(f"Chrome version: {result.stdout}")
        except:
            print("Chrome not found in PATH")
        raise

def scrape_sold_listings(driver, player_name, max_results=15):
    """Scrape sold listings with Selenium"""
    url = f"https://www.ebay.com/sch/i.html?_nkw={player_name.replace(' ', '+')}+rookie+card&_sacat=0&LH_Sold=1&LH_Complete=1&_sop=13"
    
    print(f"  Loading URL: {url}")
    driver.get(url)
    print(f"  Page loaded, waiting for JavaScript...")
    time.sleep(3)
    
    print(f"  Page title: {driver.title}")
    print(f"  Current URL: {driver.current_url}")
    
    # Save page source for debugging
    with open(f'/tmp/selenium_{player_name.replace(" ", "_")}.html', 'w') as f:
        f.write(driver.page_source[:10000])
    print(f"  Page source saved to /tmp/selenium_{player_name.replace(' ', '_')}.html")
    
    # Find all listing items
    items = driver.find_elements(By.CSS_SELECTOR, 'li.s-item')
    print(f"  Found {len(items)} items with selector 'li.s-item'")
    
    if len(items) == 0:
        # Try alternate selectors
        print("  Trying alternate selector: .srp-results li")
        items = driver.find_elements(By.CSS_SELECTOR, '.srp-results li')
        print(f"  Found {len(items)} items")
    
    if len(items) == 0:
        print("  Trying alternate selector: [class*='s-item']")
        items = driver.find_elements(By.CSS_SELECTOR, "[class*='s-item']")
        print(f"  Found {len(items)} items")
    
    sales = []
    for i, item in enumerate(items[:max_results + 5]):
        try:
            # Get title
            title_elem = item.find_element(By.CSS_SELECTOR, '.s-item__title')
            title = title_elem.text.strip()
            
            if 'Shop on eBay' in title:
                continue
            
            # Get price
            price_elem = item.find_element(By.CSS_SELECTOR, '.s-item__price')
            price_text = price_elem.text.replace('$', '').replace(',', '')
            price_match = re.search(r'([\d.]+)', price_text)
            if not price_match:
                continue
            price = float(price_match.group(1))
            
            # Get item ID from link
            link_elem = item.find_element(By.CSS_SELECTOR, '.s-item__link')
            link = link_elem.get_attribute('href')
            item_id_match = re.search(r'/itm/(\d+)', link)
            if not item_id_match:
                continue
            ebay_item_id = item_id_match.group(1)
            
            sales.append({
                'title': title,
                'sale_price': price,
                'sale_date': date.today().isoformat(),
                'ebay_item_id': ebay_item_id,
                'condition': 'Graded' if 'PSA' in title or 'BGS' in title else 'Ungraded',
                'player_name': player_name
            })
            
            print(f"    [{i+1}] ${price:.2f} - {title[:60]}")
            
            if len(sales) >= max_results:
                break
        except Exception as e:
            print(f"  Error parsing item {i}: {e}")
            continue
    
    return sales

def scrape_active_listings(driver, player_name, max_results=15):
    """Scrape active listings with Selenium"""
    url = f"https://www.ebay.com/sch/i.html?_nkw={player_name.replace(' ', '+')}+rookie+card&_sacat=0&LH_BIN=1&_sop=15"
    
    driver.get(url)
    time.sleep(3)
    
    items = driver.find_elements(By.CSS_SELECTOR, 'li.s-item')
    
    listings = []
    for item in items[:max_results + 5]:
        try:
            title_elem = item.find_element(By.CSS_SELECTOR, '.s-item__title')
            title = title_elem.text.strip()
            
            if 'Shop on eBay' in title:
                continue
            
            price_elem = item.find_element(By.CSS_SELECTOR, '.s-item__price')
            price_text = price_elem.text.replace('$', '').replace(',', '')
            price_match = re.search(r'([\d.]+)', price_text)
            if not price_match:
                continue
            price = float(price_match.group(1))
            
            link_elem = item.find_element(By.CSS_SELECTOR, '.s-item__link')
            link = link_elem.get_attribute('href')
            item_id_match = re.search(r'/itm/(\d+)', link)
            if not item_id_match:
                continue
            ebay_item_id = item_id_match.group(1)
            
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
        except:
            continue
    
    return listings

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
    from backend.services.volume_discovery import VolumeDiscovery
    
    # Get top players from Phase 1
    discovery = VolumeDiscovery()
    top_players = discovery.discover_by_volume(days=90, limit=100)
    players = [p['player_name'] for p in top_players[:5]]  # Top 5 for testing
    
    print("Real eBay Scraper - Selenium")
    print("=" * 70)
    
    driver = get_driver()
    
    try:
        for player in players:
            print(f"\n{player}")
            print("-" * 70)
            
            # Scrape sold
            print("Scraping sold listings...")
            sales = scrape_sold_listings(driver, player)
            print(f"  Found {len(sales)} sales")
            
            for sale in sales:
                details = parse_card_details(sale['title'])
                sale.update(details)
                
                try:
                    resp = requests.post(WEBHOOK_URL_SALES, json=sale, timeout=5)
                    if resp.status_code == 200:
                        print(f"    ✓ ${sale['sale_price']:.2f} - {sale['title'][:50]}")
                except:
                    pass
            
            # Scrape active
            print("Scraping active listings...")
            listings = scrape_active_listings(driver, player)
            print(f"  Found {len(listings)} listings")
            
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
    
    finally:
        driver.quit()
    
    print("\n" + "=" * 70)
    print("REAL DATA COLLECTED!")
