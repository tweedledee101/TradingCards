"""
Manual Data Entry - Quick way to get live data in

Go to eBay, copy sold listings, paste here.
"""

import requests
from datetime import datetime, timedelta

WEBHOOK_URL = "http://localhost:8000/api/webhooks/novaact/ebay"

# INSTRUCTIONS:
# 1. Go to eBay: https://www.ebay.com/sch/i.html?_nkw=Victor+Wembanyama+rookie+PSA&LH_Sold=1&LH_Complete=1
# 2. Copy 10-20 sold listings (title, price, date)
# 3. Paste them below in the format shown
# 4. Run: python3 backend/manual_data_entry.py

sales = [
    # Format: (player_name, title, price, days_ago)
    ("Victor Wembanyama", "2023 Panini Prizm Victor Wembanyama RC PSA 10", 450.00, 2),
    ("Victor Wembanyama", "2023 Select Victor Wembanyama Rookie PSA 9", 280.00, 3),
    ("Victor Wembanyama", "2023 Prizm Victor Wembanyama Base RC PSA 10", 425.00, 1),
    ("Victor Wembanyama", "2023 Optic Victor Wembanyama Rookie PSA 10", 380.00, 4),
    ("Victor Wembanyama", "2023 Prizm Victor Wembanyama RC Raw", 150.00, 2),
    
    ("Paul Skenes", "2024 Bowman Chrome Paul Skenes RC PSA 10", 520.00, 1),
    ("Paul Skenes", "2024 Topps Paul Skenes Rookie PSA 9", 180.00, 3),
    ("Paul Skenes", "2024 Bowman Paul Skenes Auto PSA 10", 1200.00, 2),
    
    ("Caitlin Clark", "2024 Prizm Caitlin Clark Rookie PSA 10", 380.00, 1),
    ("Caitlin Clark", "2024 Select Caitlin Clark RC PSA 9", 220.00, 2),
]

print("Sending manual data to database...")
print("=" * 70)

count = 0
for player_name, title, price, days_ago in sales:
    sale_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
    
    # Parse details
    import re
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
    
    payload = {
        'player_name': player_name,
        'title': title,
        'sale_price': price,
        'sale_date': sale_date,
        'ebay_item_id': str(hash(title))[:10],
        'card_year': card_year,
        'card_set': card_set,
        'is_rookie': is_rookie,
        'graded': graded,
        'grade_company': grade_company,
        'grade_value': grade_value,
        'condition': 'Graded' if graded else 'Ungraded'
    }
    
    try:
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=5)
        if resp.status_code == 200:
            count += 1
            print(f"✓ {player_name}: ${price} - {title[:60]}")
        else:
            print(f"✗ Failed: {resp.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")

print("=" * 70)
print(f"Sent {count}/{len(sales)} sales to database")
print("\nNext: Check opportunities")
print("  python3 -m backend.test_opportunities")
