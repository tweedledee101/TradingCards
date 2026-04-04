"""CE suggested_qa_flags → opportunities.qa_flags merge (object shape matches qa_opportunities)."""

from backend.utils.collectors_edge_qa_merge import (
    ce_qa_entries_from_analysis,
    merge_ce_qa_into_existing,
    opportunity_updates_from_ce_analysis,
    qa_status_after_ce_merge,
)


def test_merge_replaces_prior_ce_keeps_pipeline():
    existing = [
        {"rule": "high_roi", "severity": "warning", "reason": "ROI high"},
        {
            "rule": "ce_few_comps",
            "severity": "warning",
            "reason": "stale",
            "source": "collectors_edge",
        },
    ]
    analysis = {"suggested_qa_flags": ["ce_no_recent_comps"], "verification_points": []}
    merged = merge_ce_qa_into_existing(existing, analysis)
    rules = [x["rule"] for x in merged]
    assert rules == ["high_roi", "ce_no_recent_comps"]
    ce_row = merged[1]
    assert ce_row["severity"] == "warning"
    assert ce_row.get("source") == "collectors_edge"


def test_player_mismatch_critical_severity():
    analysis = {
        "suggested_qa_flags": ["ce_player_mismatch_risk"],
        "verification_points": [
            "Mismatch risk: pipeline player not clearly present in CE identity text"
        ],
    }
    entries = ce_qa_entries_from_analysis(analysis)
    assert len(entries) == 1
    assert entries[0]["severity"] == "critical"
    assert "Mismatch risk" in entries[0]["reason"]


def test_opportunity_updates_escalate_pending_to_flagged():
    updates = opportunity_updates_from_ce_analysis(
        existing_qa_flags=[],
        qa_status="pending",
        flagged=False,
        ce_pipeline_analysis={"suggested_qa_flags": ["ce_few_comps"], "verification_points": []},
    )
    assert updates["qa_status"] == "flagged"
    assert "flagged" not in updates
    assert len(updates["qa_flags"]) == 1


def test_opportunity_updates_critical_sets_flagged():
    updates = opportunity_updates_from_ce_analysis(
        existing_qa_flags=[],
        qa_status="clean",
        flagged=False,
        ce_pipeline_analysis={"suggested_qa_flags": ["ce_player_mismatch_risk"], "verification_points": []},
    )
    assert updates["qa_status"] == "critical"
    assert updates["flagged"] is True


def test_empty_ce_analysis_strips_old_ce_only():
    existing = [
        {"rule": "high_roi", "severity": "warning", "reason": "x"},
        {"rule": "ce_vs_scp_high", "severity": "warning", "reason": "old", "source": "collectors_edge"},
    ]
    merged = merge_ce_qa_into_existing(existing, {"suggested_qa_flags": []})
    assert [x["rule"] for x in merged] == ["high_roi"]


def test_qa_status_unchanged_when_no_ce_flags():
    assert qa_status_after_ce_merge("flagged", []) is None
