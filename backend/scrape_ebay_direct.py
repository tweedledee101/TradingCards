"""
Direct eBay Scraping with Selenium - NO API

Scrapes eBay sold listings directly from website to bypass rate limits.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time
import re
import requests
import yaml
from datetime import datetime, timedelta

WEBHOOK_URL = "http://localhost:8000/api/webhooks/novaact/ebay"

# Setup Chrome
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

# Read targets
with open('config/targets.yaml', 'r') as f:
    targets = yaml.safe_load(f)

players = targets['players'][:3]  # First 3 players

print("Scraping eBay directly with Selenium...")
print("=" * 70)

for player in players:
    player_name = player['name']
    query = f"{player_name} rookie PSA"
    
    print(f"\nScraping: {player_name}")
    print(f"  Query: {query}")
    
    # Build eBay sold listings URL
    url = f"https://www.ebay.com/sch/i.html?_nkw={query.replace(' ', '+')}&LH_Sold=1&LH_Complete=1"
    
    try:
        driver.get(url)
        time.sleep(3)
        
        # Find all listing items
        items = driver.find_elements(By.CSS_SELECTOR, ".s-item")
        print(f"  Found {len(items)} items")
        
        count = 0
        for item in items[:20]:  # First 20 items
            try:
                # Extract title
                title_elem = item.find_element(By.CSS_SELECTOR, ".s-item__title")
                title = title_elem.text
                
                if "Shop on eBay" in title:
                    continue
                
                # Extract price
                price_elem = item.find_element(By.CSS_SELECTOR, ".s-item__price")
                price_text = price_elem.text.replace('$', '').replace(',', '')
                sale_price = float(re.search(r'[\d.]+', price_text).group())
                
                # Extract date
                date_elem = item.find_element(By.CSS_SELECTOR, ".s-item__endedDate")
                date_text = date_elem.text.replace('Sold  ', '')
                
                # Parse date
                if 'h' in date_text or 'm' in date_text:
                    sale_date = datetime.now().strftime('%Y-%m-%d')
                elif 'd' in date_text:
                    days = int(re.search(r'\d+', date_text).group())
                    sale_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                else:
                    sale_date = datetime.now().strftime('%Y-%m-%d')
                
                # Extract item ID from link
                link_elem = item.find_element(By.CSS_SELECTOR, ".s-item__link")
                link = link_elem.get_attribute('href')
                item_id_match = re.search(r'/itm/(\d+)', link)
                ebay_item_id = item_id_match.group(1) if item_id_match else str(hash(title))[:10]
                
                # Parse card details
                year_match = re.search(r'\b(20\d{2})\b', title)
                card_year = int(year_match.group()) if year_match else 2023
                
                sets = ['Prizm', 'Select', 'Optic', 'Bowman', 'Topps']
                card_set = 'Unknown'
                for s in sets:
                    if s.lower() in title.lower():
                        card_set = s
                        break
                
                is_rookie = bool(re.search(r'\brc\b|\brookie\b', title.lower()))
                graded = 'psa' in title.lower() or 'bgs' in title.lower()
                
                grade_company = None
                grade_value = None
                if graded:
                    if 'psa' in title.lower():
                        grade_company = 'PSA'
                        grade_match = re.search(r'psa\s*(\d+)', title.lower())
                        grade_value = float(grade_match.group(1)) if grade_match else None
                
                # Build payload
                payload = {
                    'player_name': player_name,
                    'title': title,
                    'sale_price': sale_price,
                    'sale_date': sale_date,
                    'ebay_item_id': ebay_item_id,
                    'card_year': card_year,
                    'card_set': card_set,
                    'is_rookie': is_rookie,
                    'graded': graded,
                    'grade_company': grade_company,
                    'grade_value': grade_value,
                    'condition': 'Graded' if graded else 'Ungraded'
                }
                
                # Send to webhook
                resp = requests.post(WEBHOOK_URL, json=payload, timeout=5)
                if resp.status_code == 200:
                    count += 1
                    print(f"    ✓ ${sale_price} - {title[:50]}...")
                
            except Exception as e:
                continue
        
        print(f"  Sent {count} sales to database")
        time.sleep(2)  # Be nice to eBay
        
    except Exception as e:
        print(f"  Error: {e}")

driver.quit()

print("\n" + "=" * 70)
print("Scraping complete!")
print(f"\nNext steps:")
print(f"  1. Check database: python3 backend/debug_pwcc_sales.py")
print(f"  2. Start API: python3 -m backend.api.run")
print(f"  3. Start UI: cd frontend && npm run dev")
