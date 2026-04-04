"""Browse GET helper used by player discovery (429 + Retry-After)."""
from unittest.mock import MagicMock, patch

import pytest

from backend.discover_players import _browse_item_summary_get


@pytest.fixture
def scraper():
    s = MagicMock()
    s.base_url = 'https://api.ebay.com/buy/browse/v1'
    s.headers = {}
    s.token_manager = MagicMock()
    s.token_manager.get_token.return_value = 'tok'
    return s


@patch('backend.discover_players.time.sleep', return_value=None)
@patch('backend.discover_players.requests.get')
def test_browse_get_429_then_200(mock_get, _sleep, scraper):
    r429 = MagicMock()
    r429.status_code = 429
    r429.headers = {'Retry-After': '2'}
    r200 = MagicMock()
    r200.status_code = 200
    r200.content = b'{"total": 1}'
    r200.json.return_value = {'total': 1}
    mock_get.side_effect = [r429, r200]

    stats = {}
    r = _browse_item_summary_get(scraper, {'q': 'x', 'limit': 1}, stats=stats)

    assert r.status_code == 200
    assert stats['browse_429_waits'] == 1
    assert mock_get.call_count == 2


@patch('backend.discover_players.time.sleep', return_value=None)
@patch('backend.discover_players.requests.get')
def test_browse_get_401_refreshes_then_200(mock_get, _sleep, scraper):
    r401 = MagicMock()
    r401.status_code = 401
    r200 = MagicMock()
    r200.status_code = 200
    r200.content = b'{}'
    r200.json.return_value = {'total': 0}
    mock_get.side_effect = [r401, r200]

    r = _browse_item_summary_get(scraper, {'q': 'x', 'limit': 1}, stats={})

    assert r.status_code == 200
    scraper.token_manager._refresh_token.assert_called_once()
    assert mock_get.call_count == 2
