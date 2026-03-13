"""
Use Amazon Nova Act to Scrape Active eBay Listings

Scrapes current "Buy It Now" listings to populate ActiveListing table.
This enables OpportunityAnalyzer to compare buy prices vs market rates.
"""

import os
import json
import requests
from openai import OpenAI
from datetime import date

NOVA_API_KEY = os.getenv('NOVA_API_KEY')
if not NOVA_API_KEY:
    print("ERROR: Set NOVA_API_KEY environment variable")
    exit(1)

WEBHOOK_URL = "http://localhost:8000/api/webhooks/novaact/active-listing"

client = OpenAI(
    api_key=NOVA_API_KEY,
    base_url="https://api.nova.amazon.com/v1"
)

# Read targets
import yaml
with open('config/targets.yaml', 'r') as f:
    targets = yaml.safe_load(f)

players = targets['players']

print("Scraping Active eBay Listings with Nova Act...")
print("=" * 70)

for player in players:
    player_name = player['name']
    print(f"\nScraping: {player_name}")
    
    response = client.chat.completions.create(
        model="nova-2-lite-v1",
        messages=[{
            "role": "user",
            "content": f"""Go to eBay and search for: "{player_name} rookie PSA"

Filter to "Buy It Now" listings only (not auctions).

Extract data from 20 active listings:
- Title (full listing title)
- Price (number only, no currency symbol)
- Item ID (from the listing URL)
- Listing type (should be "buy_it_now")

Return ONLY a JSON array:
[
  {{"title": "...", "price": 450.00, "ebay_item_id": "123456789", "listing_type": "buy_it_now"}}
]

No explanatory text, only JSON array."""
        }]
    )
    
    content = response.choices[0].message.content
    print(f"  Response length: {len(content)} chars")
    
    try:
        start = content.find('[')
        end = content.rfind(']') + 1
        json_str = content[start:end]
        
        listings = json.loads(json_str)
        print(f"  Found {len(listings)} active listings")
        
        for listing in listings:
            listing['player_name'] = player_name
            
            # Parse card details from title
            title = listing['title']
            import re
            
            year_match = re.search(r'\b(20\d{2})\b', title)
            listing['card_year'] = int(year_match.group()) if year_match else 2023
            
            sets = ['Prizm', 'Select', 'Optic', 'Bowman', 'Topps']
            listing['card_set'] = 'Unknown'
            for s in sets:
                if s.lower() in title.lower():
                    listing['card_set'] = s
                    break
            
            listing['snapshot_date'] = date.today().isoformat()
            
            try:
                resp = requests.post(WEBHOOK_URL, json=listing, timeout=5)
                if resp.status_code == 200:
                    print(f"    ✓ Sent: ${listing['price']}")
                else:
                    print(f"    ✗ Failed: {resp.status_code}")
            except Exception as e:
                print(f"    ✗ Error: {e}")
    
    except Exception as e:
        print(f"  Error parsing response: {e}")
        print(f"  Raw: {content[:200]}...")

print("\n" + "=" * 70)
print("Active listings scraping complete!")
print("\nNext: Run opportunity analyzer")
print("  python -m backend.run_opportunity_analyzer")
