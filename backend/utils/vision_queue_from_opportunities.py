"""
Build a vision-retry queue from stored ``opportunities`` rows (CDN image URLs).

Used when ``job_runs`` has no ``vision_post_pipeline_queue_sample`` yet, or for ad-hoc
tertiary checks on rows already in the DB. Does not change opportunities.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_

from backend.models import Opportunity


def _listing_urls(row: Opportunity) -> list[str]:
    urls: list[str] = []
    raw = row.listing_image_urls
    if raw:
        if isinstance(raw, list):
            urls.extend(str(u).strip() for u in raw if u and str(u).strip().startswith("http"))
        elif isinstance(raw, str):
            # unlikely for JSONB but be defensive
            urls.append(raw.strip())
    iu = (row.image_url or "").strip()
    if iu.startswith("http") and iu not in urls:
        urls.insert(0, iu)
    return urls[:15]


def _pipeline_card_label(row: Opportunity) -> str:
    parts: list[str] = []
    if row.player_name:
        parts.append(str(row.player_name).strip())
    if row.card_year is not None:
        parts.append(str(int(row.card_year)))
    if row.card_set:
        parts.append(str(row.card_set).strip())
    if row.card_number:
        parts.append(f"#{row.card_number}")
    if row.parallel and str(row.parallel).strip() and str(row.parallel).strip().lower() != "base":
        parts.append(f"[{row.parallel}]")
    return " ".join(parts).strip()


def _normalize_ebay_item_id(raw: str | None) -> str | None:
    if not raw:
        return None
    s = str(raw).strip()
    if "|" in s:
        s = s.split("|")[-1].strip()
    return s or None


def fetch_vision_queue_from_opportunities(
    session,
    *,
    limit: int = 10,
    listing_type: str | None = None,
) -> list[dict[str, Any]]:
    """
    Return up to ``limit`` queue dicts compatible with ``vision_retry_scp_from_images.py``.

    Newest ``opportunities.id`` first. Skips rows with no HTTP image URLs.
    """
    lim = max(1, min(int(limit), 200))
    q = (
        session.query(Opportunity)
        .filter(
            or_(
                Opportunity.image_url.isnot(None),
                Opportunity.listing_image_urls.isnot(None),
            )
        )
        .order_by(Opportunity.id.desc())
    )
    if listing_type:
        q = q.filter(Opportunity.listing_type == listing_type)

    out: list[dict[str, Any]] = []
    for row in q.limit(lim * 4).all():  # scan a bit wider if some rows lack usable URLs
        urls = _listing_urls(row)
        if not urls:
            continue
        scp = float(row.scp_price) if row.scp_price is not None else None
        buy = float(row.buy_price) if row.buy_price is not None else None
        lt = (row.listing_type or "buy_it_now").strip()
        ship = float(row.shipping) if row.shipping is not None else 0.0
        out.append(
            {
                "reason": "from_recent_opportunities",
                "opportunity_id": row.id,
                "listing_type": lt,
                "shipping": ship,
                "pipeline_card": _pipeline_card_label(row),
                "scp_price": scp,
                "buy_price": buy,
                "ebay_item_id": _normalize_ebay_item_id(row.ebay_item_id),
                "title": ((row.ebay_title or "")[:240]),
                "image_urls": urls,
            }
        )
        if len(out) >= lim:
            break
    return out
