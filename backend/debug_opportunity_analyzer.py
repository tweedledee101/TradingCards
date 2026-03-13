"""
Debug Opportunity Analyzer

Check why cards are being filtered out
"""

from backend.utils.database import SessionLocal
from backend.services.opportunity_analyzer import OpportunityAnalyzer
from backend.models import Card, Sale, ActiveListing
from datetime import datetime, timedelta
from sqlalchemy import func

db = SessionLocal()
analyzer = OpportunityAnalyzer()

print("DEBUG: Opportunity Analyzer")
print("=" * 70)

# Get cards with both sales and listings
ninety_days_ago = datetime.now() - timedelta(days=90)

cards_with_sales = db.query(Card.id).join(Sale).filter(
    Sale.sale_date >= ninety_days_ago
).group_by(Card.id).having(
    func.count(Sale.id) >= analyzer.MIN_SALES
).all()

print(f"Cards with >= {analyzer.MIN_SALES} sales: {len(cards_with_sales)}")

for (card_id,) in cards_with_sales[:5]:  # Check first 5
    card = db.query(Card).get(card_id)
    print(f"\n--- Card {card_id}: {card.player_name} - {card.card_year} {card.card_set} ---")
    
    # Get sales
    recent_sales = db.query(Sale).filter(
        Sale.card_id == card_id,
        Sale.sale_date >= ninety_days_ago
    ).order_by(Sale.sale_date.desc()).all()
    
    print(f"Sales count: {len(recent_sales)}")
    
    if len(recent_sales) >= analyzer.MIN_SALES:
        # Check price consistency
        prices = [float(s.sale_price) for s in recent_sales]
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)
        price_range = max_price - min_price
        consistency_ratio = price_range / avg_price if avg_price > 0 else 0
        is_consistent = consistency_ratio <= (1 - analyzer.MIN_PRICE_CONSISTENCY)
        
        print(f"Avg price: ${avg_price:.2f}")
        print(f"Price range: ${min_price:.2f} - ${max_price:.2f} (${price_range:.2f})")
        print(f"Consistency ratio: {consistency_ratio:.2f} (threshold: {1 - analyzer.MIN_PRICE_CONSISTENCY})")
        print(f"Is consistent: {is_consistent}")
        
        # Check listings
        from datetime import date
        listings = db.query(ActiveListing).filter(
            ActiveListing.card_id == card_id,
            ActiveListing.snapshot_date == date.today()
        ).order_by(ActiveListing.listing_price).all()
        
        print(f"Active listings: {len(listings)}")
        
        if listings:
            cheapest = listings[0]
            buy_price = float(cheapest.listing_price)
            sell_price = avg_price
            fees = sell_price * analyzer.FEE_RATE
            gross_profit = sell_price - buy_price
            net_profit = gross_profit - fees
            
            print(f"Buy price: ${buy_price:.2f}")
            print(f"Sell price: ${sell_price:.2f}")
            print(f"Fees (13%): ${fees:.2f}")
            print(f"Net profit: ${net_profit:.2f}")
            print(f"Is profitable: {net_profit > 0}")
            
            if not is_consistent:
                print("❌ FILTERED OUT: Price not consistent")
            elif net_profit <= 0:
                print("❌ FILTERED OUT: Not profitable after fees")
            else:
                print("✅ SHOULD BE AN OPPORTUNITY!")
        else:
            print("❌ FILTERED OUT: No active listings")
    else:
        print(f"❌ FILTERED OUT: Not enough sales ({len(recent_sales)} < {analyzer.MIN_SALES})")

db.close()
