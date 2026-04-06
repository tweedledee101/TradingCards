"""
Post-ingest BIN verification: reconcile SCP reference vs 130point ``sold_comps`` and
identity tokens. Collectors Edge photo flow remains a separate Playwright job; this
layer runs headless against the DB and listing CDN URLs only.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.models import Opportunity, SoldComp


@dataclass
class SoldCompSummary:
    count: int
    median_price: Optional[float]
    avg_price: Optional[float]
    latest_sale_date: Optional[str]


def sold_comp_summary_for_identity(
    db: Session,
    *,
    player_name: str,
    card_year: Optional[int],
    card_number: Optional[str],
    limit_rows: int = 40,
    lookback_days: int = 730,
) -> SoldCompSummary:
    """Aggregate recent ``sold_comps`` rows for the same rough identity."""
    if not player_name or not card_number:
        return SoldCompSummary(0, None, None, None)

    nm = player_name.strip().lower()
    cn = (card_number or "").strip().lower()
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    q = (
        db.query(SoldComp.sale_price, SoldComp.sale_date)
        .filter(func.lower(SoldComp.player_name) == nm)
        .filter(func.lower(SoldComp.card_number) == cn)
        .filter(SoldComp.created_at >= cutoff)
    )
    if card_year is not None:
        q = q.filter(or_(SoldComp.card_year == card_year, SoldComp.card_year.is_(None)))

    rows = q.order_by(SoldComp.created_at.desc()).limit(limit_rows).all()
    if not rows:
        return SoldCompSummary(0, None, None, None)

    prices = [float(r.sale_price) for r in rows if r.sale_price is not None]
    prices.sort()
    mid = prices[len(prices) // 2] if prices else None
    avg = sum(prices) / len(prices) if prices else None
    latest = rows[0].sale_date
    return SoldCompSummary(
        count=len(rows),
        median_price=mid,
        avg_price=avg,
        latest_sale_date=str(latest) if latest else None,
    )


def verify_bin_opportunity_row(
    db: Session,
    opp: Opportunity,
    *,
    scp_tol_ratio: float = 0.40,
    conflict_ratio: float = 0.55,
    min_comps_for_verified: int = 3,
) -> Dict[str, Any]:
    """Return ``verification_status`` + ``verification_detail`` patch (merge into existing)."""
    cs = sold_comp_summary_for_identity(
        db,
        player_name=opp.player_name,
        card_year=opp.card_year,
        card_number=opp.card_number,
    )
    scp = float(opp.scp_price)
    buy = float(opp.buy_price)

    detail: Dict[str, Any] = {
        "schema": 2,
        "pipeline": "bin_verify_worker",
        "scp_price": scp,
        "buy_price": buy,
        "sold_comps": {
            "count": cs.count,
            "median_price": cs.median_price,
            "avg_price": cs.avg_price,
            "latest_sale_date": cs.latest_sale_date,
        },
        "ce": {
            "status": "deferred",
            "note": "Use scripts/dev/collectors_edge_photo_run.py --opportunity-ids for Playwright CE",
        },
        "image_urls_sample": (opp.listing_image_urls or [])[:3] if opp.listing_image_urls else [],
    }

    status = "pending"
    reasons: List[str] = []

    if cs.count == 0:
        reasons.append("no_sold_comps_match")
    elif cs.median_price and scp > 0:
        med = float(cs.median_price)
        ratio_scp = abs(med - scp) / scp
        detail["sold_comps"]["ratio_vs_scp"] = round(med / scp, 3)
        if ratio_scp > conflict_ratio:
            detail["sold_comps"]["scp_alignment"] = "divergent"
            reasons.append("scp_vs_comp_median")
            status = "conflict"
        elif cs.count >= min_comps_for_verified and ratio_scp <= scp_tol_ratio:
            detail["sold_comps"]["scp_alignment"] = "aligned"
            status = "verified"

    if opp.flagged and status == "verified":
        status = "pending"
        reasons.append("pipeline_flagged_bin_low_vs_scp")

    detail["reasons"] = reasons
    return {"verification_status": status, "verification_detail": detail}


def apply_verification_to_opportunity(db: Session, opp_id: int) -> bool:
    opp = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opp:
        return False
    lt = opp.listing_type or "buy_it_now"
    if lt != "buy_it_now":
        return False
    patch = verify_bin_opportunity_row(db, opp)
    existing = dict(opp.verification_detail or {})
    merged = {**existing, **patch["verification_detail"]}
    opp.verification_status = patch["verification_status"]
    opp.verification_detail = merged
    db.commit()
    return True
