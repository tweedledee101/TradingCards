"""
Test PWCC Webhook Endpoint

Tests that the PWCC webhook correctly receives and stores sales data.
"""

import sys
from pathlib import Path
import requests
import json

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test data - realistic PWCC sales
test_sales = [
    {
        "player_name": "Victor Wembanyama",
        "sport": "Basketball",
        "card_year": 2023,
        "card_set": "Prizm",
        "sale_price": 450.00,
        "sale_date": "2026-02-10",
        "is_rookie": True,
        "graded": True,
        "title": "2023 Panini Prizm Victor Wembanyama RC PSA 10"
    },
    {
        "player_name": "Paul Skenes",
        "sport": "Baseball",
        "card_year": 2024,
        "card_set": "Bowman Chrome",
        "sale_price": 380.00,
        "sale_date": "2026-02-11",
        "is_rookie": True,
        "graded": True,
        "title": "2024 Bowman Chrome Paul Skenes RC PSA 10"
    },
    {
        "player_name": "Caitlin Clark",
        "sport": "Basketball",
        "card_year": 2024,
        "card_set": "Prizm",
        "sale_price": 520.00,
        "sale_date": "2026-02-12",
        "is_rookie": True,
        "graded": True,
        "title": "2024 Panini Prizm Caitlin Clark RC PSA 10"
    }
]

API_URL = "http://localhost:8000/api/webhooks/novaact/pwcc"

print("Testing PWCC Webhook Endpoint")
print("=" * 60)

# Test each sale
success_count = 0
for i, sale in enumerate(test_sales, 1):
    print(f"\nTest {i}/{len(test_sales)}: {sale['player_name']}")
    
    try:
        response = requests.post(API_URL, json=sale, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"  SUCCESS: {result['message']}")
            print(f"  Card ID: {result['card_id']}")
            print(f"  Sale Price: ${result['sale_price']:.2f}")
            success_count += 1
        else:
            print(f"  FAILED: Status {response.status_code}")
            print(f"  Error: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print(f"  ERROR: Cannot connect to API server")
        print(f"  Make sure API is running: python3 -m backend.api.run")
        break
    
    except Exception as e:
        print(f"  ERROR: {e}")

print("\n" + "=" * 60)
print(f"Results: {success_count}/{len(test_sales)} sales recorded successfully")

if success_count == len(test_sales):
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")

# Verify data was stored
print("\n" + "=" * 60)
print("Verifying data in database...")

try:
    from backend.utils.database import SessionLocal
    from backend.models import Card, Sale
    from sqlalchemy import and_
    
    db = SessionLocal()
    
    for sale_data in test_sales:
        card = db.query(Card).filter(
            and_(
                Card.player_name == sale_data['player_name'],
                Card.card_year == sale_data['card_year'],
                Card.card_set == sale_data['card_set']
            )
        ).first()
        
        if card:
            sales_count = db.query(Sale).filter(Sale.card_id == card.id).count()
            print(f"  {card.player_name}: Card ID {card.id}, {sales_count} sale(s) recorded")
        else:
            print(f"  {sale_data['player_name']}: NOT FOUND IN DATABASE")
    
    db.close()
    print("\nDatabase verification complete")

except Exception as e:
    print(f"  Database verification failed: {e}")
