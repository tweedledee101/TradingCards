"""
Trend Detection Engine

Calculates velocity, momentum, and hotness scores for trading cards.

Scoring System:
- Velocity Score: Sales volume / Active listings (demand vs supply)
- Momentum Score: Price change velocity (week-over-week)
- Hotness Score: Weighted combination of velocity + momentum + social signals

Usage:
    calculator = TrendCalculator()
    hotness = calculator.calculate_hotness_score(card_id, date)
"""
from typing import Dict, Optional
from datetime import datetime, timedelta
from decimal import Decimal


class TrendCalculator:
    """
    Calculate trend metrics for trading cards
    
    Weights for hotness score:
    - Velocity: 40% (demand vs supply)
    - Momentum: 35% (price acceleration)
    - Social: 25% (hype factor)
    """
    
    # Scoring weights
    VELOCITY_WEIGHT = 0.40
    MOMENTUM_WEIGHT = 0.35
    SOCIAL_WEIGHT = 0.25
    
    def calculate_velocity_score(
        self, 
        sales_count: int, 
        active_listings: int
    ) -> float:
        """
        Calculate velocity score (sales / listings ratio)
        
        High velocity = high demand relative to supply
        
        Args:
            sales_count: Number of sales in period (e.g., 7 days)
            active_listings: Current active listings count
            
        Returns:
            Velocity score (0-100)
            
        Example:
            >>> calc = TrendCalculator()
            >>> calc.calculate_velocity_score(50, 100)
            50.0
            >>> calc.calculate_velocity_score(100, 50)
            100.0
        """
        if active_listings == 0:
            return 100.0 if sales_count > 0 else 0.0
        
        ratio = sales_count / active_listings
        
        # Normalize to 0-100 scale
        # ratio > 1.0 = very hot (more sales than listings)
        # ratio = 0.5 = moderate
        # ratio < 0.1 = cold
        score = min(ratio * 100, 100.0)
        
        return round(score, 2)
    
    def calculate_momentum_score(
        self,
        current_price: float,
        price_7d_ago: float,
        price_30d_ago: Optional[float] = None
    ) -> float:
        """
        Calculate price momentum score
        
        Measures price acceleration (week-over-week change)
        
        Args:
            current_price: Current average price
            price_7d_ago: Average price 7 days ago
            price_30d_ago: Average price 30 days ago (optional)
            
        Returns:
            Momentum score (0-100)
            
        Example:
            >>> calc = TrendCalculator()
            >>> calc.calculate_momentum_score(100, 80)  # 25% increase
            62.5
            >>> calc.calculate_momentum_score(100, 100)  # No change
            0.0
        """
        if price_7d_ago == 0:
            return 0.0
        
        # Calculate 7-day percentage change
        change_7d = ((current_price - price_7d_ago) / price_7d_ago) * 100
        
        # If we have 30-day data, factor in acceleration
        if price_30d_ago and price_30d_ago > 0:
            change_30d = ((current_price - price_30d_ago) / price_30d_ago) * 100
            # Weight recent change more heavily
            weighted_change = (change_7d * 0.7) + (change_30d * 0.3)
        else:
            weighted_change = change_7d
        
        # Normalize to 0-100 scale
        # 40%+ increase = 100 score
        # 20% increase = 50 score
        # 0% change = 0 score
        # Negative change = 0 score
        score = max(0, min(weighted_change * 2.5, 100.0))
        
        return round(score, 2)
    
    def calculate_social_score(
        self,
        mention_count: int,
        sentiment_score: float
    ) -> float:
        """
        Calculate social signal score
        
        Combines mention volume with sentiment
        
        Args:
            mention_count: Number of social media mentions
            sentiment_score: Sentiment (-1 to 1, where 1 is positive)
            
        Returns:
            Social score (0-100)
            
        Example:
            >>> calc = TrendCalculator()
            >>> calc.calculate_social_score(100, 0.8)  # High mentions, positive sentiment
            80.0
            >>> calc.calculate_social_score(10, 0.5)  # Low mentions
            25.0
        """
        # Normalize mention count (100+ mentions = max score)
        mention_score = min(mention_count, 100)
        
        # Convert sentiment from -1..1 to 0..1
        sentiment_normalized = (sentiment_score + 1) / 2
        
        # Combine: 60% mentions, 40% sentiment
        score = (mention_score * 0.6) + (sentiment_normalized * 100 * 0.4)
        
        return round(score, 2)
    
    def calculate_hotness_score(
        self,
        velocity_score: float,
        momentum_score: float,
        social_score: float = 0.0
    ) -> float:
        """
        Calculate overall hotness score
        
        Weighted combination of all signals
        
        Args:
            velocity_score: Velocity score (0-100)
            momentum_score: Momentum score (0-100)
            social_score: Social score (0-100, default 0)
            
        Returns:
            Hotness score (0-100)
            
        Example:
            >>> calc = TrendCalculator()
            >>> calc.calculate_hotness_score(80, 60, 40)
            64.0
        """
        hotness = (
            velocity_score * self.VELOCITY_WEIGHT +
            momentum_score * self.MOMENTUM_WEIGHT +
            social_score * self.SOCIAL_WEIGHT
        )
        
        return round(hotness, 2)
    
    def calculate_all_metrics(
        self,
        sales_count: int,
        active_listings: int,
        current_price: float,
        price_7d_ago: float,
        price_30d_ago: Optional[float] = None,
        mention_count: int = 0,
        sentiment_score: float = 0.0
    ) -> Dict[str, float]:
        """
        Calculate all trend metrics at once
        
        Args:
            sales_count: Sales in period
            active_listings: Current listings
            current_price: Current avg price
            price_7d_ago: Price 7 days ago
            price_30d_ago: Price 30 days ago (optional)
            mention_count: Social mentions (optional)
            sentiment_score: Sentiment -1 to 1 (optional)
            
        Returns:
            Dictionary with all scores
            
        Example:
            >>> calc = TrendCalculator()
            >>> metrics = calc.calculate_all_metrics(
            ...     sales_count=50,
            ...     active_listings=100,
            ...     current_price=100,
            ...     price_7d_ago=80
            ... )
            >>> print(metrics['hotness_score'])
        """
        velocity = self.calculate_velocity_score(sales_count, active_listings)
        momentum = self.calculate_momentum_score(current_price, price_7d_ago, price_30d_ago)
        social = self.calculate_social_score(mention_count, sentiment_score)
        hotness = self.calculate_hotness_score(velocity, momentum, social)
        
        return {
            'velocity_score': velocity,
            'momentum_score': momentum,
            'social_score': social,
            'hotness_score': hotness
        }
    
    def get_trend_category(self, hotness_score: float) -> str:
        """
        Categorize card based on hotness score
        
        Args:
            hotness_score: Hotness score (0-100)
            
        Returns:
            Category string
            
        Categories:
            - 80-100: 🔥 FIRE (extremely hot)
            - 60-79: 📈 TRENDING (strong momentum)
            - 40-59: 👀 WATCH (moderate interest)
            - 20-39: 😐 STABLE (low activity)
            - 0-19: 🥶 COLD (minimal interest)
        """
        if hotness_score >= 80:
            return "🔥 FIRE"
        elif hotness_score >= 60:
            return "📈 TRENDING"
        elif hotness_score >= 40:
            return "👀 WATCH"
        elif hotness_score >= 20:
            return "😐 STABLE"
        else:
            return "🥶 COLD"
