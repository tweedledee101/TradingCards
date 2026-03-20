"""
QA Tests: API Endpoints

Tests that the API returns valid data and doesn't leak garbage to the frontend.
"""
import pytest
from unittest.mock import patch, MagicMock
from backend.services.opportunity_analyzer import OpportunityAnalyzer


class TestOpportunitiesEndpointContract:
    """The API must return data in the expected format"""

    @pytest.fixture
    def analyzer(self):
        return OpportunityAnalyzer()

    def test_opportunity_has_required_fields(self, analyzer, db, full_test_data):
        """Every opportunity must have all fields the frontend expects"""
        required_fields = [
            "card_id", "player_name", "card_year", "card_set",
            "parallel", "arbitrage", "momentum", "opportunity_score",
            "confidence", "buy_listings", "auction_listings"
        ]
        opps = analyzer.find_opportunities(db, limit=100)
        for opp in opps:
            for field in required_fields:
                assert field in opp, f"Missing field: {field}"

    def test_arbitrage_has_required_fields(self, analyzer, db, full_test_data):
        """Arbitrage section must have all pricing fields"""
        required = [
            "buy_price", "sell_price", "fees", "net_profit",
            "roi", "market_source"
        ]
        opps = analyzer.find_opportunities(db, limit=100)
        for opp in opps:
            for field in required:
                assert field in opp["arbitrage"], f"Missing arbitrage field: {field}"

    def test_momentum_has_required_fields(self, analyzer, db, full_test_data):
        """Momentum section must have all signal fields"""
        required = [
            "price_trend", "sales_per_week", "str_rate",
            "active_listings", "momentum_score"
        ]
        opps = analyzer.find_opportunities(db, limit=100)
        for opp in opps:
            for field in required:
                assert field in opp["momentum"], f"Missing momentum field: {field}"

    def test_buy_listing_has_required_fields(self, analyzer, db, full_test_data):
        """Each BIN listing must have price, title, url, net_profit"""
        opps = analyzer.find_opportunities(db, limit=100)
        for opp in opps:
            for listing in opp["buy_listings"]:
                assert "price" in listing
                assert "net_profit" in listing
                assert "url" in listing

    def test_auction_listing_has_required_fields(self, analyzer, db, full_test_data):
        """Each auction listing must have price, potential_profit"""
        opps = analyzer.find_opportunities(db, limit=100)
        for opp in opps:
            for listing in opp["auction_listings"]:
                assert "price" in listing
                assert "potential_profit" in listing
                assert "url" in listing

    def test_opportunity_score_is_number(self, analyzer, db, full_test_data):
        """Score must be a number, not None or string"""
        opps = analyzer.find_opportunities(db, limit=100)
        for opp in opps:
            assert isinstance(opp["opportunity_score"], (int, float))

    def test_roi_is_number(self, analyzer, db, full_test_data):
        """ROI must be a number"""
        opps = analyzer.find_opportunities(db, limit=100)
        for opp in opps:
            assert isinstance(opp["arbitrage"]["roi"], (int, float))

    def test_opportunities_sorted_by_score(self, analyzer, db, full_test_data):
        """Results must be sorted by opportunity_score descending"""
        opps = analyzer.find_opportunities(db, limit=100)
        if len(opps) > 1:
            for i in range(len(opps) - 1):
                assert opps[i]["opportunity_score"] >= opps[i + 1]["opportunity_score"], \
                    "Opportunities must be sorted by score descending"
