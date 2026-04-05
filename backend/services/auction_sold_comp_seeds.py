"""Optional Browse ``q`` strings from recent ``sold_comps`` (130point worm) activity."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from sqlalchemy import func

from backend.models import SoldComp


def sold_comp_search_seeds(
    db,
    *,
    days: int = 7,
    limit: int = 25,
    sport_token: str = 'baseball',
) -> List[str]:
    """
    Top (player, year, #) keys by sold row count in the lookback window.

    Produces short queries like ``Juan Soto 2024 #123 baseball card`` so auction Browse
    hits SKUs that have actually cleared recently (card-centric lens vs player-only).
    """
    if limit <= 0:
        return []

    cutoff = datetime.utcnow() - timedelta(days=max(1, days))
    rows = (
        db.query(
            SoldComp.player_name,
            SoldComp.card_year,
            SoldComp.card_number,
            func.count(SoldComp.id).label('cnt'),
        )
        .filter(
            SoldComp.created_at >= cutoff,
            SoldComp.player_name.isnot(None),
            SoldComp.card_year.isnot(None),
            SoldComp.card_number.isnot(None),
            SoldComp.card_number != '',
        )
        .group_by(
            SoldComp.player_name,
            SoldComp.card_year,
            SoldComp.card_number,
        )
        .order_by(func.count(SoldComp.id).desc())
        .limit(limit)
        .all()
    )

    token = (sport_token or 'baseball').strip()
    out: List[str] = []
    for player_name, card_year, card_number, _cnt in rows:
        pn = (player_name or '').strip()
        cn = str(card_number).strip()
        if not pn or not cn:
            continue
        try:
            y = int(card_year)
        except (TypeError, ValueError):
            continue
        q = f'{pn} {y} #{cn} {token} card'
        out.append(' '.join(q.split()))
    return out
