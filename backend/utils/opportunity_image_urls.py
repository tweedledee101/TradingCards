"""Listing image URLs from ``opportunities`` (print script, Collectors Edge runner, etc.)."""

from __future__ import annotations

import json
from typing import Any, Iterator

from sqlalchemy import or_

from backend.models import Opportunity


def urls_for_opportunity_row(row: Opportunity) -> list[str]:
    out: list[str] = []
    if row.image_url and str(row.image_url).strip().lower().startswith("http"):
        out.append(str(row.image_url).strip())

    raw = row.listing_image_urls
    if isinstance(raw, list):
        for u in raw:
            if isinstance(u, str) and u.strip().lower().startswith("http"):
                out.append(u.strip())
    elif isinstance(raw, str) and raw.strip().startswith("["):
        try:
            arr = json.loads(raw)
            for u in arr or []:
                if isinstance(u, str) and u.strip().lower().startswith("http"):
                    out.append(u.strip())
        except json.JSONDecodeError:
            pass

    seen: set[str] = set()
    uniq: list[str] = []
    for u in out:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


def opportunity_image_meta(row: Opportunity) -> dict[str, Any]:
    """Identity + pricing slice for cross-checks (Collectors Edge, vision QA, etc.)."""
    scp = row.scp_price
    return {
        "opportunity_id": row.id,
        "ebay_item_id": row.ebay_item_id,
        "ebay_title": (row.ebay_title or "")[:500] if row.ebay_title else None,
        "listing_type": row.listing_type,
        "player_name": row.player_name,
        "card_year": int(row.card_year) if row.card_year is not None else None,
        "card_set": ((row.card_set or "").strip()[:255] or None),
        "card_number": (row.card_number or None),
        "parallel": ((row.parallel or "").strip()[:120] or None),
        "scp_price": float(scp) if scp is not None else None,
    }


def iter_opportunity_image_rows(
    session,
    *,
    listing_type: str = "all",
    skip: int = 0,
    limit: int = 1,
) -> Iterator[tuple[str, dict[str, Any], list[str]]]:
    """Yield (first_image_url, db_meta, all_urls[:15]) per row, newest ``opportunities.id`` first."""
    q = session.query(Opportunity).filter(
        or_(
            Opportunity.image_url.isnot(None),
            Opportunity.listing_image_urls.isnot(None),
        )
    )
    if listing_type != "all":
        q = q.filter(Opportunity.listing_type == listing_type)
    q = q.order_by(Opportunity.id.desc())
    pool = max((limit + skip) * 15, 50 + skip * 10)
    candidates = q.limit(pool).all()

    skip_left = max(0, skip)
    emitted = 0
    for row in candidates:
        if emitted >= limit:
            break
        urls = urls_for_opportunity_row(row)
        if not urls:
            continue
        if skip_left > 0:
            skip_left -= 1
            continue
        emitted += 1
        yield urls[0], opportunity_image_meta(row), urls[:15]


def iter_opportunity_rows_by_ids(
    session,
    ids: list[int],
) -> Iterator[tuple[str, dict[str, Any], list[str]]]:
    """
    Like ``iter_opportunity_image_rows`` but for explicit ``opportunities.id`` values,
    **in the order given**. Skips unknown ids or rows with no HTTP image URL.
    """
    if not ids:
        return
    rows = session.query(Opportunity).filter(Opportunity.id.in_(ids)).all()
    by_id = {r.id: r for r in rows}
    for oid in ids:
        row = by_id.get(oid)
        if row is None:
            continue
        urls = urls_for_opportunity_row(row)
        if not urls:
            continue
        yield urls[0], opportunity_image_meta(row), urls[:15]
