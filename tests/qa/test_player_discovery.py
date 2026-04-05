"""
Test: Player discovery must use live eBay volume data, never stale DB queries.

If get_hot_players returns [] on an empty database, the pipeline is broken --
it means we regressed to querying internal data instead of discovering from eBay.
"""
import pytest
from unittest.mock import patch, MagicMock


def test_get_hot_players_calls_ebay_not_database():
    """get_hot_players must call discover_top_players (eBay API), not query the DB."""
    with patch('backend.discover_players.discover_top_players') as mock_discover:
        mock_discover.return_value = [
            {'player_name': 'Shohei Ohtani', 'sport': 'Baseball', 'sales_volume': 5000},
            {'player_name': 'Aaron Judge', 'sport': 'Baseball', 'sales_volume': 3000},
        ]
        # Re-import to pick up the mock
        import importlib
        import find_opportunities
        importlib.reload(find_opportunities)

        players = find_opportunities.get_hot_players(limit=2)

        mock_discover.assert_called_once_with(days=7, limit=2, sport='Baseball')
        assert len(players) == 2
        assert players[0] == 'Shohei Ohtani'
        assert players[1] == 'Aaron Judge'


def test_hot_player_names_for_pipeline_wraps_discover():
    with patch('backend.discover_players.discover_top_players') as mock_discover:
        mock_discover.return_value = [
            {'player_name': 'Test Star', 'sport': 'Baseball', 'sales_volume': 1},
        ]
        from backend.discover_players import hot_player_names_for_pipeline

        names = hot_player_names_for_pipeline(limit=1, sport='Baseball', days=7)
        assert names == ['Test Star']
        mock_discover.assert_called_once_with(days=7, limit=1, sport='Baseball')


def test_get_hot_players_never_returns_empty_with_seed_players():
    """If eBay returns volume for any seed player, we must get results."""
    with patch('backend.discover_players.discover_top_players') as mock_discover:
        mock_discover.return_value = [
            {'player_name': 'Paul Skenes', 'sport': 'Baseball', 'sales_volume': 100},
        ]
        import importlib
        import find_opportunities
        importlib.reload(find_opportunities)

        players = find_opportunities.get_hot_players(limit=40)

        assert len(players) > 0, "get_hot_players must not return empty when eBay has data"


def test_get_hot_players_does_not_import_database_models():
    """get_hot_players must not depend on Card/Sale models (no DB dependency)."""
    import inspect
    from find_opportunities import get_hot_players
    source = inspect.getsource(get_hot_players)

    assert 'SessionLocal' not in source, "get_hot_players must not use SessionLocal (DB dependency)"
    assert 'Card' not in source, "get_hot_players must not query Card model"
    assert 'Sale' not in source, "get_hot_players must not query Sale model"
    assert (
        'hot_player_names_for_pipeline' in source or 'discover_top_players' in source
    ), "get_hot_players must delegate to eBay volume discovery (not DB)"
