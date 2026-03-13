"""Test PWCC site structure"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time

chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

urls_to_try = [
    "https://www.pwccmarketplace.com",
    "https://www.pwccmarketplace.com/sold-lots",
    "https://www.pwccmarketplace.com/auctions",
    "https://www.pwccmarketplace.com/lots",
    "https://pwccmarketplace.com",
]

for url in urls_to_try:
    try:
        print(f"\nTrying: {url}")
        driver.get(url)
        time.sleep(3)
        
        print(f"  Title: {driver.title}")
        print(f"  Status: {'404' if '404' in driver.page_source else 'OK'}")
        
        if '404' not in driver.page_source and 'not found' not in driver.page_source.lower():
            print(f"  SUCCESS - This URL works!")
            print(f"  Page length: {len(driver.page_source)}")
            
            # Save page source
            with open(f'/tmp/pwcc_test.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print(f"  Saved to /tmp/pwcc_test.html")
            break
    
    except Exception as e:
        print(f"  Error: {e}")

input("\nPress Enter to close...")
driver.quit()
