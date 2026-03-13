"""
Simple Opportunity Finder - Uses ONLY sold listings data (no active listings needed)

Strategy:
1. Find cards with recent sales (last 30 days)
2. Calculate market rate from sales
3. Show cards where you can potentially buy below market
4. NO API calls for active listings (user searches manually)
"""

from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy import func
from backend.utils.database import SessionLocal
from backend.models import Card, Sale

def find_simple_opportunities(min_budget: float = None, max_budget: float = None) -> List[Dict]:
    """
    Find opportunities using ONLY sold listings data
    
    Returns cards with:
    - Recent sales (market rate established)
    - Price within user budget
    - Buy zone calculated (7% below market)
    """
    db = SessionLocal()
    try:
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        # Get all cards with recent sales
        cards_with_sales = db.query(
            Card.id,
            Card.player_name,
            Card.card_year,
            Card.card_set,
            Card.sport,
            Card.is_rookie,
            func.avg(Sale.sale_price).label('avg_price'),
            func.count(Sale.id).label('sales_count')
        ).join(Sale).filter(
            Sale.sale_date >= thirty_days_ago
        ).group_by(
            Card.id,
            Card.player_name,
            Card.card_year,
            Card.card_set,
            Card.sport,
            Card.is_rookie
        ).having(
            func.count(Sale.id) >= 3  # At least 3 sales
        ).all()
        
        opportunities = []
        for card in cards_with_sales:
            avg_price = float(card.avg_price)
            buy_zone = avg_price * 0.93  # Buy 7% below market
            
            # Filter by budget
            if min_budget and buy_zone < min_budget:
                continue
            if max_budget and buy_zone > max_budget:
                continue
            
            # Calculate potential profit
            fees = avg_price * 0.13
            net_profit = avg_price - buy_zone - fees
            roi = (net_profit / buy_zone * 100) if buy_zone > 0 else 0
            
            opportunities.append({
                'id': card.id,
                'player_name': card.player_name,
                'card_year': card.card_year,
                'card_set': card.card_set,
                'sport': card.sport,
                'is_rookie': card.is_rookie,
                'avg_price': round(avg_price, 2),
                'buy_zone': round(buy_zone, 2),
                'net_profit': round(net_profit, 2),
                'roi': round(roi, 1),
                'sales_count': card.sales_count,
                'hotness_score': 50.0  # Placeholder
            })
        
        # Sort by ROI
        opportunities.sort(key=lambda x: x['roi'], reverse=True)
        
        return opportunities
        
    finally:
        db.close()

if __name__ == '__main__':
    print("Finding opportunities from sold listings only...")
    opps = find_simple_opportunities(max_budget=350)
    
    print(f"\nFound {len(opps)} opportunities under $350:")
    for i, opp in enumerate(opps[:20], 1):
        print(f"{i:2d}. {opp['player_name']:30s} {opp['card_year']} {opp['card_set']:15s} "
              f"Market: ${opp['avg_price']:6.2f} Buy: ${opp['buy_zone']:6.2f} "
              f"Profit: ${opp['net_profit']:5.2f} ({opp['roi']:4.1f}% ROI)")
