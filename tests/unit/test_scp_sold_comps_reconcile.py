from backend.services.bin_opportunity_verification import SoldCompSummary
from backend.services.scp_sold_comps_reconcile import compute_scp_reference_price


def test_reconcile_keep_scp_insufficient_comps():
    cs = SoldCompSummary(2, 50.0, 48.0, None)
    ref, d = compute_scp_reference_price(100.0, cs)
    assert ref == 100.0
    assert d["action"] == "keep_scp"


def test_reconcile_blend_aligned():
    cs = SoldCompSummary(5, 95.0, 94.0, None)
    ref, d = compute_scp_reference_price(100.0, cs)
    assert d["action"] == "blend_aligned"
    assert ref == 97.5


def test_reconcile_use_median_when_divergent_strong():
    cs = SoldCompSummary(6, 40.0, 38.0, None)
    ref, d = compute_scp_reference_price(100.0, cs)
    assert d["action"] == "use_comp_median"
    assert ref == 40.0
