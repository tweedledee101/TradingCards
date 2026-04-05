"""
Unit tests for eBay scraper
Tests title parsing, data extraction, and API response handling
"""
import pytest
import requests
from unittest.mock import Mock, patch
from backend.scrapers.ebay_scraper import EbayScraper
from tests.fixtures.sample_data import (
    EBAY_SOLD_RESPONSE,
    EBAY_ACTIVE_RESPONSE,
    EXPECTED_PARSED_SALES,
    TITLE_PARSING_TESTS
)


@pytest.fixture
def scraper():
    """Create EbayScraper instance for testing (no real eBay credentials needed)"""
    mock_tm = Mock()
    mock_tm.get_token.return_value = 'fake-token-for-tests'
    with patch('backend.utils.token_manager.token_manager', mock_tm):
        return EbayScraper()


class TestTitleParsing:
    """Test card detail extraction from listing titles"""
    
    @pytest.mark.unit
    @pytest.mark.parametrize("test_case", TITLE_PARSING_TESTS)
    def test_extract_card_info(self, scraper, test_case):
        """Test extraction of card details from various title formats"""
        result = scraper._extract_card_info(test_case['title'])
        expected = test_case['expected']
        
        assert result['is_rookie'] == expected['is_rookie'], \
            f"Rookie detection failed for: {test_case['title']}"
        assert result['card_year'] == expected['card_year'], \
            f"Year extraction failed for: {test_case['title']}"
        assert result['graded'] == expected['graded'], \
            f"Grading detection failed for: {test_case['title']}"
        assert result['grade_company'] == expected['grade_company'], \
            f"Grade company extraction failed for: {test_case['title']}"
        assert result['grade_value'] == expected['grade_value'], \
            f"Grade value extraction failed for: {test_case['title']}"
        assert result['card_set'] == expected['card_set'], \
            f"Card set extraction failed for: {test_case['title']}"
    
    @pytest.mark.unit
    def test_rookie_detection_rc(self, scraper):
        """Test RC abbreviation is detected as rookie"""
        result = scraper._extract_card_info("2023 Player Name RC")
        assert result['is_rookie'] is True
    
    @pytest.mark.unit
    def test_rookie_detection_full_word(self, scraper):
        """Test full word 'rookie' is detected"""
        result = scraper._extract_card_info("2023 Player Name Rookie Card")
        assert result['is_rookie'] is True
    
    @pytest.mark.unit
    def test_non_rookie_card(self, scraper):
        """Test non-rookie cards are correctly identified"""
        result = scraper._extract_card_info("2023 Player Name Base Card")
        assert result['is_rookie'] is False
    
    @pytest.mark.unit
    def test_psa_grade_extraction(self, scraper):
        """Test PSA grade extraction"""
        test_cases = [
            ("Card PSA 10", 'PSA', 10.0),
            ("Card PSA10", 'PSA', 10.0),
            ("Card PSA 9", 'PSA', 9.0),
            ("Card PSA 8.5", 'PSA', 8.5),
        ]
        for title, expected_company, expected_grade in test_cases:
            result = scraper._extract_card_info(title)
            assert result['grade_company'] == expected_company
            assert result['grade_value'] == expected_grade
    
    @pytest.mark.unit
    def test_bgs_grade_extraction(self, scraper):
        """Test BGS/Beckett grade extraction"""
        test_cases = [
            ("Card BGS 9.5", 'BGS', 9.5),
            ("Card Beckett 9", 'BGS', 9.0),
        ]
        for title, expected_company, expected_grade in test_cases:
            result = scraper._extract_card_info(title)
            assert result['grade_company'] == expected_company
            assert result['grade_value'] == expected_grade
    
    @pytest.mark.unit
    def test_year_extraction(self, scraper):
        """Test year extraction from titles"""
        test_cases = [
            ("2023 Player Card", 2023),
            ("1986 Fleer Jordan", 1986),
            ("2000 Topps Chrome", 2000),
            ("Player Card No Year", None),
        ]
        for title, expected_year in test_cases:
            result = scraper._extract_card_info(title)
            assert result['card_year'] == expected_year
    
    @pytest.mark.unit
    def test_card_set_extraction(self, scraper):
        """Test card set extraction"""
        test_cases = [
            ("2023 Prizm Player RC", 'Prizm'),
            ("2023 Topps Chrome Player", 'Topps Chrome'),
            ("2023 Bowman Chrome Player", 'Bowman Chrome'),
            ("2023 Select Player", 'Select'),
            ("2023 Unknown Set Player", 'Unknown'),
        ]
        for title, expected_set in test_cases:
            result = scraper._extract_card_info(title)
            assert result['card_set'] == expected_set


class TestCardNumberFromListingText:
    """Browse API item descriptions often carry # when title/aspects do not."""

    @pytest.mark.unit
    def test_first_hashtag_card_number_plain(self, scraper):
        assert EbayScraper._first_hashtag_card_number('foo #USC35 bar') == 'USC35'
        assert EbayScraper._first_hashtag_card_number('no hash') is None

    @pytest.mark.unit
    def test_html_to_plain_strips_tags(self, scraper):
        raw = '<p>Card # <b>M1B-8</b> serial</p>'
        assert 'M1B-8' in EbayScraper._html_to_plain(raw)

    @pytest.mark.unit
    def test_item_description_plain_merges_fields(self, scraper):
        blob = EbayScraper._item_description_plain_text({
            'shortDescription': {'value': 'See scan #29 mint'},
            'description': '',
        })
        assert '#29' in blob or '29' in blob
        assert EbayScraper._first_hashtag_card_number(blob) == '29'

    @pytest.mark.unit
    def test_first_reasonable_year_in_text(self, scraper):
        assert EbayScraper._first_reasonable_year_in_text('2021 Bowman Chrome') == 2021
        assert EbayScraper._first_reasonable_year_in_text('no digits') is None


class TestAPIResponseParsing:
    """Test parsing of eBay API responses"""
    
    @pytest.mark.unit
    def test_parse_sold_listings(self, scraper):
        """Test parsing of sold listings API response"""
        results = scraper._parse_results(EBAY_SOLD_RESPONSE)
        
        assert len(results) == 3, "Should parse all 3 items"
        
        # Check first item
        first = results[0]
        expected_first = EXPECTED_PARSED_SALES[0]
        
        assert first['ebay_item_id'] == expected_first['ebay_item_id']
        assert first['price'] == expected_first['price']
        assert first['is_rookie'] == expected_first['is_rookie']
        assert first['card_year'] == expected_first['card_year']
        assert first['grade_company'] == expected_first['grade_company']
        assert first['grade_value'] == expected_first['grade_value']
    
    @pytest.mark.unit
    def test_listing_type_detection(self, scraper):
        """Test auction vs buy-it-now detection"""
        results = scraper._parse_results(EBAY_SOLD_RESPONSE)
        
        assert results[0]['listing_type'] == 'buy_it_now'
        assert results[1]['listing_type'] == 'auction'
    
    @pytest.mark.unit
    def test_empty_response(self, scraper):
        """Test handling of empty API response"""
        empty_response = {"itemSummaries": []}
        results = scraper._parse_results(empty_response)
        assert results == []
    
    @pytest.mark.unit
    def test_missing_fields(self, scraper):
        """Test handling of items missing required fields (year/set) -- skipped by parser"""
        incomplete_response = {
            "itemSummaries": [{
                "itemId": "123",
                "title": "Test Card"
                # Missing price, date, year, set -- parser skips these
            }]
        }
        results = scraper._parse_results(incomplete_response)
        assert results == []  # Skipped: no card_year or card_set extractable


class TestScraperMethods:
    """Test scraper methods with mocked API calls"""
    
    @pytest.mark.unit
    @patch('backend.scrapers.ebay_scraper.requests.get')
    def test_search_sold_listings_success(self, mock_get, scraper):
        """Test successful sold listings search"""
        mock_response = Mock()
        mock_response.json.return_value = EBAY_SOLD_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        results = scraper.search_sold_listings("Wembanyama rookie", days_back=7)
        
        assert len(results) == 3
        assert mock_get.called
        assert 'Wembanyama rookie' in str(mock_get.call_args)
    
    @pytest.mark.unit
    @patch('backend.scrapers.ebay_scraper.requests.get')
    def test_search_sold_listings_api_error(self, mock_get, scraper):
        """Test handling of API errors"""
        import requests as req
        mock_get.side_effect = req.exceptions.ConnectionError("API Error")
        
        results = scraper.search_sold_listings("test query")
        
        assert results == []  # Should return empty list on error
    
    @pytest.mark.unit
    @patch('backend.scrapers.ebay_scraper.requests.get')
    def test_get_active_listings(self, mock_get, scraper):
        """Test active listings retrieval"""
        mock_response = Mock()
        mock_response.json.return_value = EBAY_ACTIVE_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        results = scraper.get_active_listings("Wembanyama")
        
        assert len(results) == 2
        assert all('price' in item for item in results)
        assert all('listing_type' in item for item in results)
    
    @pytest.mark.unit
    @patch('backend.scrapers.ebay_scraper.requests.get')
    def test_get_rookie_cards(self, mock_get, scraper):
        """Test rookie card search for multiple players"""
        mock_response = Mock()
        mock_response.json.return_value = EBAY_SOLD_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        players = ["Wembanyama", "Henderson"]
        results = scraper.get_rookie_cards(players, 2023)
        
        # Should call API once per player
        assert mock_get.call_count == 2
        
        # Should add player_name to results
        assert all('player_name' in item for item in results)


# Minimal Browse `item_summary/search` payload for `search_auctions_ending_soon` (auction branch)
_AUCTION_ITEM = {
    "itemId": "v1|123|0",
    "title": "2023 Topps Chrome Test Player RC",
    "price": {"value": "25.00", "currency": "USD"},
    "buyingOptions": ["AUCTION"],
    "bidCount": 3,
    "itemEndDate": "2026-04-06T12:00:00.000Z",
    "shippingOptions": [{"shippingCost": {"value": "0", "currency": "USD"}}],
    "localizedAspects": [],
    "image": {"imageUrl": "https://i.ebayimg.com/images/g/xx/s-l500.jpg"},
}


class TestSearchAuctionsEndingSoon:
    """`search_auctions_ending_soon` HTTP behavior (429 retry, success path)."""

    @pytest.mark.unit
    @patch("backend.scrapers.ebay_scraper.time.sleep", return_value=None)
    @patch("backend.scrapers.ebay_scraper.requests.get")
    def test_success_200_parses_auction(self, mock_get, _sleep, scraper):
        ok = Mock()
        ok.status_code = 200
        ok.json.return_value = {"itemSummaries": [_AUCTION_ITEM], "total": 5421}
        ok.raise_for_status.return_value = None
        mock_get.return_value = ok

        meta = {}
        rows = scraper.search_auctions_ending_soon("baseball test", hours=48, meta_out=meta)

        assert len(rows) == 1
        assert meta.get("ebay_total") == 5421
        assert rows[0]["ebay_item_id"] == "v1|123|0"
        assert rows[0]["listing_type"] == "auction"
        assert rows[0]["price"] == 25.0
        mock_get.assert_called()

    @pytest.mark.unit
    @patch("backend.scrapers.ebay_scraper.time.sleep", return_value=None)
    @patch("backend.scrapers.ebay_scraper.requests.get")
    def test_429_then_200_retries(self, mock_get, _sleep, scraper):
        r429 = Mock()
        r429.status_code = 429
        r429.headers = {"Retry-After": "5"}

        r200 = Mock()
        r200.status_code = 200
        r200.json.return_value = {"itemSummaries": []}
        r200.raise_for_status.return_value = None

        mock_get.side_effect = [r429, r200]

        rows = scraper.search_auctions_ending_soon("q", hours=12)

        assert rows == []
        assert mock_get.call_count == 2

    @pytest.mark.unit
    @patch("backend.scrapers.ebay_scraper.time.sleep", return_value=None)
    @patch("backend.scrapers.ebay_scraper.requests.get")
    def test_429_exhausted_returns_empty(self, mock_get, _sleep, scraper):
        r429 = Mock()
        r429.status_code = 429
        r429.headers = {"Retry-After": "1"}
        r429.raise_for_status.side_effect = requests.exceptions.HTTPError(response=r429)

        mock_get.return_value = r429

        rows = scraper.search_auctions_ending_soon("q", hours=12)

        assert rows == []
        assert mock_get.call_count == 6


class TestDataValidation:
    """Test data validation and edge cases"""
    
    @pytest.mark.unit
    def test_price_conversion(self, scraper):
        """Test price is converted to float"""
        response = {
            "itemSummaries": [{
                "itemId": "123",
                "title": "2023 Topps Chrome Test Player RC",
                "price": {"value": "123.45", "currency": "USD"},
                "itemEndDate": "2025-02-10T15:30:00.000Z",
                "buyingOptions": ["FIXED_PRICE"]
            }]
        }
        results = scraper._parse_results(response)
        assert isinstance(results[0]['price'], float)
        assert results[0]['price'] == 123.45
    
    @pytest.mark.unit
    def test_grade_value_as_float(self, scraper):
        """Test grade values are floats"""
        result = scraper._extract_card_info("Card PSA 10")
        assert isinstance(result['grade_value'], float)
        
        result = scraper._extract_card_info("Card BGS 9.5")
        assert isinstance(result['grade_value'], float)
    
    @pytest.mark.unit
    def test_year_as_integer(self, scraper):
        """Test year is extracted as integer"""
        result = scraper._extract_card_info("2023 Player Card")
        assert isinstance(result['card_year'], int)
        assert result['card_year'] == 2023


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
