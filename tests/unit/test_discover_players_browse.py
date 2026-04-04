"""Browse GET helper used by player discovery (429 + decreasing backoff)."""
from unittest.mock import MagicMock, patch

import pytest

from backend.discover_players import _browse_item_summary_get, _discover_429_backoff_seconds


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
def test_browse_get_429_retry_after_respects_schedule_not_60(mock_get, mock_sleep, scraper):
    """Retry-After 90 does not force 60s; first backoff uses schedule step 25s."""
    r429 = MagicMock()
    r429.status_code = 429
    r429.headers = {'Retry-After': '90'}
    r200 = MagicMock()
    r200.status_code = 200
    r200.content = b'{"total": 1}'
    r200.json.return_value = {'total': 1}
    mock_get.side_effect = [r429, r200]

    stats = {}
    r = _browse_item_summary_get(scraper, {'q': 'x', 'limit': 1}, stats=stats)

    assert r.status_code == 200
    waits = [c.args[0] for c in mock_sleep.call_args_list if c.args]
    assert 25.0 in waits


@patch('backend.discover_players.time.sleep', return_value=None)
@patch('backend.discover_players.requests.get')
def test_browse_get_two_429s_use_decreasing_backoff(mock_get, mock_sleep, scraper):
    r429 = MagicMock()
    r429.status_code = 429
    r429.headers = {}
    r200 = MagicMock()
    r200.status_code = 200
    r200.content = b'{"total": 1}'
    r200.json.return_value = {'total': 1}
    mock_get.side_effect = [r429, r429, r200]

    stats = {}
    r = _browse_item_summary_get(scraper, {'q': 'x', 'limit': 1}, stats=stats)

    assert r.status_code == 200
    waits = [c.args[0] for c in mock_sleep.call_args_list if c.args]
    assert waits.index(25.0) < waits.index(12.0)


def test_discover_429_backoff_short_retry_after():
    assert _discover_429_backoff_seconds(0, '3') == 3.0
    assert _discover_429_backoff_seconds(1, '90') == 12.0


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
