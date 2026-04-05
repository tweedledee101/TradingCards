"""sold_comps → Browse seed strings."""
from unittest.mock import MagicMock

import pytest

from backend.services.auction_sold_comp_seeds import sold_comp_search_seeds


@pytest.mark.unit
def test_sold_comp_search_seeds_zero_limit():
    mock_db = MagicMock()
    assert sold_comp_search_seeds(mock_db, limit=0) == []


@pytest.mark.unit
def test_sold_comp_search_seeds_formats_queries():
    mock_db = MagicMock()
    chain = mock_db.query.return_value
    for m in ('filter', 'group_by', 'order_by', 'limit'):
        getattr(chain, m).return_value = chain
    chain.all.return_value = [
        ('Juan Soto', 2024, 'US175', 12),
    ]
    out = sold_comp_search_seeds(mock_db, days=7, limit=5, sport_token='baseball')
    assert len(out) == 1
    assert 'Juan Soto' in out[0]
    assert '2024' in out[0]
    assert '#US175' in out[0]
