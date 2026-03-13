"""
Grading Opportunity Analyzer

Finds raw cards that can be graded and sold for profit.

Strategy:
1. Buy raw card ($15-$30)
2. Grade with PSA ($25 fee)
3. Sell PSA 10 for $100+
4. Profit = PSA 10 price - raw price - $25 grading fee
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from backend.models import Card, Sale, GradingPopulation

class GradingOpportunityAnalyzer:
    """Find cards worth grading for profit"""
    
    GRADING_FEE = 25.0  # PSA grading fee
    MIN_PSA_10_RATE = 0.15  # Need at least 15% PSA 10 rate
    MIN_PROFIT = 50.0  # Minimum profit after grading
    
    def analyze_card(self, db: Session, card_id: int) -> Optional[Dict]:
        """Analyze if a card is worth grading"""
        card = db.query(Card).get(card_id)
        if not card:
            return None
        
        # Get PSA 10 rate
        grading = db.query(GradingPopulation).filter(
            GradingPopulation.card_id == card_id
        ).first()
        
        if not grading or not grading.psa_10_rate:
            return None  # No grading data
        
        psa_10_rate = float(grading.psa_10_rate)
        if psa_10_rate < self.MIN_PSA_10_RATE:
            return None  # Too hard to grade
        
        # Get raw card prices (ungraded sales)
        ninety_days_ago = datetime.now() - timedelta(days=90)
        raw_sales = db.query(Sale).filter(
            Sale.card_id == card_id,
            Sale.graded == False,
            Sale.sale_date >= ninety_days_ago
        ).all()
        
        if len(raw_sales) < 3:
            return None  # Not enough raw sales
        
        avg_raw_price = sum(float(s.sale_price) for s in raw_sales) / len(raw_sales)
        
        # Get PSA 10 prices
        psa_10_sales = db.query(Sale).filter(
            Sale.card_id == card_id,
            Sale.graded == True,
            Sale.grade_company == 'PSA',
            Sale.grade_value == 10.0,
            Sale.sale_date >= ninety_days_ago
        ).all()
        
        if len(psa_10_sales) < 3:
            return None  # Not enough PSA 10 sales
        
        avg_psa_10_price = sum(float(s.sale_price) for s in psa_10_sales) / len(psa_10_sales)
        
        # Calculate profit
        total_cost = avg_raw_price + self.GRADING_FEE
        gross_profit = avg_psa_10_price - total_cost
        fees = avg_psa_10_price * 0.13  # eBay fees on sale
        net_profit = gross_profit - fees
        roi = (net_profit / total_cost * 100) if total_cost > 0 else 0
        
        if net_profit < self.MIN_PROFIT:
            return None  # Not profitable enough
        
        return {
            'card_id': card_id,
            'player_name': card.player_name,
            'card_year': card.card_year,
            'card_set': card.card_set,
            'is_rookie': card.is_rookie,
            'sport': card.sport,
            'opportunity_type': 'GRADING',
            'raw_price': round(avg_raw_price, 2),
            'grading_fee': self.GRADING_FEE,
            'psa_10_price': round(avg_psa_10_price, 2),
            'total_cost': round(total_cost, 2),
            'net_profit': round(net_profit, 2),
            'roi': round(roi, 1),
            'psa_10_rate': round(psa_10_rate * 100, 1),
            'confidence': self._get_confidence(psa_10_rate, net_profit),
            'raw_sales_count': len(raw_sales),
            'psa_10_sales_count': len(psa_10_sales)
        }
    
    def _get_confidence(self, psa_10_rate: float, profit: float) -> str:
        """Calculate confidence based on PSA 10 rate and profit"""
        if psa_10_rate >= 0.30 and profit >= 100:
            return 'VERY HIGH 🔥'
        elif psa_10_rate >= 0.20 and profit >= 75:
            return 'HIGH ✅'
        elif psa_10_rate >= 0.15 and profit >= 50:
            return 'MEDIUM ⚠️'
        else:
            return 'LOW 🥶'
    
    def find_grading_opportunities(
        self,
        db: Session,
        max_raw_price: Optional[float] = None,
        min_psa_10_rate: Optional[float] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Find all grading opportunities"""
        
        # Get all cards with grading data
        cards_with_grading = db.query(Card.id).join(GradingPopulation).filter(
            GradingPopulation.psa_10_rate >= (min_psa_10_rate or self.MIN_PSA_10_RATE)
        ).all()
        
        opportunities = []
        for (card_id,) in cards_with_grading:
            opp = self.analyze_card(db, card_id)
            if opp:
                if max_raw_price and opp['raw_price'] > max_raw_price:
                    continue
                opportunities.append(opp)
        
        # Sort by ROI
        opportunities.sort(key=lambda x: x['roi'], reverse=True)
        return opportunities[:limit]
