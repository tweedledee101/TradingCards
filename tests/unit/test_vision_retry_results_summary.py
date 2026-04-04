"""Regression: job_runs.results_summary as str vs dict (RDS)."""
import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]


def _load_vision_retry_module():
    path = _ROOT / "scripts" / "vision_retry_scp_from_images.py"
    spec = importlib.util.spec_from_file_location("vision_retry_scp_from_images", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
def test_parse_results_summary_dict_roundtrip():
    mod = _load_vision_retry_module()
    raw = {"no_scp_vision_queue_sample": [{"ebay_item_id": "1", "image_urls": ["https://x"]}]}
    data = mod._parse_results_summary(raw)
    assert data["no_scp_vision_queue_sample"][0]["ebay_item_id"] == "1"


@pytest.mark.unit
def test_parse_results_summary_json_str():
    mod = _load_vision_retry_module()
    data = mod._parse_results_summary('{"no_scp_vision_queue_sample": []}')
    assert data["no_scp_vision_queue_sample"] == []


@pytest.mark.unit
def test_parse_results_summary_none():
    mod = _load_vision_retry_module()
    assert mod._parse_results_summary(None) == {}


@pytest.mark.unit
def test_parse_results_summary_bad_json():
    mod = _load_vision_retry_module()
    assert mod._parse_results_summary("not json") == {}


@pytest.mark.unit
def test_vision_queue_from_summary_prefers_merged():
    mod = _load_vision_retry_module()
    data = {
        "vision_post_pipeline_queue_sample": [{"ebay_item_id": "9", "reason": "x"}],
        "no_scp_vision_queue_sample": [{"ebay_item_id": "1"}],
    }
    q = mod._vision_queue_from_summary(data, job_name="auction_finder")
    assert len(q) == 1 and q[0]["ebay_item_id"] == "9"


@pytest.mark.unit
def test_vision_queue_unified_json_null_treated_as_empty():
    mod = _load_vision_retry_module()
    data = {"vision_post_pipeline_queue_sample": None}
    assert mod._vision_queue_from_summary(data, job_name="auction_finder") == []


@pytest.mark.unit
def test_vision_queue_empty_list_does_not_fallback_to_legacy():
    mod = _load_vision_retry_module()
    data = {
        "vision_post_pipeline_queue_sample": [],
        "no_scp_vision_queue_sample": [{"ebay_item_id": "legacy", "image_urls": ["u"]}],
    }
    q = mod._vision_queue_from_summary(data, job_name="auction_finder")
    assert q == []


@pytest.mark.unit
def test_vision_queue_from_summary_legacy_auction():
    mod = _load_vision_retry_module()
    data = {"no_scp_vision_queue_sample": [{"ebay_item_id": "2", "image_urls": ["u"]}]}
    q = mod._vision_queue_from_summary(data, job_name="auction_finder")
    assert q[0]["reason"] == "auction_no_pricing_after_fallbacks"


@pytest.mark.unit
def test_vision_queue_opportunity_finder_no_legacy():
    mod = _load_vision_retry_module()
    data = {"no_scp_vision_queue_sample": [{"ebay_item_id": "2", "image_urls": ["u"]}]}
    assert mod._vision_queue_from_summary(data, job_name="opportunity_finder") == []


@pytest.mark.unit
def test_vision_queue_unified_includes_step2_and_step3_rows():
    mod = _load_vision_retry_module()
    data = {
        "vision_post_pipeline_queue_sample": [
            {"ebay_item_id": "s2", "reason": "step2_no_year", "image_urls": ["https://i"]},
            {
                "ebay_item_id": "s3",
                "reason": "auction_no_pricing_after_fallbacks",
                "image_urls": ["https://j"],
            },
        ],
    }
    q = mod._vision_queue_from_summary(data, job_name="auction_finder")
    assert len(q) == 2
    assert q[0]["reason"] == "step2_no_year"
    assert q[1]["reason"] == "auction_no_pricing_after_fallbacks"
