"""Test to find exact price selectors on SCP product page"""
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from bs4 import BeautifulSoup
import time, re

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
    pass

time.sleep(3)
soup = BeautifulSoup(driver.page_source, "html.parser")

# Find the price boxes at top of page (Ungraded, Grade 9, PSA 10)
print("\n=== Price boxes (span.price.js-price at top) ===")
price_spans = soup.find_all("span", class_="price")
for i, span in enumerate(price_spans[:10]):
    parent = span.parent
    grandparent = parent.parent if parent else None
    gp_id = grandparent.get("id", "") if grandparent else ""
    gp_class = grandparent.get("class", []) if grandparent else []
    p_id = parent.get("id", "") if parent else ""
    p_class = parent.get("class", []) if parent else []
    print(f"  [{i}] {span.get_text(strip=True):>12}  parent={parent.name}.{p_class}#{p_id}  gp={grandparent.name if grandparent else '?'}.{gp_class}#{gp_id}")

# Find the attribute table for ePID
print("\n=== Attribute table ===")
attr_table = soup.find("table", id="attribute")
if attr_table:
    for row in attr_table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True)
            value = cells[1].get_text(strip=True)
            if label:
                print(f"  {label} {value}")

# Find price section IDs
print("\n=== Elements with 'used' or 'loose' or 'ungraded' in id/class ===")
for el in soup.find_all(True):
    el_id = el.get("id", "")
    el_class = " ".join(el.get("class", []))
    combined = f"{el_id} {el_class}".lower()
    if any(w in combined for w in ["used", "loose", "ungraded", "cib", "graded", "new_price", "complete", "psa"]):
        text = el.get_text(strip=True)[:60]
        if text:
            print(f"  {el.name}#{el_id}.{el_class}: {text}")

driver.quit()
