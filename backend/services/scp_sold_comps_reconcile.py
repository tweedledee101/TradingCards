"""
Pre-eBay reference price: blend SCP catalog ``price`` with ``sold_comps`` median when enough
comps exist, to reduce bad economics from stale or wrong SCP rows.

Used when ``find_opportunities`` runs with ``--dev-reconcile-scp-comps`` (dev / strict runs).
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from backend.services.bin_opportunity_verification import SoldCompSummary, sold_comp_summary_for_identity

MIN_COMPS = 3
STRONG_COMPS = 5


def _coerce_year(year: Any) -> Optional[int]:
    if year is None:
        return None
    if isinstance(year, int):
        return year
    s = str(year).strip()
    if s.isdigit() and len(s) == 4:
        return int(s)
    return None


def compute_scp_reference_price(
    scp: float,
    cs: SoldCompSummary,
    *,
    min_comps: int = MIN_COMPS,
    strong_comps: int = STRONG_COMPS,
) -> Tuple[float, Dict[str, Any]]:
    """Return ``(reference_price, detail_dict)`` for logging / ``verification_detail``."""
    detail: Dict[str, Any] = {
        "schema": "pre_ebay_scp_reconcile",
        "scp_raw": round(float(scp), 2),
        "sold_comps_count": cs.count,
        "sold_comps_median": float(cs.median_price) if cs.median_price is not None else None,
        "sold_comps_avg": float(cs.avg_price) if cs.avg_price is not None else None,
    }

    if scp <= 0 or cs.median_price is None or cs.count < min_comps:
        detail["action"] = "keep_scp"
        detail["reason"] = (
            "no_median" if cs.median_price is None else "insufficient_comps" if cs.count < min_comps else "bad_scp"
        )
        return float(scp), detail

    med = float(cs.median_price)
    ratio_diff = abs(med - scp) / scp if scp else 0.0
    detail["ratio_median_vs_scp"] = round(med / scp, 4) if scp else None
    detail["abs_ratio_diff"] = round(ratio_diff, 4)

    if ratio_diff <= 0.15:
        ref = (scp + med) / 2.0
        detail["action"] = "blend_aligned"
    elif ratio_diff <= 0.40:
        ref = 0.35 * scp + 0.65 * med
        detail["action"] = "blend_moderate"
    else:
        if cs.count >= strong_comps:
            ref = med
            detail["action"] = "use_comp_median"
        else:
            ref = 0.25 * scp + 0.75 * med
            detail["action"] = "blend_divergent_limited_n"

    ref = max(0.01, round(ref, 2))
    detail["reference_price"] = ref
    return ref, detail


def apply_scp_sold_comps_reconcile(db: Session, variation: dict) -> None:
    """Mutate ``variation`` in place: ``price`` → reference; set ``_scp_price_raw``, ``_price_reconciliation``."""
    scp = float(variation.get("price") or 0)
    player = (variation.get("player") or "").strip()
    cn = str(variation.get("card_number") or "").strip()
    year = _coerce_year(variation.get("year"))

    cs = sold_comp_summary_for_identity(
        db,
        player_name=player,
        card_year=year,
        card_number=cn,
        parallel=str(variation.get("parallel") or "") or None,
    )
    ref, detail = compute_scp_reference_price(scp, cs)
    variation["_scp_price_raw"] = scp
    variation["_price_reconciliation"] = detail
    variation["price"] = ref
