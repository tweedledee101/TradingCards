"""
Sell-Through Rate Calculator
Calculates sell-through rates from existing eBay data (sales vs listings)
No external scraping needed - uses data already in database
"""
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.utils.database import SessionLocal
from backend.models import Card, Sale, ActiveListing, PriceTrend

class SellThroughCalculator:
    """Calculate sell-through rates from eBay data"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def calculate_sell_through(self, card_id: int, days_back: int = 14) -> dict:
        """
        Calculate sell-through rate for a card
        
        Sell-through rate = (Sales / Total Listings) * 100
        Higher = better (card is selling fast)
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        # Count sales in period
        sales_count = self.db.query(Sale).filter(
            Sale.card_id == card_id,
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date
        ).count()
        
        # Get average active listings
        listings_count = self.db.query(func.avg(func.count(ActiveListing.id))).filter(
            ActiveListing.card_id == card_id,
            ActiveListing.snapshot_date >= start_date,
            ActiveListing.snapshot_date <= end_date
        ).group_by(ActiveListing.snapshot_date).scalar()
        
        listings_count = float(listings_count) if listings_count else 0
        
        # Calculate sell-through rate
        if listings_count > 0:
            sell_through_rate = (sales_count / (sales_count + listings_count)) * 100
        else:
            sell_through_rate = 0
        
        # Calculate listings-to-sales ratio (lower is better)
        if sales_count > 0:
            listings_to_sales = listings_count / sales_count
        else:
            listings_to_sales = 999  # High number = bad
        
        # Calculate average days to sell
        avg_days = self._calculate_avg_days_to_sell(card_id, days_back)
        
        return {
            'card_id': card_id,
            'sales_count': sales_count,
            'avg_listings': round(listings_count, 1),
            'sell_through_rate': round(sell_through_rate, 2),
            'listings_to_sales_ratio': round(listings_to_sales, 2),
            'avg_days_to_sell': avg_days,
            'period_days': days_back,
            'calculated_date': date.today().isoformat()
        }
    
    def _calculate_avg_days_to_sell(self, card_id: int, days_back: int) -> float:
        """
        Estimate average days to sell based on sales velocity
        Simple heuristic: days_back / sales_count
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        sales_count = self.db.query(Sale).filter(
            Sale.card_id == card_id,
            Sale.sale_date >= start_date
        ).count()
        
        if sales_count > 0:
            return round(days_back / sales_count, 1)
        return 999.0  # No sales = very slow
    
    def update_all_cards(self, days_back: int = 14) -> int:
        """
        Calculate sell-through for all cards and update price_trends
        """
        cards = self.db.query(Card).all()
        updated = 0
        
        for card in cards:
            metrics = self.calculate_sell_through(card.id, days_back)
            
            # Update today's price trend
            trend = self.db.query(PriceTrend).filter(
                PriceTrend.card_id == card.id,
                PriceTrend.trend_date == date.today()
            ).first()
            
            if trend:
                trend.sell_through_rate = metrics['sell_through_rate']
                trend.avg_days_to_sell = metrics['avg_days_to_sell']
                trend.listings_to_sales_ratio = metrics['listings_to_sales_ratio']
                updated += 1
        
        self.db.commit()
        return updated
    
    def get_fast_movers(self, min_sell_through: float = 50.0, limit: int = 20) -> list:
        """
        Get cards with high sell-through rates (fast sellers)
        """
        today = date.today()
        
        results = self.db.query(PriceTrend, Card).join(Card).filter(
            PriceTrend.trend_date == today,
            PriceTrend.sell_through_rate >= min_sell_through
        ).order_by(PriceTrend.sell_through_rate.desc()).limit(limit).all()
        
        fast_movers = []
        for trend, card in results:
            fast_movers.append({
                'player_name': card.player_name,
                'card_year': card.card_year,
                'card_set': card.card_set,
                'sell_through_rate': float(trend.sell_through_rate),
                'avg_days_to_sell': float(trend.avg_days_to_sell) if trend.avg_days_to_sell else None,
                'hotness_score': float(trend.hotness_score) if trend.hotness_score else 0
            })
        
        return fast_movers
    
    def close(self):
        self.db.close()

def main():
    """Run sell-through calculation for all cards"""
    print(f"🚀 Sell-Through Calculator started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("📊 Calculating from existing eBay data (no external scraping needed)")
    
    calculator = SellThroughCalculator()
    
    try:
        updated = calculator.update_all_cards(days_back=14)
        print(f"\n✅ Updated sell-through rates for {updated} cards")
        
        # Show top fast movers
        print("\n🔥 Top 10 Fast Movers (High Sell-Through):")
        print("-" * 80)
        fast_movers = calculator.get_fast_movers(min_sell_through=30.0, limit=10)
        
        for i, card in enumerate(fast_movers, 1):
            print(f"{i}. {card['player_name']} {card['card_year']} {card['card_set']}")
            print(f"   Sell-Through: {card['sell_through_rate']:.1f}% | "
                  f"Avg Days to Sell: {card['avg_days_to_sell']:.1f} | "
                  f"Hotness: {card['hotness_score']:.1f}")
        
        print(f"\n✅ Complete!")
        
    finally:
        calculator.close()

if __name__ == '__main__':
    main()
