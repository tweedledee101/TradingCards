"""
Merge Collectors Edge ``ce_pipeline_analysis`` into ``opportunities.qa_flags``.

CE rules use the same object shape as ``qa_opportunities.py`` (rule / severity / reason)
so the API and React cards render them consistently. Prior CE-derived entries are
replaced on each merge; pipeline QA rules (e.g. ``high_roi``) are preserved.
"""

from __future__ import annotations

from typing import Any

CE_QA_SOURCE = "collectors_edge"

# Align with qa_opportunities.py severities for UI styling.
_CE_RULE_SEVERITY: dict[str, str] = {
    "ce_player_mismatch_risk": "critical",
    "ce_year_mismatch_risk": "warning",
    "ce_no_recent_comps": "warning",
    "ce_few_comps": "warning",
    "ce_vs_scp_low": "warning",
    "ce_vs_scp_high": "warning",
    "ce_low_confidence_bundle": "info",
}

_CE_RULE_REASON_FALLBACK: dict[str, str] = {
    "ce_player_mismatch_risk": (
        "Collectors Edge identity text does not clearly include the pipeline player — "
        "wrong image, parse noise, or multi-player lot."
    ),
    "ce_year_mismatch_risk": (
        "Collectors Edge year signals do not align with pipeline card_year — "
        "verify product vs listing year."
    ),
    "ce_no_recent_comps": "Collectors Edge: no recent comparable sales cited.",
    "ce_few_comps": "Collectors Edge: few comparable sales cited.",
    "ce_vs_scp_low": "Collectors Edge median is well below SCP ungraded — verify comps and parallel.",
    "ce_vs_scp_high": "Collectors Edge median is well above SCP ungraded — verify parallel / autograph / condition narrative.",
    "ce_low_confidence_bundle": (
        "Collectors Edge shows weak data or low confidence — do not rely on CE $ alone for go/no-go."
    ),
}


def _reason_for_rule(rule: str, analysis: dict[str, Any]) -> str:
    """Prefer a related verification line; fall back to static copy."""
    vps = analysis.get("verification_points") or []
    adds = analysis.get("additional_indicators") or []
    for line in list(vps) + list(adds):
        if not isinstance(line, str) or len(line) < 12:
            continue
        low = line.lower()
        if rule == "ce_player_mismatch_risk" and "mismatch" in low and "player" in low:
            return line.strip()
        if rule == "ce_year_mismatch_risk" and "year" in low and ("pipeline" in low or "verify" in low):
            return line.strip()
        if rule == "ce_no_recent_comps" and "no recent" in low:
            return line.strip()
        if rule == "ce_few_comps" and "few comparable" in low:
            return line.strip()
        if rule == "ce_vs_scp_low" and "below scp" in low:
            return line.strip()
        if rule == "ce_vs_scp_high" and "above scp" in low:
            return line.strip()
        if rule == "ce_low_confidence_bundle" and ("weak" in low or "confidence" in low) and "composite" in low:
            return line.strip()
    return _CE_RULE_REASON_FALLBACK.get(rule, f"Collectors Edge QA signal: {rule}")


def ce_qa_entries_from_analysis(ce_pipeline_analysis: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Build ``qa_opportunities``-shaped flag dicts from ``suggested_qa_flags``."""
    if not ce_pipeline_analysis:
        return []
    names = ce_pipeline_analysis.get("suggested_qa_flags") or []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for name in names:
        if not isinstance(name, str) or not name.strip():
            continue
        rule = name.strip()
        if rule in seen:
            continue
        seen.add(rule)
        sev = _CE_RULE_SEVERITY.get(rule, "info")
        out.append(
            {
                "rule": rule,
                "severity": sev,
                "reason": _reason_for_rule(rule, ce_pipeline_analysis),
                "source": CE_QA_SOURCE,
            }
        )
    return out


def _is_ce_flag_entry(f: dict[str, Any]) -> bool:
    r = f.get("rule")
    if isinstance(r, str) and r.startswith("ce_"):
        return True
    return f.get("source") == CE_QA_SOURCE


def merge_ce_qa_into_existing(
    existing_qa_flags: list[Any] | None,
    ce_pipeline_analysis: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """
    Drop prior CE-derived flags, keep pipeline / manual QA objects, append fresh CE flags.
    String entries (legacy) are kept unless they look like CE rule names.
    """
    raw = list(existing_qa_flags or [])
    kept: list[dict[str, Any]] = []
    for f in raw:
        if isinstance(f, str):
            s = f.strip()
            if s.startswith("ce_"):
                continue
            kept.append({"rule": s, "severity": "info", "reason": s})
            continue
        if not isinstance(f, dict):
            continue
        if _is_ce_flag_entry(f):
            continue
        kept.append(dict(f))

    fresh = ce_qa_entries_from_analysis(ce_pipeline_analysis)
    return kept + fresh


def qa_status_after_ce_merge(prior_status: str | None, ce_entries: list[dict[str, Any]]) -> str | None:
    """Return new qa_status when CE adds flags; None means leave unchanged."""
    if not ce_entries:
        return None
    if any(e.get("severity") == "critical" for e in ce_entries):
        return "critical"
    ps = (prior_status or "pending").lower()
    if ps in ("pending", "clean"):
        return "flagged"
    return None


def flagged_after_ce_merge(prior_flagged: bool, ce_entries: list[dict[str, Any]]) -> bool | None:
    """Return new ``flagged`` when CE reports critical; None means leave unchanged."""
    if not ce_entries:
        return None
    if any(e.get("severity") == "critical" for e in ce_entries):
        return True
    return None


def opportunity_updates_from_ce_analysis(
    *,
    existing_qa_flags: list[Any] | None,
    qa_status: str | None,
    flagged: bool | None,
    ce_pipeline_analysis: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Fields to apply on ``Opportunity`` after a successful CE photo run.

    Always includes ``qa_flags`` (merged list). Optionally ``qa_status`` and ``flagged``.
    """
    merged = merge_ce_qa_into_existing(existing_qa_flags, ce_pipeline_analysis)
    ce_entries = ce_qa_entries_from_analysis(ce_pipeline_analysis)
    out: dict[str, Any] = {"qa_flags": merged}
    st = qa_status_after_ce_merge(qa_status, ce_entries)
    if st is not None:
        out["qa_status"] = st
    fg = flagged_after_ce_merge(bool(flagged), ce_entries)
    if fg is not None:
        out["flagged"] = fg
    return out
