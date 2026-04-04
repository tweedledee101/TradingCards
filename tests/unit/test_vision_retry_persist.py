"""vision_retry_scp_from_images.py persist helpers (no DB)."""
import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]


def _load():
    path = _ROOT / "scripts" / "vision_retry_scp_from_images.py"
    spec = importlib.util.spec_from_file_location("vision_retry_scp_from_images", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
def test_confidence_meets_min():
    m = _load()
    assert m._confidence_meets_min("high", "medium")
    assert m._confidence_meets_min("medium", "medium")
    assert not m._confidence_meets_min("low", "medium")
    assert m._confidence_meets_min("unclear", "unclear")


@pytest.mark.unit
def test_profit_bin_matches_pipeline_formula():
    m = _load()
    # find_opportunities: profit = scp - buy - buy * FEE
    buy, ship, scp = 50.0, 0.0, 100.0
    p, r = m._profit_and_roi("buy_it_now", buy, ship, scp)
    assert abs(p - (scp - buy - buy * m.FEE_RATE)) < 0.01
    assert r == (p / buy * 100.0)


@pytest.mark.unit
def test_buy_price_prefers_buy_price_key():
    m = _load()
    b, s = m._buy_price_and_shipping({"buy_price": 12.5, "buy_price_or_bin": 99.0})
    assert b == 12.5


@pytest.mark.unit
def test_listing_type_from_job_source():
    m = _load()
    assert m._listing_type_for_queue_item("auction_finder", {}) == "auction"
    assert m._listing_type_for_queue_item("opportunity_finder", {}) == "buy_it_now"
    assert m._listing_type_for_queue_item("opportunity_finder", {"listing_type": "auction"}) == "auction"
