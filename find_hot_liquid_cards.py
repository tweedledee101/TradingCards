#!/usr/bin/env python3
"""
Find Hot Liquid Cards with Low Competition

Combines multiple signals to find cards with:
1. High liquidity (proven sellers)
2. Low competition (few active listings)
3. Rising prices (momentum)
"""
from backend.utils.database import SessionLocal
from backend.models import Card, Sale, ActiveListing
from sqlalchemy import func
from datetime import datetime, timedelta

def find_hot_liquid_cards(min_sales=3, days=30, min_ratio=0.3):
    """
    Find cards that are:
    - Liquid: min_sales in last X days
    - Low competition: sales/listings ratio > min_ratio
    - Has card number (can be scraped)
    
    Args:
        min_sales: Minimum sales in period (default 3)
        days: Period to analyze (default 30)
        min_ratio: Minimum sales/listings ratio (default 0.3 = 30%)
    """
    db = SessionLocal()
    cutoff = datetime.now() - timedelta(days=days)
    
    # Get cards with sales data
    cards_with_sales = db.query(
        Card.id,
        Card.player_name,
        Card.card_year,
        Card.card_set,
        Card.card_number,
        func.count(Sale.id).label('sales_count'),
        func.avg(Sale.sale_price).label('avg_price')
    ).join(Sale).filter(
        Card.sport == 'Baseball',
        Card.card_number.isnot(None),
        Sale.sale_date >= cutoff
    ).group_by(
        Card.id,
        Card.player_name,
        Card.card_year,
        Card.card_set,
        Card.card_number
    ).having(
        func.count(Sale.id) >= min_sales
    ).all()
    
    print(f"Found {len(cards_with_sales)} cards with {min_sales}+ sales in last {days} days")
    
    # Check active listings for each card
    results = []
    
    for card in cards_with_sales:
        # Get active listings count
        listings_count = db.query(func.count(ActiveListing.id)).filter(
            ActiveListing.card_id == card.id
        ).scalar() or 0
        
        # Calculate supply/demand ratio
        if listings_count > 0:
            ratio = card.sales_count / listings_count
        else:
            ratio = card.sales_count  # No competition!
        
        # Only include if ratio meets threshold
        if ratio >= min_ratio:
            results.append({
                'player_name': card.player_name,
                'card_year': card.card_year,
                'card_set': card.card_set,
                'card_number': card.card_number,
                'sales': card.sales_count,
                'listings': listings_count,
                'ratio': ratio,
                'avg_price': float(card.avg_price) if card.avg_price else 0,
                'competition': 'NONE' if listings_count == 0 else 'LOW' if ratio > 1.0 else 'MEDIUM'
            })
    
    db.close()
    
    # Sort by ratio (highest first)
    results.sort(key=lambda x: x['ratio'], reverse=True)
    
    return results

if __name__ == '__main__':
    print("=" * 80)
    print("HOT LIQUID CARDS FINDER")
    print("=" * 80)
    
    # Find cards with good supply/demand ratio
    hot_cards = find_hot_liquid_cards(min_sales=3, days=30, min_ratio=0.3)
    
    print(f"\nFound {len(hot_cards)} cards with low competition:\n")
    
    for i, card in enumerate(hot_cards[:20], 1):
        print(f"{i}. {card['player_name']} {card['card_year']} {card['card_set']} #{card['card_number']}")
        print(f"   Sales: {card['sales']} | Listings: {card['listings']} | Ratio: {card['ratio']:.2f} | Competition: {card['competition']}")
        print(f"   Avg Price: ${card['avg_price']:.2f}")
        print()
    
    if len(hot_cards) > 20:
        print(f"... and {len(hot_cards) - 20} more")
    
    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    print("1. Run scrape_scp_selenium.py on these cards to get variations")
    print("2. Search eBay for active listings of these specific cards")
    print("3. Buy cards with low competition and proven demand")
