"""
Opportunity Analyzer - Finds profitable arbitrage opportunities with momentum validation

Rules:
  1. Never show negative profit opportunities
  2. Minimum $10 net profit to be worth pursuing
  3. Auctions are primary opportunities (ending below market = real deals)
  4. BIN below market is secondary (rare but valuable when found)
  5. Every opportunity must have SCP market rate
"""
from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from backend.models import Card, Sale, ActiveListing, MarketRate
from backend.utils.listing_filter import is_noise_listing


class OpportunityAnalyzer:
    """Analyze cards for arbitrage opportunities with momentum signals"""
    
    FEE_RATE = 0.13
    MIN_SALES = 3
    MIN_PROFIT = 10.0  # Minimum $10 net profit
    
    def analyze_card(self, db: Session, card_id: int) -> Optional[Dict]:
        card = db.query(Card).get(card_id)
        if not card:
            return None
        
        # Get recent sales (last 90 days)
        ninety_days_ago = datetime.now() - timedelta(days=90)
        recent_sales = db.query(Sale).filter(
            Sale.card_id == card_id,
            Sale.sale_date >= ninety_days_ago
        ).order_by(Sale.sale_date.desc()).all()
        
        if len(recent_sales) < self.MIN_SALES:
            return None
        
        market_data = self._calculate_market_data(recent_sales)
        
        # Require SCP market rate
        scp_rate = self._get_market_rate(db, card_id, card)
        if not scp_rate:
            return None
        
        sell_price = scp_rate['sell_price']
        
        # Sanity check: SCP rate vs actual sales (3x threshold)
        avg_sale = market_data['avg_price']
        median_sale = market_data['median_price']
        if avg_sale > 0 and median_sale > 0:
            ratio = sell_price / avg_sale
            ratio_median = sell_price / median_sale
            if ratio > 3 and ratio_median > 3:
                return None
        
        # Get current listings (last 7 days)
        week_ago = date.today() - timedelta(days=7)
        listings = db.query(ActiveListing).filter(
            ActiveListing.card_id == card_id,
            ActiveListing.snapshot_date >= week_ago
        ).order_by(ActiveListing.listing_price).all()
        
        if not listings:
            return None
        
        # Separate BIN and auction listings
        bin_listings = []
        auction_listings = []
        
        for l in listings:
            lp = float(l.listing_price)
            if lp <= 0:
                continue
            if is_noise_listing(l.listing_title or ''):
                continue
            item_id = l.ebay_item_id or ''
            legacy_id = item_id.split('|')[1] if '|' in item_id else item_id
            url = l.listing_url or f"https://www.ebay.com/itm/{legacy_id}"
            
            net = sell_price * (1 - self.FEE_RATE) - lp
            
            entry = {
                'price': round(lp, 2),
                'title': l.listing_title or '',
                'url': url,
                'listing_type': l.listing_type,
                'net_profit': round(net, 2),
            }
            
            if l.listing_type == 'auction':
                entry['current_bid'] = round(lp, 2)
                entry['potential_profit'] = round(net, 2)
                if net >= self.MIN_PROFIT:
                    auction_listings.append(entry)
            else:
                if net >= self.MIN_PROFIT:
                    bin_listings.append(entry)
        
        bin_listings.sort(key=lambda x: x['price'])
        auction_listings.sort(key=lambda x: x['price'])
        
        # Must have at least one profitable listing (BIN or auction)
        if not bin_listings and not auction_listings:
            return None
        
        # Build arbitrage summary from best available deal
        best_listing = (bin_listings[0] if bin_listings else auction_listings[0])
        buy_price = best_listing['price']
        fees = sell_price * self.FEE_RATE
        net_profit = best_listing['net_profit']
        roi = (net_profit / buy_price * 100) if buy_price > 0 else 0
        profit_score = min(roi * 2, 100)
        
        arbitrage = {
            'is_profitable': True,
            'buy_price': round(buy_price, 2),
            'sell_price': round(sell_price, 2),
            'fees': round(fees, 2),
            'net_profit': round(net_profit, 2),
            'roi': round(roi, 1),
            'profit_score': round(max(profit_score, 0), 1),
            'available_listings': len(bin_listings) + len(auction_listings),
            'market_source': 'sportscardspro',
            'scp_ungraded': scp_rate.get('ungraded'),
            'scp_grade_9': scp_rate.get('grade_9'),
            'scp_psa_10': scp_rate.get('psa_10'),
        }
        
        # Momentum
        momentum = self._calculate_momentum(db, card_id, recent_sales)
        
        # Score: 70% arbitrage, 30% momentum
        opportunity_score = (
            arbitrage['profit_score'] * 0.7 +
            momentum['momentum_score'] * 0.3
        )
        
        # Build eBay search URL
        search_parts = []
        if card.card_year:
            search_parts.append(str(card.card_year))
        if card.card_set:
            search_parts.append(card.card_set)
        search_parts.append(card.player_name)
        if card.card_number:
            search_parts.append(f'#{card.card_number}')
        if card.parallel and card.parallel != 'Base':
            search_parts.append(card.parallel)
        ebay_search = '+'.join(' '.join(search_parts).split())
        arbitrage['ebay_url'] = f"https://www.ebay.com/sch/i.html?_nkw={ebay_search}&LH_BIN=1"

        return {
            'card_id': card_id,
            'player_name': card.player_name,
            'card_year': card.card_year,
            'card_set': card.card_set,
            'card_number': card.card_number,
            'parallel': card.parallel or 'Base',
            'grade_company': card.grade_company,
            'grade_value': float(card.grade_value) if card.grade_value else None,
            'is_rookie': card.is_rookie,
            'sport': card.sport,
            'image_url': card.image_url,
            'market_data': market_data,
            'arbitrage': arbitrage,
            'buy_listings': bin_listings,
            'auction_listings': auction_listings,
            'momentum': momentum,
            'opportunity_score': round(opportunity_score, 1),
            'confidence': self._get_confidence_level(momentum['momentum_score'])
        }
    
    def _get_market_rate(self, db: Session, card_id: int, card: Card) -> Optional[Dict]:
        rate = db.query(MarketRate).filter(
            MarketRate.card_id == card_id
        ).order_by(MarketRate.date_recorded.desc()).first()

        if not rate:
            return None

        ungraded = float(rate.ungraded_price) if rate.ungraded_price else None
        grade_9 = float(rate.grade_9_price) if rate.grade_9_price else None
        psa_10 = float(rate.psa_10_price) if rate.psa_10_price else None

        grade_val = float(card.grade_value) if card.grade_value else None
        if card.grade_company and grade_val:
            if grade_val >= 10 and psa_10:
                sell_price = psa_10
            elif grade_val >= 9 and grade_9:
                sell_price = grade_9
            elif ungraded:
                sell_price = ungraded
            else:
                return None
        else:
            sell_price = ungraded
            if not sell_price:
                return None

        return {
            'sell_price': sell_price,
            'source': 'sportscardspro',
            'ungraded': ungraded,
            'grade_9': grade_9,
            'psa_10': psa_10,
        }

    def _calculate_market_data(self, sales: List[Sale]) -> Dict:
        prices = sorted([float(s.sale_price) for s in sales])
        avg_price = sum(prices) / len(prices)
        median_price = prices[len(prices) // 2]
        min_price = prices[0]
        max_price = prices[-1]
        
        price_range = max_price - min_price
        is_consistent = (price_range / avg_price) <= 0.50 if avg_price > 0 else False
        
        search_window_days = 30
        sales_per_day = len(sales) / search_window_days
        
        if sales_per_day >= 1:
            est_days_to_sell = 3
            flip_speed = 'QUICK FLIP'
        elif sales_per_day >= 0.5:
            est_days_to_sell = 7
            flip_speed = 'FAST'
        elif sales_per_day >= 0.2:
            est_days_to_sell = 14
            flip_speed = 'MEDIUM'
        elif sales_per_day >= 0.1:
            est_days_to_sell = 30
            flip_speed = 'SLOW'
        else:
            est_days_to_sell = 60
            flip_speed = 'SIT & WAIT'
        
        return {
            'avg_price': round(avg_price, 2),
            'median_price': round(median_price, 2),
            'min_price': round(min_price, 2),
            'max_price': round(max_price, 2),
            'price_range': round(price_range, 2),
            'is_consistent': is_consistent,
            'sales_count': len(sales),
            'avg_days_to_sell': round(est_days_to_sell, 1),
            'flip_speed': flip_speed
        }
    
    def _calculate_arbitrage(self, market_rate: float, listings: List[ActiveListing]) -> Dict:
        """Legacy method kept for compatibility"""
        if not listings:
            return {'is_profitable': False}
        
        valid_listings = [l for l in listings if float(l.listing_price) > 0]
        if not valid_listings:
            return {'is_profitable': False}
        
        cheapest = valid_listings[0]
        buy_price = float(cheapest.listing_price)
        sell_price = market_rate
        fees = sell_price * self.FEE_RATE
        net_profit = sell_price - buy_price - fees
        roi = (net_profit / buy_price * 100) if buy_price > 0 else 0
        profit_score = min(roi * 2, 100)
        
        return {
            'is_profitable': net_profit >= self.MIN_PROFIT,
            'buy_price': round(buy_price, 2),
            'sell_price': round(sell_price, 2),
            'fees': round(fees, 2),
            'net_profit': round(net_profit, 2),
            'roi': round(roi, 1),
            'profit_score': round(profit_score, 1),
            'available_listings': len(valid_listings),
        }
    
    def _calculate_momentum(self, db: Session, card_id: int, recent_sales: List[Sale]) -> Dict:
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
        
        search_window_days = 30
        sales_per_week = len(recent_sales) / (search_window_days / 7)
        
        week_ago = date.today() - timedelta(days=7)
        listings_count = db.query(ActiveListing).filter(
            ActiveListing.card_id == card_id,
            ActiveListing.snapshot_date >= week_ago
        ).count()
        
        str_rate = (len(recent_sales) / listings_count * 100) if listings_count > 0 else 100
        
        price_score = max(0, min((price_change + 20) * 1.25, 50))
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
        if momentum_score >= 70:
            return 'VERY HIGH'
        elif momentum_score >= 50:
            return 'HIGH'
        elif momentum_score >= 30:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def find_opportunities(
        self,
        db: Session,
        min_budget: Optional[float] = None,
        max_budget: Optional[float] = None,
        min_profit: Optional[float] = None,
        min_roi: Optional[float] = None,
        momentum_filter: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
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
            buy_price = opp['arbitrage']['buy_price']
            if min_budget and buy_price < min_budget:
                continue
            if max_budget and buy_price > max_budget:
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
        
        opportunities.sort(key=lambda x: x['opportunity_score'], reverse=True)
        return opportunities[:limit]
