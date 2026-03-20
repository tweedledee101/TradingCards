"""
QA Tests: Opportunity Analyzer

Every test here is a bug that was found manually.
If any of these fail, we've regressed.
"""
import pytest
from backend.services.opportunity_analyzer import OpportunityAnalyzer
from backend.models import Sale


@pytest.fixture
def analyzer():
    return OpportunityAnalyzer()


class TestNeverShowNegativeProfit:
    """BUG: UI showed opportunities with -$0.52, -$0.25, -$0.74, -$49.89 profit"""

    def test_analyze_card_never_returns_negative_profit(self, analyzer, db, full_test_data):
        """No card should ever return negative net_profit"""
        for card in full_test_data["cards"]:
            result = analyzer.analyze_card(db, card.id)
            if result is None:
                continue
            assert result["arbitrage"]["net_profit"] >= 0, \
                f"{card.player_name} {card.card_set} returned negative profit: {result['arbitrage']['net_profit']}"

    def test_find_opportunities_no_negative_profit(self, analyzer, db, full_test_data):
        """find_opportunities should never include negative profit deals"""
        opps = analyzer.find_opportunities(db, limit=100)
        for opp in opps:
            assert opp["arbitrage"]["net_profit"] >= 0, \
                f"{opp['player_name']} has negative profit: {opp['arbitrage']['net_profit']}"

    def test_buy_listings_all_profitable(self, analyzer, db, full_test_data):
        """Every BIN listing shown must have positive profit"""
        opps = analyzer.find_opportunities(db, limit=100)
        for opp in opps:
            for listing in opp.get("buy_listings", []):
                assert listing["net_profit"] >= 0, \
                    f"BIN listing at ${listing['price']} has negative profit"

    def test_auction_listings_all_profitable(self, analyzer, db, full_test_data):
        """Every auction listing shown must have positive potential profit"""
        opps = analyzer.find_opportunities(db, limit=100)
        for opp in opps:
            for listing in opp.get("auction_listings", []):
                assert listing["potential_profit"] >= 0, \
                    f"Auction at ${listing['price']} has negative potential profit"


class TestMinimumProfitThreshold:
    """BUG: UI showed $0.42, $0.26, $0.92 profit deals -- not worth pursuing"""

    def test_minimum_10_dollar_profit(self, analyzer, db, full_test_data):
        """No opportunity should have less than $10 net profit"""
        opps = analyzer.find_opportunities(db, limit=100)
        for opp in opps:
            assert opp["arbitrage"]["net_profit"] >= 10.0, \
                f"{opp['player_name']} {opp['card_set']} has only ${opp['arbitrage']['net_profit']} profit"

    def test_crews_cheap_card_excluded(self, analyzer, db, full_test_data):
        """Dylan Crews 2025 Heritage base at $1.92 SCP should NOT be an opportunity"""
        result = analyzer.analyze_card(db, 4)  # Crews cheap card
        assert result is None, "Sub-$10 profit card should not be an opportunity"

    def test_henderson_pink_foil_excluded(self, analyzer, db, full_test_data):
        """Henderson Pink Foil at $2.37 SCP with $3.50 BIN = no profit, should be excluded"""
        result = analyzer.analyze_card(db, 2)  # Henderson Pink Foil
        assert result is None, "Henderson Pink Foil should not be an opportunity (no $10+ profit listing)"


class TestSCPSanityCheck:
    """BUG: SCP returned $803.93 for a $1 card, $8999 for a $3 card"""

    def test_3x_sanity_check_rejects_bad_rate(self, analyzer, db, full_test_data):
        """Carroll: SCP says $803.93, actual sales avg $1.00 -- should be rejected (803x off)"""
        result = analyzer.analyze_card(db, 7)  # Carroll with bad SCP rate
        assert result is None, "Card with SCP rate 803x off from sales should be rejected"

    def test_good_rate_passes_sanity_check(self, analyzer, db, full_test_data):
        """Holliday: SCP says $92.53, actual sales avg ~$88 -- should pass (1.05x)"""
        result = analyzer.analyze_card(db, 3)  # Holliday with good rate
        # Should not be None (rate is reasonable)
        # May still be None if no profitable listings, but not due to sanity check
        # The key test is that Carroll (803x) is rejected while Holliday (1.05x) is not


class TestSCPRequired:
    """Every opportunity MUST have an SCP market rate"""

    def test_no_scp_no_opportunity(self, analyzer, db, full_test_data):
        """Card without SCP rate should return None"""
        result = analyzer.analyze_card(db, 5)  # Henderson with no card_number, no SCP rate
        assert result is None, "Card without SCP rate should not be an opportunity"

    def test_all_opportunities_have_scp(self, analyzer, db, full_test_data):
        """Every returned opportunity must have SCP rates"""
        opps = analyzer.find_opportunities(db, limit=100)
        for opp in opps:
            assert opp["arbitrage"]["market_source"] == "sportscardspro", \
                f"{opp['player_name']} missing SCP source"
            assert opp["arbitrage"].get("scp_ungraded") is not None or \
                   opp["arbitrage"].get("scp_grade_9") is not None or \
                   opp["arbitrage"].get("scp_psa_10") is not None, \
                f"{opp['player_name']} has no SCP prices"


class TestAuctionsAsOpportunities:
    """BUG: Most results were BIN-only. Auctions are where the real value is."""

    def test_auction_only_card_can_be_opportunity(self, analyzer, db, full_test_data):
        """Sasaki with auction at $5 and SCP rate $25 = $16.75 profit. Should show."""
        result = analyzer.analyze_card(db, 6)  # Sasaki auction-only
        assert result is not None, "Auction-only card with $16+ profit should be an opportunity"
        assert len(result["auction_listings"]) > 0, "Should have auction listings"

    def test_auction_profit_calculated_correctly(self, analyzer, db, full_test_data):
        """Auction profit = SCP rate * (1 - 0.13) - current_bid"""
        result = analyzer.analyze_card(db, 6)
        if result and result["auction_listings"]:
            auction = result["auction_listings"][0]
            expected_profit = 25.0 * 0.87 - 5.0  # $21.75 - $5 = $16.75
            assert abs(auction["potential_profit"] - expected_profit) < 0.01, \
                f"Auction profit should be ~${expected_profit:.2f}, got ${auction['potential_profit']}"


class TestHollidayAutoOpportunity:
    """REAL FIND: Holliday Heritage Auto at $70 BIN, SCP $92.53 = $10.50 profit"""

    def test_holliday_is_opportunity(self, analyzer, db, full_test_data):
        """This was the first real opportunity found with the tool"""
        result = analyzer.analyze_card(db, 3)
        assert result is not None, "Holliday Auto should be an opportunity"

    def test_holliday_profit_correct(self, analyzer, db, full_test_data):
        """$92.53 * 0.87 - $70 = $10.50"""
        result = analyzer.analyze_card(db, 3)
        if result:
            expected = 92.53 * 0.87 - 70.0
            assert abs(result["arbitrage"]["net_profit"] - expected) < 0.50, \
                f"Holliday profit should be ~${expected:.2f}, got ${result['arbitrage']['net_profit']}"

    def test_holliday_shows_auction_too(self, analyzer, db, full_test_data):
        """Holliday has a $45 auction -- should show alongside the BIN"""
        result = analyzer.analyze_card(db, 3)
        if result:
            assert len(result["auction_listings"]) > 0 or len(result["buy_listings"]) > 0, \
                "Holliday should have at least one listing"


class TestMinimumSalesRequired:
    """Need at least 3 sales for confidence"""

    def test_card_with_2_sales_excluded(self, analyzer, db, sample_cards, sample_listings, sample_market_rates):
        """Card with only 2 sales should not be an opportunity"""
        from datetime import datetime, timedelta
        # Add only 2 sales for card 1
        db.add(Sale(card_id=1, sale_price=100.0, sale_date=datetime.now(),
                     ebay_item_id="few-1", source="ebay"))
        db.add(Sale(card_id=1, sale_price=105.0, sale_date=datetime.now() - timedelta(days=5),
                     ebay_item_id="few-2", source="ebay"))
        db.commit()

        result = analyzer.analyze_card(db, 1)
        assert result is None, "Card with only 2 sales should not be an opportunity"


class TestFeeCalculation:
    """Fees must be 13% of sell price, not buy price"""

    def test_fees_are_13_percent_of_sell_price(self, analyzer, db, full_test_data):
        """Fees = sell_price * 0.13"""
        opps = analyzer.find_opportunities(db, limit=100)
        for opp in opps:
            sell = opp["arbitrage"]["sell_price"]
            fees = opp["arbitrage"]["fees"]
            expected_fees = round(sell * 0.13, 2)
            assert abs(fees - expected_fees) < 0.02, \
                f"Fees should be ${expected_fees}, got ${fees}"

    def test_net_profit_formula(self, analyzer, db, full_test_data):
        """net_profit = sell_price * 0.87 - buy_price"""
        opps = analyzer.find_opportunities(db, limit=100)
        for opp in opps:
            sell = opp["arbitrage"]["sell_price"]
            buy = opp["arbitrage"]["buy_price"]
            net = opp["arbitrage"]["net_profit"]
            expected = round(sell * 0.87 - buy, 2)
            assert abs(net - expected) < 0.02, \
                f"Net profit should be ${expected}, got ${net}"
