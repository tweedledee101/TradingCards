from unittest.mock import MagicMock

from backend.utils.ebay_rate_limits import parse_ratelimit_headers, _pick_browse_rate_entry


def test_parse_ratelimit_headers():
    r = MagicMock()
    r.headers = {
        'X-EBAY-C-RATELIMIT-LIMIT': '5000',
        'X-EBAY-C-RATELIMIT-REMAINING': '120',
        'X-EBAY-C-RATELIMIT-RESET': '2026-01-01T00:00:00.000Z',
    }
    out = parse_ratelimit_headers(r)
    assert out['limit'] == '5000'
    assert out['remaining'] == '120'
    assert out['reset'].startswith('2026')
    assert out['source'] == 'response_headers'


def test_pick_browse_rate_entry_prefers_search_like_resource():
    data = {
        'rateLimits': [
            {
                'apiContext': 'Buy',
                'apiName': 'Browse',
                'resources': [
                    {'name': 'buy.browse.other', 'rates': [{'limit': 100, 'remaining': 50}]},
                    {'name': 'buy.browse.item_summary.search', 'rates': [{'limit': 5000, 'remaining': 10}]},
                ],
            }
        ]
    }
    picked = _pick_browse_rate_entry(data)
    assert picked is not None
    assert picked['remaining'] == 10
    assert 'item_summary' in picked['resource']
