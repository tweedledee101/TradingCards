"""
Collect Real eBay Data for Discovered Players

Reads targets.yaml and collects eBay data for each player.
Uses rate-limit-friendly approach (delays between queries).
"""

import sys
from pathlib import Path
import yaml
import time

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.scrapers.ebay_scraper import EbayScraper
from backend.utils.database import SessionLocal
from backend.models import Card, Sale

print("=" * 70)
print("COLLECTING REAL EBAY DATA FOR DISCOVERED PLAYERS")
print("=" * 70)

# Load targets
with open('config/targets.yaml', 'r') as f:
    targets = yaml.safe_load(f)

players = targets['players'][:3]  # Only first 3 to avoid rate limits

print(f"\nCollecting data for {len(players)} players...")
print("-" * 70)

scraper = EbayScraper()
db = SessionLocal()

for i, player in enumerate(players, 1):
    player_name = player['name']
    sport = player['sport']
    
    print(f"\n{i}. {player_name} ({sport})")
    
    # Search eBay
    query = f"{player_name} rookie PSA"
    print(f"   Searching: {query}")
    
    try:
        results = scraper.search_sold_listings(
            query, 
            days_back=30,
            player_name=player_name,
            sport=sport
        )
        
        print(f"   Found: {len(results)} sales")
        
        # Store in database
        stored = 0
        for sale_data in results:
            # Find or create card
            card = db.query(Card).filter(
                Card.player_name == player_name,
                Card.card_year == sale_data['card_year'],
                Card.card_set == sale_data['card_set']
            ).first()
            
            if not card:
                card = Card(
                    player_name=player_name,
                    sport=sport,
                    card_year=sale_data['card_year'],
                    card_set=sale_data['card_set'],
                    is_rookie=sale_data['is_rookie']
                )
                db.add(card)
                db.flush()
            
            # Create sale
            sale = Sale(
                card_id=card.id,
                sale_price=sale_data['price'],
                sale_date=sale_data['sale_date'],
                ebay_item_id=sale_data['ebay_item_id'],
                graded=sale_data['graded'],
                grade_company=sale_data.get('grade_company'),
                grade_value=sale_data.get('grade_value'),
                listing_title=sale_data['title'],
                source='ebay'
            )
            db.add(sale)
            stored += 1
        
        db.commit()
        print(f"   Stored: {stored} sales in database")
        
        # Rate limiting - wait 10 seconds between players
        if i < len(players):
            print(f"   Waiting 10 seconds (rate limit)...")
            time.sleep(10)
    
    except Exception as e:
        print(f"   ERROR: {e}")
        db.rollback()
        continue

db.close()

print("\n" + "=" * 70)
print("DATA COLLECTION COMPLETE")
print("=" * 70)
print("\nNext: Open dashboard to see real opportunities")
print("  http://localhost:3000")
