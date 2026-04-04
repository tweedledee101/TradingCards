"""Queue shaping for vision_retry from stored opportunities (no live DB)."""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from backend.utils.vision_queue_from_opportunities import (
    fetch_vision_queue_from_opportunities,
    _listing_urls,
    _normalize_ebay_item_id,
    _pipeline_card_label,
)


def test_normalize_ebay_item_id():
    assert _normalize_ebay_item_id("v1|12345") == "12345"
    assert _normalize_ebay_item_id("99") == "99"
    assert _normalize_ebay_item_id(None) is None


def test_listing_urls_orders_main_image_first():
    row = MagicMock()
    row.image_url = "https://i.ebayimg.com/a.jpg"
    row.listing_image_urls = ["https://i.ebayimg.com/b.jpg"]
    u = _listing_urls(row)
    assert u[0] == "https://i.ebayimg.com/a.jpg"


def test_pipeline_card_label():
    row = MagicMock()
    row.player_name = "Test Player"
    row.card_year = 2020
    row.card_set = "Topps"
    row.card_number = "FA-1"
    row.parallel = "Gold"
    assert "Test Player" in _pipeline_card_label(row)
    assert "#FA-1" in _pipeline_card_label(row)
    assert "[Gold]" in _pipeline_card_label(row)


@pytest.mark.unit
def test_fetch_vision_queue_skips_no_http_images():
    session = MagicMock()
    bad = MagicMock()
    bad.id = 1
    bad.image_url = None
    bad.listing_image_urls = None
    bad.player_name = "X"
    bad.card_year = None
    bad.card_set = None
    bad.card_number = None
    bad.parallel = None
    bad.scp_price = None
    bad.buy_price = None
    bad.ebay_item_id = None
    bad.ebay_title = ""

    good = MagicMock()
    good.id = 2
    good.image_url = "https://i.ebayimg.com/x.jpg"
    good.listing_image_urls = []
    good.player_name = "A"
    good.card_year = 2019
    good.card_set = "Finest"
    good.card_number = "1"
    good.parallel = "Base"
    good.scp_price = Decimal("10.00")
    good.buy_price = Decimal("5.00")
    good.ebay_item_id = "999"
    good.ebay_title = "Title here"

    chain = MagicMock()
    chain.filter.return_value = chain
    chain.order_by.return_value = chain
    chain.limit.return_value = chain
    chain.all.return_value = [bad, good]
    session.query.return_value = chain

    out = fetch_vision_queue_from_opportunities(session, limit=5)
    assert len(out) == 1
    assert out[0]["opportunity_id"] == 2
    assert out[0]["reason"] == "from_recent_opportunities"
    assert out[0]["image_urls"][0].startswith("https://")
