"""
Opportunity Analyzer - Finds profitable arbitrage opportunities with momentum validation

Focuses on:
1. Arbitrage: Can I buy below market and profit after fees?
2. Momentum: Is demand rising? (confidence booster)
"""
from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from backend.models import Card, Sale, ActiveListing


class OpportunityAnalyzer:
    """Analyze cards for arbitrage opportunities with momentum signals"""
    
    # eBay + PayPal fees (13% total)
    FEE_RATE = 0.13
    
    # Minimum data requirements
    MIN_SALES = 3  # Need at least 3 sales for confidence
    MIN_PRICE_CONSISTENCY = 0.50  # Sales within 50% of each other (relaxed for trading cards)
    
    def analyze_card(self, db: Session, card_id: int) -> Optional[Dict]:
        """
        Analyze a single card for opportunity
        
        Returns None if not enough data or no opportunity
        """
        card = db.query(Card).get(card_id)
        if not card:
            return None
        
        # Get recent sales (last 90 days to catch test data with future dates)
        ninety_days_ago = datetime.now() - timedelta(days=90)
        recent_sales = db.query(Sale).filter(
            Sale.card_id == card_id,
            Sale.sale_date >= ninety_days_ago
        ).order_by(Sale.sale_date.desc()).all()
        
        if len(recent_sales) < self.MIN_SALES:
            return None  # Not enough data
        
        # Calculate market metrics
        market_data = self._calculate_market_data(recent_sales)
        # Skip consistency check - trading cards are naturally volatile
        # if not market_data['is_consistent']:
        #     return None  # Too volatile, skip
        
        # Get current listings
        listings = db.query(ActiveListing).filter(
            ActiveListing.card_id == card_id,
            ActiveListing.snapshot_date == date.today()
        ).order_by(ActiveListing.listing_price).all()
        
        if not listings:
            # Try yesterday's listings as fallback
            yesterday = date.today() - timedelta(days=1)
            listings = db.query(ActiveListing).filter(
                ActiveListing.card_id == card_id,
                ActiveListing.snapshot_date == yesterday
            ).order_by(ActiveListing.listing_price).all()
        
        if not listings:
            return None  # No listings available
        
        # Find arbitrage opportunity
        arbitrage = self._calculate_arbitrage(
            market_rate=market_data['avg_price'],
            listings=listings
        )
        
        if not arbitrage['is_profitable']:
            return None  # No profit after fees
        
        # Filter out very low profit opportunities (minimum $5 profit OR 15% ROI)
        if arbitrage['net_profit'] < 5 and arbitrage['roi'] < 15:
            return None  # Not worth the effort
        
        # Calculate momentum signals
        momentum = self._calculate_momentum(db, card_id, recent_sales)
        
        # Calculate opportunity score (70% arbitrage, 30% momentum)
        opportunity_score = (
            arbitrage['profit_score'] * 0.7 +
            momentum['momentum_score'] * 0.3
        )
        
        return {
            'card_id': card_id,
            'player_name': card.player_name,
            'card_year': card.card_year,
            'card_set': card.card_set,
            'card_number': card.card_number,
            'parallel': card.parallel,
            'grade_company': card.grade_company,
            'grade_value': float(card.grade_value) if card.grade_value else None,
            'is_rookie': card.is_rookie,
            'sport': card.sport,
            'market_data': market_data,
            'arbitrage': arbitrage,
            'momentum': momentum,
            'opportunity_score': round(opportunity_score, 1),
            'confidence': self._get_confidence_level(momentum['momentum_score'])
        }
    
    def _calculate_market_data(self, sales: List[Sale]) -> Dict:
        """Calculate market rate and consistency from recent sales"""
        prices = [float(s.sale_price) for s in sales]
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)
        
        # Check price consistency (are sales within 20% of average?)
        price_range = max_price - min_price
        is_consistent = (price_range / avg_price) <= (1 - self.MIN_PRICE_CONSISTENCY)
        
        # Calculate average days to sell (estimate based on sales velocity)
        days_span = (sales[0].sale_date - sales[-1].sale_date).days or 1
        sales_per_day = len(sales) / days_span if days_span > 0 else 0
        
        # Estimate days to sell based on velocity
        if sales_per_day >= 1:
            est_days_to_sell = 7  # Quick flip - sells within a week
            flip_speed = 'QUICK FLIP 🚀'
        elif sales_per_day >= 0.5:
            est_days_to_sell = 14  # Medium - 2 weeks
            flip_speed = 'MEDIUM ⏱️'
        elif sales_per_day >= 0.2:
            est_days_to_sell = 30  # Slow - 1 month
            flip_speed = 'SLOW 🐌'
        else:
            est_days_to_sell = 60  # Very slow - sit and wait
            flip_speed = 'SIT & WAIT 💤'
        
        return {
            'avg_price': round(avg_price, 2),
            'min_price': round(min_price, 2),
            'max_price': round(max_price, 2),
            'price_range': round(price_range, 2),
            'is_consistent': is_consistent,
            'sales_count': len(sales),
            'avg_days_to_sell': round(est_days_to_sell, 1),
            'flip_speed': flip_speed
        }
    
    def _calculate_arbitrage(self, market_rate: float, listings: List[ActiveListing]) -> Dict:
        """Calculate arbitrage opportunity from current listings"""
        if not listings:
            return {'is_profitable': False}
        
        # Find cheapest listing
        cheapest = listings[0]
        buy_price = float(cheapest.listing_price)
        
        # Calculate profit after fees
        sell_price = market_rate
        fees = sell_price * self.FEE_RATE
        gross_profit = sell_price - buy_price
        net_profit = gross_profit - fees
        
        # Calculate ROI
        roi = (net_profit / buy_price * 100) if buy_price > 0 else 0
        
        # Profit score (0-100): 50% ROI = 100 points
        profit_score = min(roi * 2, 100)
        
        return {
            'is_profitable': net_profit > 0,
            'buy_price': round(buy_price, 2),
            'sell_price': round(sell_price, 2),
            'gross_profit': round(gross_profit, 2),
            'fees': round(fees, 2),
            'net_profit': round(net_profit, 2),
            'roi': round(roi, 1),
            'profit_score': round(profit_score, 1),
            'available_listings': len(listings),
            'ebay_item_id': cheapest.ebay_item_id,
            'ebay_url': f"https://www.ebay.com/itm/{cheapest.ebay_item_id}" if cheapest.ebay_item_id else None
        }
    
    def _calculate_momentum(self, db: Session, card_id: int, recent_sales: List[Sale]) -> Dict:
        """Calculate momentum signals (price trend, velocity, supply)"""
        
        # Price trend (90 days vs 45 days vs now)
        ninety_days_ago = datetime.now() - timedelta(days=90)
        fortyfive_days_ago = datetime.now() - timedelta(days=45)
        
        old_sales = [s for s in recent_sales if s.sale_date < fortyfive_days_ago]
        new_sales = [s for s in recent_sales if s.sale_date >= fortyfive_days_ago]
        
        if old_sales and new_sales:
            old_avg = sum(float(s.sale_price) for s in old_sales) / len(old_sales)
            new_avg = sum(float(s.sale_price) for s in new_sales) / len(new_sales)
            price_change = ((new_avg - old_avg) / old_avg * 100) if old_avg > 0 else 0
            price_trend = '↑' if price_change > 5 else ('↓' if price_change < -5 else '→')
        else:
            price_change = 0
            price_trend = '→'
        
        # Sales velocity (sales per week)
        days_span = (recent_sales[0].sale_date - recent_sales[-1].sale_date).days or 1
        sales_per_week = len(recent_sales) / (days_span / 7) if days_span > 0 else 0
        
        # Supply (current listings)
        listings_count = db.query(ActiveListing).filter(
            ActiveListing.card_id == card_id,
            ActiveListing.snapshot_date == date.today()
        ).count()
        
        # Sell-through rate
        str_rate = (len(recent_sales) / listings_count * 100) if listings_count > 0 else 100
        
        # Momentum score (0-100)
        # Price trend: +20% = 50 points, 0% = 25 points, -20% = 0 points
        price_score = max(0, min((price_change + 20) * 1.25, 50))
        
        # STR: 100%+ = 50 points, 50% = 25 points, 0% = 0 points
        str_score = min(str_rate / 2, 50)
        
        momentum_score = price_score + str_score
        
        return {
            'price_change_45d': round(price_change, 1),
            'price_trend': price_trend,
            'sales_per_week': round(sales_per_week, 1),
            'str_rate': round(str_rate, 1),
            'active_listings': listings_count,
            'momentum_score': round(momentum_score, 1)
        }
    
    def _get_confidence_level(self, momentum_score: float) -> str:
        """Convert momentum score to confidence level"""
        if momentum_score >= 70:
            return 'VERY HIGH 🔥'
        elif momentum_score >= 50:
            return 'HIGH ✅'
        elif momentum_score >= 30:
            return 'MEDIUM ⚠️'
        else:
            return 'LOW 🥶'
    
    def find_opportunities(
        self,
        db: Session,
        min_budget: Optional[float] = None,
        max_budget: Optional[float] = None,
        min_profit: Optional[float] = None,
        min_roi: Optional[float] = None,
        momentum_filter: Optional[str] = None,  # 'rising', 'stable', 'all'
        limit: int = 20
    ) -> List[Dict]:
        """
        Find all opportunities matching filters
        
        Returns list sorted by opportunity_score (best first)
        """
        # Get all cards with recent sales (last 90 days)
        ninety_days_ago = datetime.now() - timedelta(days=90)
        
        cards_with_sales = db.query(Card.id).join(Sale).filter(
            Sale.sale_date >= ninety_days_ago
        ).group_by(Card.id).having(
            func.count(Sale.id) >= self.MIN_SALES
        ).all()
        
        opportunities = []
        for (card_id,) in cards_with_sales:
            opp = self.analyze_card(db, card_id)
            if not opp:
                continue
            
            # Apply filters
            if min_budget and opp['arbitrage']['buy_price'] < min_budget:
                continue
            if max_budget and opp['arbitrage']['buy_price'] > max_budget:
                continue
            if min_profit and opp['arbitrage']['net_profit'] < min_profit:
                continue
            if min_roi and opp['arbitrage']['roi'] < min_roi:
                continue
            if momentum_filter == 'rising' and opp['momentum']['price_trend'] != '↑':
                continue
            if momentum_filter == 'stable' and opp['momentum']['price_trend'] == '↓':
                continue
            
            opportunities.append(opp)
        
        # Sort by opportunity score (best first)
        opportunities.sort(key=lambda x: x['opportunity_score'], reverse=True)
        
        return opportunities[:limit]
