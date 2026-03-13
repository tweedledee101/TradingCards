"""
PWCC Nova Act Scraper - Discover Trending Players

Uses Nova Act to scrape PWCC auctions and identify hot players.
"""

import os
import json
import requests
from openai import OpenAI

NOVA_API_KEY = os.getenv('NOVA_API_KEY')
if not NOVA_API_KEY:
    print("ERROR: Set NOVA_API_KEY environment variable")
    exit(1)

WEBHOOK_URL = "http://localhost:8000/api/webhooks/novaact/pwcc"

client = OpenAI(
    api_key=NOVA_API_KEY,
    base_url="https://api.nova.amazon.com/v1"
)

print("Using Nova Act to scrape PWCC auctions...")
print("=" * 70)
print("Sending request to Nova Act AI...")
print("(This may take 30-60 seconds while Nova Act browses websites)")
print()

# Ask Nova Act to scrape PWCC
response = client.chat.completions.create(
    model="nova-2-lite-v1",
    messages=[{
        "role": "user",
        "content": """Go to https://www.pwccmarketplace.com and find recently sold sports card auctions.

Look for the "Recently Sold" or "Auction Results" section.

Extract data from 50-100 recent sales:
- Player name (parse from auction title)
- Sport (Basketball, Baseball, Football, Hockey)
- Card year (2020-2024)
- Card set (Prizm, Select, Bowman, Topps, Optic, etc.)
- Final sale price in USD
- Sale date (YYYY-MM-DD)
- Is it a rookie card? (look for "RC" or "Rookie" in title)
- Is it graded? (look for "PSA", "BGS", "SGC" in title)
- Full auction title

Return ONLY a JSON array:
[
  {
    "player_name": "Victor Wembanyama",
    "sport": "Basketball",
    "card_year": 2023,
    "card_set": "Prizm",
    "sale_price": 4500.00,
    "sale_date": "2026-02-13",
    "is_rookie": true,
    "graded": true,
    "title": "2023 Panini Prizm Victor Wembanyama RC PSA 10"
  }
]

If you cannot access PWCC, try these alternative sites:
- eBay sold listings for "sports cards" with high prices (over $500)
- Goldin Auctions recent sales
- Heritage Auctions sports cards

Focus on cards that sold in the last 7 days for $200-$5000.

Do not include any explanatory text, only the JSON array."""
    }]
)

content = response.choices[0].message.content
print("✓ Received response from Nova Act")
print(f"Response length: {len(content)} chars")
print("Parsing JSON data...")
print()

try:
    # Extract JSON from response
    start = content.find('[')
    end = content.rfind(']') + 1
    json_str = content[start:end]
    
    sales = json.loads(json_str)
    print(f"Found {len(sales)} PWCC sales")
    
    # Send each sale to webhook
    count = 0
    for sale in sales:
        try:
            resp = requests.post(WEBHOOK_URL, json=sale, timeout=5)
            if resp.status_code == 200:
                count += 1
                print(f"  ✓ {sale['player_name']}: ${sale['sale_price']}")
            else:
                print(f"  ✗ Failed: {resp.status_code}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print("=" * 70)
    print(f"Sent {count}/{len(sales)} PWCC sales to database")
    print("\nNext: Run discovery aggregator")
    print("  python backend/run_discovery_integrated.py --now")

except Exception as e:
    print(f"Error parsing response: {e}")
    print(f"Raw response: {content[:500]}...")
