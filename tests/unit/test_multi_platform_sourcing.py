"""
Tests for Multi-Platform Sourcing Service

Tests all dealer workflow features:
- Facebook Marketplace URL generation
- COMC search URLs
- Whatnot search URLs
- Arbitrage calculation
- Multi-platform aggregation
"""
import pytest
from backend.services.multi_platform_sourcing import MultiPlatformSourcingService
from backend.scrapers.facebook_marketplace_scraper import FacebookMarketplaceScraper
from backend.scrapers.comc_scraper import COMCScraper
from backend.scrapers.whatnot_scraper import WhatnotScraper

def test_facebook_marketplace_url_generation():
    """Test Facebook Marketplace search URL generation"""
    scraper = FacebookMarketplaceScraper()
    
    url = scraper.get_search_url("Victor Wembanyama", 2023, "Prizm", max_price=100)
    
    assert "facebook.com/marketplace/search" in url
    assert "Victor%20Wembanyama" in url or "Victor+Wembanyama" in url
    assert "2023" in url
    assert "Prizm" in url
    assert "maxPrice=100" in url

def test_comc_url_generation():
    """Test COMC search URL generation"""
    scraper = COMCScraper()
    
    url = scraper.get_search_url("Anthony Edwards", 2020, "Prizm")
    
    assert "comc.com/Cards" in url
    assert "Anthony" in url
    assert "Edwards" in url
    assert "2020" in url
    assert "Prizm" in url

def test_whatnot_url_generation():
    """Test Whatnot search URL generation"""
    scraper = WhatnotScraper()
    
    url = scraper.get_search_url("Caitlin Clark", 2024, "Prizm")
    
    assert "whatnot.com/search" in url
    assert "Caitlin" in url
    assert "Clark" in url
    assert "2024" in url

def test_multi_platform_sourcing_options():
    """Test getting sourcing options from all platforms"""
    service = MultiPlatformSourcingService()
    
    options = service.get_sourcing_options(
        player="Paul Skenes",
        year=2024,
        card_set="Bowman Chrome",
        card_number="150",
        parallel="Silver",
        grade_company="PSA",
        grade_value=10,
        target_buy_price=50.0
    )
    
    # Returns nested structure with urls and decision_metrics
    urls = options["urls"]
    assert "ebay" in urls
    assert "facebook" in urls
    assert "comc" in urls
    assert "whatnot" in urls
    assert "mercari" in urls
    
    # eBay URL should include all details
    ebay_url = urls["ebay"]
    assert "Paul" in ebay_url
    assert "Skenes" in ebay_url
    assert "2024" in ebay_url
    assert "150" in ebay_url or "%23150" in ebay_url
    assert "Silver" in ebay_url
    assert "PSA" in ebay_url
    assert "10" in ebay_url

def test_arbitrage_calculation():
    """Test arbitrage potential calculation"""
    service = MultiPlatformSourcingService()
    
    market_price = 100.0
    platform_prices = {
        "facebook": 60.0,  # 40% below market
        "comc": 75.0,      # 25% below market
        "whatnot": 85.0,   # 15% below market
        "mercari": 110.0   # Above market - skip
    }
    
    opportunities = service.calculate_arbitrage_potential(market_price, platform_prices)
    
    # Should have 3 opportunities (not mercari)
    assert len(opportunities) == 3
    
    # Should be sorted by ROI descending
    assert opportunities[0]["platform"] == "facebook"  # Best ROI
    assert opportunities[0]["buy_price"] == 60.0
    assert opportunities[0]["sell_price"] == 100.0
    
    # Check profit calculations
    fb_opp = opportunities[0]
    assert fb_opp["gross_profit"] == 40.0
    assert fb_opp["net_profit"] > 0  # After fees
    assert fb_opp["roi"] > 0
    
    # Net profit should account for eBay fees (13.15%) and shipping ($5)
    expected_net = 100.0 - 60.0 - (100.0 * 0.1315) - 5.0
    assert abs(fb_opp["net_profit"] - expected_net) < 0.01

def test_ebay_url_with_raw_card():
    """Test eBay URL generation for raw (ungraded) cards"""
    service = MultiPlatformSourcingService()
    
    url = service._get_ebay_url(
        player="Caleb Williams",
        year=2024,
        card_set="Prizm",
        card_number="301",
        parallel="Base",
        grade_company=None,
        grade_value=None,
        max_price=50.0
    )
    
    assert "Caleb" in url
    assert "Williams" in url
    assert "2024" in url
    assert "Prizm" in url
    assert "301" in url or "%23301" in url
    assert "raw" in url  # Should add "raw" when no grade
    assert "_udlo=" in url  # Min price filter
    assert "_udhi=" in url  # Max price filter

def test_ebay_url_with_graded_card():
    """Test eBay URL generation for graded cards"""
    service = MultiPlatformSourcingService()
    
    url = service._get_ebay_url(
        player="Anthony Edwards",
        year=2020,
        card_set="Prizm",
        card_number="258",
        parallel="Silver",
        grade_company="PSA",
        grade_value=10,
        max_price=100.0
    )
    
    assert "PSA" in url
    assert "10" in url
    assert "raw" not in url  # Should NOT add "raw" when graded

def test_mercari_url_generation():
    """Test Mercari URL generation"""
    service = MultiPlatformSourcingService()
    
    url = service._get_mercari_url("Elly De La Cruz", 2023, "Topps Chrome")
    
    assert "mercari.com/search" in url
    assert "Elly" in url
    assert "Cruz" in url
    assert "2023" in url
    assert "Topps" in url

def test_sourcing_options_without_optional_fields():
    """Test sourcing options with minimal card info"""
    service = MultiPlatformSourcingService()
    
    options = service.get_sourcing_options(
        player="Brock Purdy",
        year=2022,
        card_set="Prizm"
    )
    
    # Returns nested structure
    urls = options["urls"]
    assert len(urls) == 5
    assert all(isinstance(url, str) for url in urls.values())

def test_arbitrage_with_no_opportunities():
    """Test arbitrage calculation when all prices are above market"""
    service = MultiPlatformSourcingService()
    
    market_price = 50.0
    platform_prices = {
        "facebook": 60.0,
        "comc": 55.0,
        "whatnot": 65.0
    }
    
    opportunities = service.calculate_arbitrage_potential(market_price, platform_prices)
    
    # Should return empty list (no profitable opportunities)
    assert len(opportunities) == 0

def test_roi_calculation_accuracy():
    """Test ROI calculation matches dealer expectations"""
    service = MultiPlatformSourcingService()
    
    # Dealer buys at $60, sells at $100
    market_price = 100.0
    platform_prices = {"facebook": 60.0}
    
    opportunities = service.calculate_arbitrage_potential(market_price, platform_prices)
    
    opp = opportunities[0]
    
    # Net profit = 100 - 60 - (100 * 0.1315) - 5 = 21.85
    # ROI = (21.85 / 60) * 100 = 36.4%
    assert abs(opp["net_profit"] - 21.85) < 0.01
    assert abs(opp["roi"] - 36.4) < 0.5

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
