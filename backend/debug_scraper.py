"""
Debug scraper - Check what HTML we're actually getting
"""
import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Test COMC
print("Testing COMC...")
url = "https://www.comc.com/Cards/Baseball/Shohei_Ohtani"
response = requests.get(url, headers=headers, timeout=10)
print(f"Status: {response.status_code}")
print(f"URL: {response.url}")

soup = BeautifulSoup(response.text, 'html.parser')

# Save first 5000 chars
with open('/tmp/comc_debug.html', 'w') as f:
    f.write(response.text[:5000])

print("HTML saved to /tmp/comc_debug.html")
print("\nSearching for price indicators...")

# Look for dollar signs
prices = soup.find_all(text=lambda t: '$' in str(t))[:10]
for p in prices:
    print(f"  Found: {p.strip()[:80]}")

print("\nSearching for links...")
links = soup.find_all('a', href=True)[:10]
for link in links:
    print(f"  {link.get('href')}: {link.text.strip()[:50]}")
