"""sold_comps / sales vs Browse ranking in discover_top_players."""
from unittest.mock import MagicMock, patch

from backend.discover_players import discover_top_players, fetch_hot_players_from_sold_comps


def test_discover_top_players_sales_returns_without_browse():
    fake = [('Pat Player', 'Baseball', 12)]
    db = MagicMock()
    with patch('backend.discover_players.fetch_hot_players_from_sales', return_value=fake) as m:
        with patch('backend.discover_players.EbayScraper') as ebay_cls:
            out = discover_top_players(
                limit=10,
                sport='Baseball',
                db_session=db,
                rank_source='sales',
                sales_rank_lookback_days=7,
            )
    assert out == [{'player_name': 'Pat Player', 'sport': 'Baseball', 'sales_volume': 12}]
    m.assert_called_once()
    ebay_cls.assert_not_called()


def test_discover_top_players_sold_comps_returns_without_browse():
    fake = [{'player_name': 'Alpha', 'sport': 'Baseball', 'sales_volume': 42}]
    db = MagicMock()
    with patch('backend.discover_players.fetch_hot_players_from_sold_comps', return_value=fake) as m:
        with patch('backend.discover_players.EbayScraper') as ebay_cls:
            out = discover_top_players(
                limit=5,
                sport='Baseball',
                db_session=db,
                rank_source='sold_comps',
                sold_comps_lookback_days=14,
            )
    assert out == fake
    m.assert_called_once_with(db, 14, 5, 'Baseball')
    ebay_cls.assert_not_called()


def test_discover_top_players_sold_comps_empty_falls_back_to_browse():
    db = MagicMock()
    with patch('backend.discover_players.fetch_hot_players_from_sold_comps', return_value=[]):
        with patch('backend.discover_players.EbayScraper') as ebay_cls:
            scraper = MagicMock()
            ebay_cls.return_value = scraper
            with patch('backend.discover_players.fetch_buy_browse_app_quota', return_value=None):
                with patch('backend.discover_players._browse_item_summary_get') as browse_get:
                    browse_get.return_value = MagicMock(
                        status_code=200,
                        content=b'{}',
                        json=lambda: {'total': 0},
                    )
                    discover_top_players(
                        limit=1,
                        sport='Baseball',
                        db_session=db,
                        rank_source='sold_comps',
                        sold_comps_fallback_browse=True,
                        max_queries=1,
                    )
    ebay_cls.assert_called_once()


def test_fetch_hot_players_from_sold_comps_respects_sport_when_cards_exist():
    """Player with dominant Basketball in cards is skipped for Baseball job."""
    db = MagicMock()
    sold_rows = [
        ('Hoops Star', 100),
        ('Slugger Only', 50),
    ]
    qmock = MagicMock()
    db.query.return_value = qmock
    qmock.filter.return_value = qmock
    qmock.group_by.return_value = qmock
    qmock.order_by.return_value = qmock
    qmock.limit.return_value = qmock
    qmock.all.return_value = sold_rows

    with patch('backend.discover_players.dominant_sport_for_player') as dom:
        def _dom(_, name):
            if name == 'Hoops Star':
                return 'Basketball'
            return 'Baseball'

        dom.side_effect = _dom
        out = fetch_hot_players_from_sold_comps(db, lookback_days=7, limit=5, sport_key='Baseball')

    assert len(out) == 1
    assert out[0]['player_name'] == 'Slugger Only'

