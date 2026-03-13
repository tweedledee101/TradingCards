"""
Multi-Platform Sourcing Service

Aggregates buying options from multiple platforms for arbitrage opportunities.
This is how professional dealers find cards cheap and flip on eBay.
"""
from typing import Dict, List, Optional
from backend.scrapers.facebook_marketplace_scraper import FacebookMarketplaceScraper
from backend.scrapers.comc_scraper import COMCScraper
from backend.scrapers.whatnot_scraper import WhatnotScraper

class MultiPlatformSourcingService:
    """Find cards across multiple platforms for arbitrage"""
    
    def __init__(self):
        self.facebook = FacebookMarketplaceScraper()
        self.comc = COMCScraper()
        self.whatnot = WhatnotScraper()
    
    def get_sourcing_options(
        self,
        player: str,
        year: int,
        card_set: str,
        card_number: Optional[str] = None,
        parallel: Optional[str] = None,
        grade_company: Optional[str] = None,
        grade_value: Optional[float] = None,
        target_buy_price: Optional[float] = None,
        market_price: Optional[float] = None,
        sales_count_30d: Optional[int] = None,
        avg_days_to_sell: Optional[int] = None
    ) -> Dict:
        """
        Get sourcing options from all platforms with dealer decision metrics
        
        Args:
            player: Player name
            year: Card year
            card_set: Card set
            card_number: Card number (optional)
            parallel: Parallel type (optional)
            grade_company: Grading company (optional)
            grade_value: Grade value (optional)
            target_buy_price: Maximum buy price (optional)
            market_price: eBay market rate (optional)
            sales_count_30d: Sales in last 30 days (optional)
            avg_days_to_sell: Average days to sell (optional)
            
        Returns:
            Dict with platform URLs and dealer decision metrics
        """
        # Get platform URLs
        urls = {
            "ebay": self._get_ebay_url(player, year, card_set, card_number, parallel, grade_company, grade_value, target_buy_price),
            "facebook": self.facebook.get_search_url(player, year, card_set, target_buy_price),
            "comc": self.comc.get_search_url(player, year, card_set),
            "whatnot": self.whatnot.get_search_url(player, year, card_set),
            "mercari": self._get_mercari_url(player, year, card_set),
        }
        
        # Calculate dealer decision metrics
        decision_metrics = self._calculate_dealer_metrics(
            market_price=market_price,
            target_buy_price=target_buy_price,
            sales_count_30d=sales_count_30d,
            avg_days_to_sell=avg_days_to_sell
        )
        
        return {
            "urls": urls,
            "decision_metrics": decision_metrics
        }
    
    def _get_ebay_url(
        self,
        player: str,
        year: int,
        card_set: str,
        card_number: Optional[str],
        parallel: Optional[str],
        grade_company: Optional[str],
        grade_value: Optional[float],
        max_price: Optional[float]
    ) -> str:
        """Generate eBay search URL with exact card details"""
        query = f"{player} {year} {card_set}"
        if card_number:
            query += f" #{card_number}"
        if parallel and parallel != "Base":
            query += f" {parallel}"
        if grade_company and grade_value:
            query += f" {grade_company} {grade_value}"
        else:
            query += " raw"
        
        url = f"https://www.ebay.com/sch/i.html?_nkw={query.replace(' ', '+')}"
        
        if max_price:
            min_price = int(max_price * 0.8)
            max_price_int = int(max_price * 1.2)
            url += f"&_udlo={min_price}&_udhi={max_price_int}"
        
        url += "&LH_BIN=1&_sop=15"  # Buy It Now, lowest price first
        return url
    
    def _get_mercari_url(self, player: str, year: int, card_set: str) -> str:
        """Generate Mercari search URL"""
        query = f"{player} {year} {card_set}"
        return f"https://www.mercari.com/search/?keyword={query.replace(' ', '%20')}"
    
    def calculate_arbitrage_potential(
        self,
        market_price: float,
        platform_prices: Dict[str, float]
    ) -> List[Dict]:
        """
        Calculate arbitrage potential for each platform
        
        Args:
            market_price: eBay market rate
            platform_prices: Dict of platform -> price
            
        Returns:
            List of arbitrage opportunities sorted by profit potential
        """
        EBAY_FEES = 0.1315  # 13.15%
        SHIPPING = 5.00
        
        opportunities = []
        
        for platform, buy_price in platform_prices.items():
            if buy_price and buy_price < market_price:
                gross_profit = market_price - buy_price
                net_profit = market_price - buy_price - (market_price * EBAY_FEES) - SHIPPING
                roi = (net_profit / buy_price) * 100
                
                opportunities.append({
                    "platform": platform,
                    "buy_price": buy_price,
                    "sell_price": market_price,
                    "gross_profit": gross_profit,
                    "net_profit": net_profit,
                    "roi": roi,
                    "margin": (net_profit / market_price) * 100
                })
        
        # Sort by ROI descending
        opportunities.sort(key=lambda x: x["roi"], reverse=True)
        return opportunities
    
    def _calculate_dealer_metrics(
        self,
        market_price: Optional[float],
        target_buy_price: Optional[float],
        sales_count_30d: Optional[int],
        avg_days_to_sell: Optional[int]
    ) -> Dict:
        """Calculate professional dealer decision metrics"""
        if not market_price or not target_buy_price:
            return {"available": False}
        
        EBAY_FEES = 0.1315
        SHIPPING = 5.00
        MIN_SALES_LIQUID = 3
        MIN_MARGIN_PCT = 30
        PRICE_DROP_BUFFER = 0.15
        
        # Net profit calculation
        net_profit = market_price - target_buy_price - (market_price * EBAY_FEES) - SHIPPING
        margin_pct = (net_profit / target_buy_price) * 100 if target_buy_price > 0 else 0
        
        # Liquidity check
        is_liquid = sales_count_30d >= MIN_SALES_LIQUID if sales_count_30d else None
        
        # Risk buffer (survives 15% price drop?)
        price_after_drop = market_price * (1 - PRICE_DROP_BUFFER)
        net_after_drop = price_after_drop - target_buy_price - (price_after_drop * EBAY_FEES) - SHIPPING
        survives_drop = net_after_drop > 0
        
        # Turnaround category
        if avg_days_to_sell:
            if avg_days_to_sell <= 14:
                turnaround = "fast_flip"  # 1-14 days
            elif avg_days_to_sell <= 60:
                turnaround = "standard"    # 2-8 weeks
            else:
                turnaround = "long_hold"   # 3+ months
        else:
            turnaround = "unknown"
        
        # Deal quality score (0-100)
        score = 0
        if is_liquid:
            score += 30  # Liquidity
        if margin_pct >= MIN_MARGIN_PCT:
            score += 30  # Margin
        if survives_drop:
            score += 20  # Risk buffer
        if turnaround == "fast_flip":
            score += 20  # Fast turnaround
        elif turnaround == "standard":
            score += 10
        
        # Recommendation
        if score >= 80:
            recommendation = "BUY"  # Strong deal
        elif score >= 60:
            recommendation = "CONSIDER"  # Decent deal
        elif score >= 40:
            recommendation = "MARGINAL"  # Risky
        else:
            recommendation = "PASS"  # Skip
        
        return {
            "available": True,
            "net_profit": round(net_profit, 2),
            "margin_pct": round(margin_pct, 1),
            "is_liquid": is_liquid,
            "sales_30d": sales_count_30d,
            "survives_15pct_drop": survives_drop,
            "turnaround": turnaround,
            "avg_days_to_sell": avg_days_to_sell,
            "deal_quality_score": score,
            "recommendation": recommendation
        }
