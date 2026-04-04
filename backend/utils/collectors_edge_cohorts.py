"""
Sample ``opportunities`` rows with listing images for Collectors Edge **exploration** runs.

Cohorts help compare CE behavior on baseline listings vs weak SCP / QA attention rows.
All sampling scans recent ids first (newest ``opportunities.id``) and stays read-only.
"""

from __future__ import annotations

from typing import Any, Callable, Iterator

from sqlalchemy import or_

from backend.models import Opportunity

from backend.utils.opportunity_image_urls import urls_for_opportunity_row

CohortFn = Callable[[Opportunity], bool]

# Keys are CLI / script names; values filter a row that already has ≥1 image URL.
COHORT_FILTERS: dict[str, CohortFn] = {
    # Any recent row with an image (same spirit as default --from-db ordering).
    "baseline": lambda row: True,
    # No product URL from SCP scrape (still may have heuristic price from pipeline).
    "weak_scp_url": lambda row: not (row.scp_url and str(row.scp_url).strip()),
    # Pipeline marked suspicious match / pricing.
    "flagged": lambda row: bool(row.flagged),
    # QA still open or escalated.
    "qa_attention": lambda row: (row.qa_status or "pending").lower() in (
        "pending",
        "flagged",
        "critical",
    ),
    "auction": lambda row: (row.listing_type or "").lower() == "auction",
    "bin": lambda row: (row.listing_type or "buy_it_now").lower() == "buy_it_now",
    # Ingest used a non-SCP price path when recorded.
    "non_scp_price_source": lambda row: (row.price_source or "scp").lower() != "scp",
    # Rows where SCP page link failed or match is suspect — **not** "everyone qa=pending".
    "scp_or_qa_gap": lambda row: (
        not (row.scp_url and str(row.scp_url).strip())
        or bool(row.flagged)
        or (row.qa_status or "").lower() in ("flagged", "critical")
    ),
}


def list_cohort_names() -> list[str]:
    return sorted(COHORT_FILTERS.keys())


def sample_opportunity_ids_for_cohort(
    session,
    cohort: str,
    *,
    limit: int,
    scan_cap: int = 600,
    exclude_ids: set[int] | frozenset[int] | None = None,
) -> list[int]:
    """
    Return up to ``limit`` opportunity ids (newest first) that have an image URL and
    pass the cohort predicate.
    """
    fn = COHORT_FILTERS.get(cohort)
    if fn is None:
        known = ", ".join(list_cohort_names())
        raise ValueError(f"Unknown cohort {cohort!r}. Use one of: {known}")

    ex = exclude_ids or frozenset()
    q = (
        session.query(Opportunity)
        .filter(
            or_(
                Opportunity.image_url.isnot(None),
                Opportunity.listing_image_urls.isnot(None),
            )
        )
        .order_by(Opportunity.id.desc())
        .limit(max(scan_cap, limit * 50))
    )
    out: list[int] = []
    for row in q:
        if row.id in ex:
            continue
        if not urls_for_opportunity_row(row):
            continue
        if not fn(row):
            continue
        out.append(row.id)
        if len(out) >= limit:
            break
    return out


def cohort_row_summary(session, opportunity_id: int) -> dict[str, Any] | None:
    """Light snapshot for exploration logs (no secrets)."""
    row = session.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not row:
        return None
    has_url = bool(row.scp_url and str(row.scp_url).strip())
    return {
        "opportunity_id": row.id,
        "listing_type": row.listing_type,
        "flagged": bool(row.flagged),
        "qa_status": row.qa_status,
        "price_source": row.price_source,
        "has_scp_url": has_url,
        "player_name": row.player_name,
        "card_year": int(row.card_year) if row.card_year is not None else None,
        "card_number": row.card_number,
        "parallel": (row.parallel or "")[:80] or None,
        "ebay_title": (row.ebay_title or "")[:120] if row.ebay_title else None,
    }


def iter_cohort_plan(
    session,
    cohorts: list[str],
    *,
    per_cohort: int,
    scan_cap: int = 600,
    dedupe_globally: bool = True,
) -> Iterator[tuple[str, list[int]]]:
    """Yield (cohort_name, [ids...]) for each cohort in order.

    When ``dedupe_globally`` is True (default), ids already chosen for an earlier
    cohort in this plan are excluded from later cohorts so one explore batch does
    not run CE twice on the same opportunity.
    """
    excluded: set[int] = set()
    for name in cohorts:
        ids = sample_opportunity_ids_for_cohort(
            session,
            name,
            limit=per_cohort,
            scan_cap=scan_cap,
            exclude_ids=excluded if dedupe_globally else None,
        )
        if dedupe_globally:
            excluded.update(ids)
        yield name, ids
