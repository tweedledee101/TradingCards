"""Test loading an SCP product page directly to see price table structure"""
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from bs4 import BeautifulSoup
import time

options = Options()
options.add_argument("--headless")
options.set_preference("general.useragent.override",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0")
options.binary_location = "/usr/bin/firefox"
service = Service(executable_path="/usr/local/bin/geckodriver")

driver = webdriver.Firefox(options=options, service=service)
driver.set_page_load_timeout(30)

url = "https://www.sportscardspro.com/game/baseball-cards-1999-bowman-chrome-impact/ken-griffey-jr-refractor-i20"
print(f"Loading: {url}")

try:
    driver.get(url)
except:
    pass  # timeout ok

time.sleep(3)
soup = BeautifulSoup(driver.page_source, "html.parser")

# Look for price elements
print("\n=== Product Title ===")
title = soup.find("h1")
if title:
    print(title.get_text(strip=True))

print("\n=== Price Table ===")
# Look for the price display area
price_table = soup.find("table", id="attribute")
if price_table:
    rows = price_table.find_all("tr")
    for row in rows:
        cells = row.find_all(["th", "td"])
        print(" | ".join(c.get_text(strip=True)[:30] for c in cells))
else:
    # Try other price elements
    for cls in ["used_price", "cib_price", "new_price", "price"]:
        els = soup.find_all(class_=cls)
        for el in els:
            print(f"  .{cls}: {el.get_text(strip=True)}")

# Look for any price-like spans/divs
print("\n=== All price-related elements ===")
for el in soup.find_all(string=lambda t: t and "$" in t):
    parent = el.parent
    if parent:
        cls = parent.get("class", [])
        print(f"  {parent.name}.{cls}: {el.strip()[:60]}")

driver.quit()
