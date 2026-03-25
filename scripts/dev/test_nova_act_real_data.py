"""
Test Nova Act - Real vs Fake Data

Asks Nova Act to scrape eBay and checks if data looks real.
"""

import os
import json
from openai import OpenAI

NOVA_API_KEY = os.getenv('NOVA_API_KEY')

client = OpenAI(
    api_key=NOVA_API_KEY,
    base_url="https://api.nova.amazon.com/v1"
)

print("Testing Nova Act with a simple eBay search...")
print("=" * 70)

# Test with a common card
response = client.chat.completions.create(
    model="nova-2-lite-v1",
    messages=[{
        "role": "user",
        "content": """Go to eBay.com and search for: "2023 Topps Chrome Julio Rodriguez"

Find SOLD listings (completed sales).

Extract 5 recent sales with:
- Exact title from eBay
- Sale price (exact number from eBay)
- Sale date (exact date from eBay)
- eBay item number (from URL)

Return ONLY JSON array. No explanations.
[
  {"title": "...", "sale_price": 45.00, "sale_date": "2026-02-10", "ebay_item_id": "123456789"}
]"""
    }]
)

content = response.choices[0].message.content
print("\nNova Act Response:")
print("-" * 70)
print(content)
print("-" * 70)

try:
    start = content.find('[')
    end = content.rfind(']') + 1
    sales = json.loads(content[start:end])
    
    print(f"\n✓ Parsed {len(sales)} sales")
    print("\nData Analysis:")
    print("-" * 70)
    
    for i, sale in enumerate(sales, 1):
        print(f"\n{i}. {sale.get('title', 'NO TITLE')}")
        print(f"   Price: ${sale.get('sale_price', 0)}")
        print(f"   Date: {sale.get('sale_date', 'NO DATE')}")
        print(f"   Item ID: {sale.get('ebay_item_id', 'NO ID')}")
    
    # Check if data looks real
    print("\n" + "=" * 70)
    print("REALITY CHECK:")
    print("=" * 70)
    
    prices = [s.get('sale_price', 0) for s in sales]
    avg_price = sum(prices) / len(prices) if prices else 0
    
    print(f"Average price: ${avg_price:.2f}")
    print(f"Price range: ${min(prices):.2f} - ${max(prices):.2f}")
    
    # Check for suspicious patterns
    if len(set(prices)) == 1:
        print("⚠️  WARNING: All prices are identical (likely fake)")
    elif all(p % 50 == 0 for p in prices):
        print("⚠️  WARNING: All prices are round numbers (likely fake)")
    else:
        print("✓ Prices look realistic (varied)")
    
    # Check item IDs
    item_ids = [s.get('ebay_item_id', '') for s in sales]
    if all(len(str(id)) < 5 for id in item_ids):
        print("⚠️  WARNING: Item IDs too short (likely fake)")
    else:
        print("✓ Item IDs look realistic")
    
    # Check dates
    dates = [s.get('sale_date', '') for s in sales]
    if all(d == dates[0] for d in dates):
        print("⚠️  WARNING: All dates identical (likely fake)")
    else:
        print("✓ Dates look realistic (varied)")

except Exception as e:
    print(f"\n✗ Error parsing response: {e}")

print("\n" + "=" * 70)
print("CONCLUSION:")
print("If you see warnings above, Nova Act is generating fake data.")
print("If all checks pass, Nova Act is scraping real eBay data.")
print("=" * 70)
