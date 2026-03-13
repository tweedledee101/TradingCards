"""
Use Amazon Nova Act to Scrape eBay

Nova Act is an AI agent that can browse websites and extract data.
This script uses it to scrape eBay sold listings and send to webhook.
"""

import os
import json
import requests
from openai import OpenAI

NOVA_API_KEY = os.getenv('NOVA_API_KEY')
if not NOVA_API_KEY:
    print("ERROR: Set NOVA_API_KEY environment variable")
    print("export NOVA_API_KEY='your-key-here'")
    exit(1)

WEBHOOK_URL = "http://localhost:8000/api/webhooks/novaact/ebay"

client = OpenAI(
    api_key=NOVA_API_KEY,
    base_url="https://api.nova.amazon.com/v1"
)

# Read targets
import yaml
with open('config/targets.yaml', 'r') as f:
    targets = yaml.safe_load(f)

players = targets['players']  # All players

print("Using Amazon Nova Act to scrape eBay...")
print("=" * 70)

for player in players:
    player_name = player['name']
    print(f"\nScraping: {player_name}")
    
    # Ask Nova Act to scrape eBay
    response = client.chat.completions.create(
        model="nova-2-lite-v1",
        messages=[{
            "role": "user",
            "content": f"""Go to eBay and search for sold listings: "{player_name} rookie PSA"

Extract the following data from the last 20 sold listings:
- Title (full listing title)
- Sale price (number only, no currency symbol)
- Sale date (YYYY-MM-DD format)
- Item ID (from the listing URL)
- Condition (Graded or Ungraded)

Return ONLY a JSON array with this exact structure:
[
  {{"title": "...", "sale_price": 450.00, "sale_date": "2026-02-10", "ebay_item_id": "123456789", "condition": "Graded"}}
]

Do not include any explanatory text, only the JSON array."""
        }]
    )
    
    content = response.choices[0].message.content
    print(f"  Nova Act response length: {len(content)} chars")
    
    try:
        # Extract JSON from response
        start = content.find('[')
        end = content.rfind(']') + 1
        json_str = content[start:end]
        
        sales = json.loads(json_str)
        print(f"  Found {len(sales)} sales")
        
        # Send each sale to webhook
        for sale in sales:
            # Add player name and parse card details
            sale['player_name'] = player_name
            
            # Extract year and set from title
            title = sale['title']
            import re
            year_match = re.search(r'\b(20\d{2})\b', title)
            sale['card_year'] = int(year_match.group()) if year_match else 2023
            
            # Extract set
            sets = ['Prizm', 'Select', 'Optic', 'Bowman', 'Topps']
            sale['card_set'] = 'Unknown'
            for s in sets:
                if s.lower() in title.lower():
                    sale['card_set'] = s
                    break
            
            # Detect rookie
            sale['is_rookie'] = bool(re.search(r'\brc\b|\brookie\b', title.lower()))
            
            # Detect grading
            sale['graded'] = sale['condition'] == 'Graded'
            if sale['graded']:
                if 'psa' in title.lower():
                    sale['grade_company'] = 'PSA'
                    grade_match = re.search(r'psa\s*(\d+)', title.lower())
                    sale['grade_value'] = float(grade_match.group(1)) if grade_match else None
                else:
                    sale['grade_company'] = None
                    sale['grade_value'] = None
            
            # Send to webhook
            try:
                resp = requests.post(WEBHOOK_URL, json=sale, timeout=5)
                if resp.status_code == 200:
                    print(f"    ✓ Sent: ${sale['sale_price']}")
                else:
                    print(f"    ✗ Failed: {resp.status_code}")
            except Exception as e:
                print(f"    ✗ Error: {e}")
    
    except Exception as e:
        print(f"  Error parsing response: {e}")
        print(f"  Raw response: {content[:200]}...")

print("\n" + "=" * 70)
print("Scraping complete!")
print("\nNext: Check database and open UI")
print("  python3 backend/debug_pwcc_sales.py")
print("  cd frontend && npm run dev")
