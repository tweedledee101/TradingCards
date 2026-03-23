"""
Unit tests for Trend Calculator

Tests all scoring algorithms:
- Velocity score (sales / listings)
- Momentum score (price changes)
- Social score (mentions + sentiment)
- Hotness score (weighted combination)
"""
import pytest
from backend.services.trend_calculator import TrendCalculator


@pytest.fixture
def calculator():
    """Fixture providing TrendCalculator instance"""
    return TrendCalculator()


class TestVelocityScore:
    """Test velocity score calculations"""
    
    @pytest.mark.unit
    def test_high_velocity(self, calculator):
        """More sales than listings = high velocity"""
        score = calculator.calculate_velocity_score(100, 50)
        assert score == 100.0
    
    @pytest.mark.unit
    def test_moderate_velocity(self, calculator):
        """Equal sales and listings = moderate velocity"""
        score = calculator.calculate_velocity_score(50, 100)
        assert score == 50.0
    
    @pytest.mark.unit
    def test_low_velocity(self, calculator):
        """Few sales, many listings = low velocity"""
        score = calculator.calculate_velocity_score(10, 100)
        assert score == 10.0
    
    @pytest.mark.unit
    def test_zero_listings(self, calculator):
        """Zero listings with sales = max score"""
        score = calculator.calculate_velocity_score(50, 0)
        assert score == 100.0
    
    @pytest.mark.unit
    def test_zero_sales_zero_listings(self, calculator):
        """No sales, no listings = zero score"""
        score = calculator.calculate_velocity_score(0, 0)
        assert score == 0.0


class TestMomentumScore:
    """Test momentum score calculations"""
    
    @pytest.mark.unit
    def test_strong_momentum(self, calculator):
        """40%+ price increase = high momentum"""
        score = calculator.calculate_momentum_score(140, 100)
        assert score == 100.0
    
    @pytest.mark.unit
    def test_moderate_momentum(self, calculator):
        """20% price increase = moderate momentum"""
        score = calculator.calculate_momentum_score(120, 100)
        assert score == 50.0
    
    @pytest.mark.unit
    def test_no_momentum(self, calculator):
        """No price change = zero momentum"""
        score = calculator.calculate_momentum_score(100, 100)
        assert score == 0.0
    
    @pytest.mark.unit
    def test_negative_momentum(self, calculator):
        """Price decrease = zero momentum"""
        score = calculator.calculate_momentum_score(80, 100)
        assert score == 0.0
    
    @pytest.mark.unit
    def test_with_30day_data(self, calculator):
        """Momentum with 30-day acceleration"""
        score = calculator.calculate_momentum_score(120, 100, 90)
        assert score > 0
        assert score <= 100


class TestSocialScore:
    """Test social signal score calculations"""
    
    @pytest.mark.unit
    def test_high_mentions_positive_sentiment(self, calculator):
        """High mentions + positive sentiment = high score"""
        # 100*0.6 + ((0.8+1)/2)*100*0.4 = 60 + 36 = 96
        score = calculator.calculate_social_score(100, 0.8)
        assert score == 96.0
    
    @pytest.mark.unit
    def test_low_mentions(self, calculator):
        """Low mentions = lower score"""
        # 10*0.6 + ((0.5+1)/2)*100*0.4 = 6 + 30 = 36
        score = calculator.calculate_social_score(10, 0.5)
        assert score == 36.0
    
    @pytest.mark.unit
    def test_negative_sentiment(self, calculator):
        """Negative sentiment reduces score but mentions still contribute"""
        # 100*0.6 + ((-0.5+1)/2)*100*0.4 = 60 + 10 = 70
        score = calculator.calculate_social_score(100, -0.5)
        assert score == 70.0
    
    @pytest.mark.unit
    def test_zero_mentions(self, calculator):
        """No mentions = sentiment-only score"""
        # 0*0.6 + ((0.5+1)/2)*100*0.4 = 0 + 30 = 30
        score = calculator.calculate_social_score(0, 0.5)
        assert score == 30.0


class TestHotnessScore:
    """Test overall hotness score calculations"""
    
    @pytest.mark.unit
    def test_all_high_scores(self, calculator):
        """All high component scores = high hotness"""
        score = calculator.calculate_hotness_score(100, 100, 100)
        assert score == 100.0
    
    @pytest.mark.unit
    def test_all_zero_scores(self, calculator):
        """All zero component scores = zero hotness"""
        score = calculator.calculate_hotness_score(0, 0, 0)
        assert score == 0.0
    
    @pytest.mark.unit
    def test_weighted_combination(self, calculator):
        """Hotness uses correct weights"""
        score = calculator.calculate_hotness_score(80, 60, 40)
        expected = (80 * 0.40) + (60 * 0.35) + (40 * 0.25)
        assert score == round(expected, 2)
    
    @pytest.mark.unit
    def test_no_social_data(self, calculator):
        """Hotness works without social data"""
        score = calculator.calculate_hotness_score(80, 60)
        assert score > 0
        assert score < 100


class TestAllMetrics:
    """Test calculating all metrics at once"""
    
    @pytest.mark.unit
    def test_calculate_all_metrics(self, calculator):
        """All metrics calculated correctly"""
        metrics = calculator.calculate_all_metrics(
            sales_count=50,
            active_listings=100,
            current_price=120,
            price_7d_ago=100
        )
        
        assert 'velocity_score' in metrics
        assert 'momentum_score' in metrics
        assert 'social_score' in metrics
        assert 'hotness_score' in metrics
        
        assert metrics['velocity_score'] == 50.0
        assert metrics['momentum_score'] == 50.0
        assert metrics['social_score'] == 20.0
    
    @pytest.mark.unit
    def test_with_all_data(self, calculator):
        """All metrics with complete data"""
        metrics = calculator.calculate_all_metrics(
            sales_count=80,
            active_listings=100,
            current_price=150,
            price_7d_ago=100,
            price_30d_ago=90,
            mention_count=50,
            sentiment_score=0.7
        )
        
        assert all(0 <= v <= 100 for v in metrics.values())


class TestTrendCategory:
    """Test trend categorization"""
    
    @pytest.mark.unit
    def test_fire_category(self, calculator):
        """Score 80+ = FIRE"""
        category = calculator.get_trend_category(85)
        assert "FIRE" in category
    
    @pytest.mark.unit
    def test_trending_category(self, calculator):
        """Score 60-79 = TRENDING"""
        category = calculator.get_trend_category(65)
        assert "TRENDING" in category
    
    @pytest.mark.unit
    def test_watch_category(self, calculator):
        """Score 40-59 = WATCH"""
        category = calculator.get_trend_category(45)
        assert "WATCH" in category
    
    @pytest.mark.unit
    def test_stable_category(self, calculator):
        """Score 20-39 = STABLE"""
        category = calculator.get_trend_category(25)
        assert "STABLE" in category
    
    @pytest.mark.unit
    def test_cold_category(self, calculator):
        """Score 0-19 = COLD"""
        category = calculator.get_trend_category(10)
        assert "COLD" in category


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    @pytest.mark.unit
    def test_extreme_velocity(self, calculator):
        """Very high sales/listings ratio capped at 100"""
        score = calculator.calculate_velocity_score(1000, 10)
        assert score == 100.0
    
    @pytest.mark.unit
    def test_extreme_momentum(self, calculator):
        """Very high price increase capped at 100"""
        score = calculator.calculate_momentum_score(1000, 100)
        assert score == 100.0
    
    @pytest.mark.unit
    def test_extreme_social(self, calculator):
        """Very high mentions capped properly"""
        score = calculator.calculate_social_score(1000, 1.0)
        assert score <= 100.0
    
    @pytest.mark.unit
    def test_zero_price_7d(self, calculator):
        """Zero price 7 days ago handled"""
        score = calculator.calculate_momentum_score(100, 0)
        assert score == 0.0
