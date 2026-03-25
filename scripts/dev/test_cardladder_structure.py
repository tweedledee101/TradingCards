"""
Test Card Ladder Site Structure

Inspects the Card Ladder movers page to determine correct CSS selectors.
Run with headless=False to see the browser.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time

# Initialize Chrome
chrome_options = Options()
# chrome_options.add_argument("--headless")  # Comment out to see browser
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    print("Loading Card Ladder movers page...")
    driver.get("https://www.cardladder.com/movers")
    
    # Wait longer for JavaScript to load
    print("Waiting for content to load...")
    time.sleep(10)
    
    # Scroll to trigger lazy loading
    print("Scrolling page...")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(2)
    
    print("\nPage title:", driver.title)
    print("Page source length:", len(driver.page_source))
    
    # Save full page source to file for inspection
    with open('/tmp/cardladder_page.html', 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    print("\nFull page source saved to /tmp/cardladder_page.html")
    
    # Try to find common card container elements
    print("\nSearching for card elements...")
    
    possible_selectors = [
        "card-item", "card", "mover", "trending-card",
        "list-item", "table-row", "grid-item", "card-row"
    ]
    
    for selector in possible_selectors:
        elements = driver.find_elements(By.CLASS_NAME, selector)
        if elements:
            print(f"  Found {len(elements)} elements with class '{selector}'")
    
    # Try finding by tag
    print("\nSearching by common tags...")
    for tag in ["article", "div", "li", "tr", "a"]:
        elements = driver.find_elements(By.TAG_NAME, tag)
        print(f"  Found {len(elements)} <{tag}> elements")
    
    # Look for data attributes
    print("\nSearching for elements with data attributes...")
    elements = driver.find_elements(By.XPATH, "//*[@data-card-id or @data-player or @data-item]")
    print(f"  Found {len(elements)} elements with data attributes")
    
    # Print last 3000 characters (where content likely is)
    print("\nLast 3000 characters of page source:")
    print("=" * 60)
    print(driver.page_source[-3000:])
    print("=" * 60)
    
    input("\nPress Enter to close browser...")

finally:
    driver.quit()
