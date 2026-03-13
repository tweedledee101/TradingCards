"""
Generate Active Listings from Sales Data

Creates realistic active listings based on existing sales:
- 80% of listings priced BELOW average (opportunity zone)
- 20% of listings priced ABOVE average (overpriced)
- Price range: 70%-130% of average sale price
"""
import sys
sys.path.insert(0, '/app')

from backend.utils.database import SessionLocal
from backend.models import Card, Sale, ActiveListing
from datetime import datetime, timedelta, date
import random

db = SessionLocal()

# Get all cards with sales
ninety_days_ago = datetime.now() - timedelta(days=90)
cards_with_sales = db.query(Card).join(Sale).filter(
    Sale.sale_date >= ninety_days_ago
).distinct().all()

print(f"Found {len(cards_with_sales)} cards with sales")
print("Generating active listings...\n")

total_created = 0

for card in cards_with_sales:
    # Get sales for this card
    sales = db.query(Sale).filter(
        Sale.card_id == card.id,
        Sale.sale_date >= ninety_days_ago
    ).all()
    
    if len(sales) < 3:
        continue
    
    # Calculate average sale price
    avg_price = float(sum(s.sale_price for s in sales) / len(sales))
    
    # Generate 3-8 active listings per card
    num_listings = random.randint(3, 8)
    
    for i in range(num_listings):
        # 80% chance of below-average price (opportunity)
        if random.random() < 0.8:
            # Below average: 70%-95% of avg
            price = avg_price * random.uniform(0.70, 0.95)
        else:
            # Above average: 105%-130% of avg
            price = avg_price * random.uniform(1.05, 1.30)
        
        listing = ActiveListing(
            card_id=card.id,
            ebay_item_id=f"MOCK{card.id}{i}{random.randint(1000,9999)}",
            listing_price=round(price, 2),
            listing_type='buy_it_now',
            snapshot_date=date.today()
        )
        db.add(listing)
        total_created += 1
    
    print(f"✓ {card.player_name} ({card.card_year} {card.card_set}): {num_listings} listings (avg ${avg_price:.2f})")

db.commit()
db.close()

print(f"\n{'='*70}")
print(f"Created {total_created} active listings")
print("Run Phase 2 test now!")
