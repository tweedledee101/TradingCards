from backend.utils.collectors_edge_cohorts import COHORT_FILTERS, list_cohort_names


def test_list_cohort_names_sorted():
    names = list_cohort_names()
    assert names == sorted(names)
    assert "baseline" in names
    assert "weak_scp_url" in names
    assert "scp_or_qa_gap" in names


def test_cohort_filter_registry_complete():
    assert len(COHORT_FILTERS) >= 6
