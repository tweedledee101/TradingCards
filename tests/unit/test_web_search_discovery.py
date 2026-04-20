"""
Tests for Web Search Discovery adapter.
Mocked -- no real network calls.
"""
import pytest
from unittest.mock import patch, MagicMock
from backend.services.web_search_discovery import WebSearchDiscovery


@pytest.fixture
def discovery():
    return WebSearchDiscovery(delay=0)


def _fake_results(urls):
    """Build fake ddgs results from URL list."""
    return [{"href": u, "title": f"Title for {u}", "body": "snippet"} for u in urls]


class TestItemIdExtraction:
    def test_extracts_item_ids_from_itm_urls(self, discovery):
        results = _fake_results([
            "https://www.ebay.com/itm/123456789",
            "https://www.ebay.com/itm/987654321",
        ])
        items = discovery._extract_item_ids(results)
        assert len(items) == 2
        assert items[0]["item_id"] == "123456789"
        assert items[1]["item_id"] == "987654321"

    def test_deduplicates_item_ids(self, discovery):
        results = _fake_results([
            "https://www.ebay.com/itm/123456789",
            "https://www.ebay.com/itm/123456789",
            "https://www.ebay.com/itm/111111111",
        ])
        items = discovery._extract_item_ids(results)
        assert len(items) == 2

    def test_ignores_non_itm_ebay_urls(self, discovery):
        results = _fake_results([
            "https://www.ebay.com/b/Some-Category/212/bn_123",
            "https://www.ebay.com/p/12345",
            "https://www.ebay.com/itm/999999999",
        ])
        items = discovery._extract_item_ids(results)
        assert len(items) == 1
        assert items[0]["item_id"] == "999999999"

    def test_ignores_non_ebay_urls(self, discovery):
        results = _fake_results([
            "https://www.mercari.com/us/item/123",
            "https://www.comc.com/Cards/Baseball/2024/1",
        ])
        items = discovery._extract_item_ids(results)
        assert len(items) == 0

    def test_preserves_title_and_snippet(self, discovery):
        results = [{"href": "https://www.ebay.com/itm/555", "title": "Card Title", "body": "Card snippet"}]
        items = discovery._extract_item_ids(results)
        assert items[0]["title"] == "Card Title"
        assert items[0]["snippet"] == "Card snippet"


class TestQueryBuilding:
    @patch("backend.services.web_search_discovery.DDGS")
    def test_bin_query_includes_site_prefix(self, mock_ddgs_cls, discovery):
        mock_ctx = MagicMock()
        mock_ctx.text.return_value = []
        mock_ddgs_cls.return_value.__enter__ = lambda s: mock_ctx
        mock_ddgs_cls.return_value.__exit__ = lambda s, *a: None

        discovery.search_ebay_listings(player="mike trout", year=2011, card_set="topps update", card_number="US175")

        call_args = mock_ctx.text.call_args
        query = call_args[0][0]
        assert query.startswith("site:ebay.com/itm")
        assert "mike trout" in query
        assert "2011" in query
        assert "topps update" in query
        assert "#US175" in query

    @patch("backend.services.web_search_discovery.DDGS")
    def test_skips_base_parallel(self, mock_ddgs_cls, discovery):
        mock_ctx = MagicMock()
        mock_ctx.text.return_value = []
        mock_ddgs_cls.return_value.__enter__ = lambda s: mock_ctx
        mock_ddgs_cls.return_value.__exit__ = lambda s, *a: None

        discovery.search_ebay_listings(player="test", parallel="Base")

        query = mock_ctx.text.call_args[0][0]
        assert "Base" not in query

    @patch("backend.services.web_search_discovery.DDGS")
    def test_includes_non_base_parallel(self, mock_ddgs_cls, discovery):
        mock_ctx = MagicMock()
        mock_ctx.text.return_value = []
        mock_ddgs_cls.return_value.__enter__ = lambda s: mock_ctx
        mock_ddgs_cls.return_value.__exit__ = lambda s, *a: None

        discovery.search_ebay_listings(player="test", parallel="Gold Refractor")

        query = mock_ctx.text.call_args[0][0]
        assert "Gold Refractor" in query

    @patch("backend.services.web_search_discovery.DDGS")
    def test_auction_query_adds_site_prefix(self, mock_ddgs_cls, discovery):
        mock_ctx = MagicMock()
        mock_ctx.text.return_value = []
        mock_ddgs_cls.return_value.__enter__ = lambda s: mock_ctx
        mock_ddgs_cls.return_value.__exit__ = lambda s, *a: None

        discovery.search_ebay_auctions("2024 topps chrome auto")

        query = mock_ctx.text.call_args[0][0]
        assert query == "site:ebay.com/itm 2024 topps chrome auto"


class TestNoResultsHandling:
    @patch("backend.services.web_search_discovery.DDGS")
    def test_returns_empty_on_no_results_exception(self, mock_ddgs_cls, discovery):
        mock_ctx = MagicMock()
        mock_ctx.text.side_effect = Exception("No results found.")
        mock_ddgs_cls.return_value.__enter__ = lambda s: mock_ctx
        mock_ddgs_cls.return_value.__exit__ = lambda s, *a: None

        result = discovery.search_ebay_listings(player="nobody")
        assert result == []

    @patch("backend.services.web_search_discovery.DDGS")
    def test_raises_on_other_exceptions(self, mock_ddgs_cls, discovery):
        mock_ctx = MagicMock()
        mock_ctx.text.side_effect = RuntimeError("Connection failed")
        mock_ddgs_cls.return_value.__enter__ = lambda s: mock_ctx
        mock_ddgs_cls.return_value.__exit__ = lambda s, *a: None

        with pytest.raises(RuntimeError):
            discovery.search_ebay_listings(player="test")
