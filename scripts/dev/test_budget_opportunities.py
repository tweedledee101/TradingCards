"""
End-to-End Test with Budget-Friendly Players

Scrapes real eBay data for players with cards in $10-$100 range
"""

import os
import json
import requests
from openai import OpenAI
from datetime import date

NOVA_API_KEY = os.getenv('NOVA_API_KEY')
WEBHOOK_URL_SALES = "http://localhost:8000/api/webhooks/novaact/ebay"
WEBHOOK_URL_LISTINGS = "http://localhost:8000/api/webhooks/novaact/active-listing"

client = OpenAI(
    api_key=NOVA_API_KEY,
    base_url="https://api.nova.amazon.com/v1"
)

# Budget-friendly players with cards in $10-$100 range
BUDGET_PLAYERS = [
    "Bo Bichette",
    "Randy Arozarena",
    "Julio Rodriguez",
    "Bobby Witt Jr",
    "Gunnar Henderson"
]

print("=" * 70)
print("END-TO-END TEST: Budget-Friendly Players ($10-$100)")
print("=" * 70)

for player_name in BUDGET_PLAYERS:
    print(f"\n{'='*70}")
    print(f"Player: {player_name}")
    print(f"{'='*70}")
    
    # Step 1: Scrape SOLD listings
    print(f"\n[1/2] Scraping sold listings for {player_name}...")
    response = client.chat.completions.create(
        model="nova-2-lite-v1",
        messages=[{
            "role": "user",
            "content": f"""Go to eBay and search for SOLD listings: "{player_name} rookie card"

Find cards that sold for $10-$100 (budget range).

Extract the last 15 sold listings:
- Title
- Sale price (number only)
- Sale date (YYYY-MM-DD)
- Item ID
- Condition (Graded or Ungraded)

Return ONLY JSON array:
[
  {{"title": "...", "sale_price": 45.00, "sale_date": "2026-02-10", "ebay_item_id": "123", "condition": "Graded"}}
]"""
        }]
    )
    
    content = response.choices[0].message.content
    
    try:
        start = content.find('[')
        end = content.rfind(']') + 1
        sales = json.loads(content[start:end])
        
        print(f"  Found {len(sales)} sold listings")
        
        success = 0
        for sale in sales:
            sale['player_name'] = player_name
            
            import re
            title = sale['title']
            year_match = re.search(r'\b(20\d{2})\b', title)
            sale['card_year'] = int(year_match.group()) if year_match else 2023
            
            sets = ['Prizm', 'Select', 'Optic', 'Bowman', 'Topps']
            sale['card_set'] = 'Unknown'
            for s in sets:
                if s.lower() in title.lower():
                    sale['card_set'] = s
                    break
            
            sale['is_rookie'] = bool(re.search(r'\brc\b|\brookie\b', title.lower()))
            sale['graded'] = sale['condition'] == 'Graded'
            
            try:
                resp = requests.post(WEBHOOK_URL_SALES, json=sale, timeout=5)
                if resp.status_code == 200:
                    success += 1
            except:
                pass
        
        print(f"  ✓ Saved {success}/{len(sales)} sales")
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
        continue
    
    # Step 2: Scrape ACTIVE listings
    print(f"\n[2/2] Scraping active listings for {player_name}...")
    response = client.chat.completions.create(
        model="nova-2-lite-v1",
        messages=[{
            "role": "user",
            "content": f"""Go to eBay and search for: "{player_name} rookie card"

Filter to "Buy It Now" listings in $10-$100 range.

Extract 15 active listings:
- Title
- Price (number only)
- Item ID
- Listing type (buy_it_now)

Return ONLY JSON array:
[
  {{"title": "...", "price": 45.00, "ebay_item_id": "123", "listing_type": "buy_it_now"}}
]"""
        }]
    )
    
    content = response.choices[0].message.content
    
    try:
        start = content.find('[')
        end = content.rfind(']') + 1
        listings = json.loads(content[start:end])
        
        print(f"  Found {len(listings)} active listings")
        
        success = 0
        for listing in listings:
            listing['player_name'] = player_name
            
            title = listing['title']
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
                resp = requests.post(WEBHOOK_URL_LISTINGS, json=listing, timeout=5)
                if resp.status_code == 200:
                    success += 1
            except:
                pass
        
        print(f"  ✓ Saved {success}/{len(listings)} listings")
    
    except Exception as e:
        print(f"  ✗ Error: {e}")

print("\n" + "=" * 70)
print("SCRAPING COMPLETE!")
print("=" * 70)
print("\nNext: Run opportunity analyzer")
print("  python -m backend.run_opportunity_analyzer")
