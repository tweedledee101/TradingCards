"""
Unit tests for eBay scraper
Tests title parsing, data extraction, and API response handling
"""
import pytest
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
    """Create EbayScraper instance for testing"""
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
            ("2023 Unknown Set Player", None),
        ]
        for title, expected_set in test_cases:
            result = scraper._extract_card_info(title)
            assert result['card_set'] == expected_set


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
        """Test handling of missing fields in API response"""
        incomplete_response = {
            "itemSummaries": [{
                "itemId": "123",
                "title": "Test Card"
                # Missing price, date, etc.
            }]
        }
        results = scraper._parse_results(incomplete_response)
        assert len(results) == 1
        assert results[0]['price'] == 0.0  # Default value


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
        mock_get.side_effect = Exception("API Error")
        
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


class TestDataValidation:
    """Test data validation and edge cases"""
    
    @pytest.mark.unit
    def test_price_conversion(self, scraper):
        """Test price is converted to float"""
        response = {
            "itemSummaries": [{
                "itemId": "123",
                "title": "Test",
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
