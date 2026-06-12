"""
Market API - Volume leaders from SCP cache.

Shows cards with proven sales velocity (daily/weekly).
Data comes from scp_cache, refreshed by the SCP worm.
"""
from fastapi import APIRouter, Query
from sqlalchemy import text
from typing import Optional

from backend.utils.database import get_db
from fastapi import Depends
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/market/volume-leaders")
def get_volume_leaders(
    sport: Optional[str] = Query(default=None),
    min_price: float = Query(default=5.0),
    max_price: float = Query(default=1000.0),
    volume_filter: str = Query(default="daily_weekly", description="daily_weekly, weekly, monthly"),
    sort: str = Query(default="volume", description="volume, price_desc, price_asc, player"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Cards with proven sales volume from SCP cache."""

    # Build volume filter
    if volume_filter == "daily_weekly":
        vol_clause = "(LOWER(v->>'volume') LIKE '%per day%' OR LOWER(v->>'volume') LIKE '%per week%')"
    elif volume_filter == "weekly":
        vol_clause = "LOWER(v->>'volume') LIKE '%per week%'"
    else:  # monthly
        vol_clause = "(LOWER(v->>'volume') LIKE '%per day%' OR LOWER(v->>'volume') LIKE '%per week%' OR LOWER(v->>'volume') LIKE '%per month%')"

    # Build sort
    sort_clause = {
        'volume': "CASE WHEN LOWER(v->>'volume') LIKE '%per day%' THEN 0 WHEN LOWER(v->>'volume') LIKE '%per week%' THEN 1 ELSE 2 END, (v->>'ungraded')::numeric DESC",
        'price_desc': "(v->>'ungraded')::numeric DESC",
        'price_asc': "(v->>'ungraded')::numeric ASC",
        'player': "sc.player_name ASC, (v->>'ungraded')::numeric DESC",
    }.get(sort, "CASE WHEN LOWER(v->>'volume') LIKE '%per day%' THEN 0 WHEN LOWER(v->>'volume') LIKE '%per week%' THEN 1 ELSE 2 END")

    # Search filter
    search_clause = ""
    params = {'min_p': min_price, 'max_p': max_price, 'lim': limit, 'off': offset}
    if search:
        search_clause = "AND (LOWER(sc.player_name) LIKE :search OR LOWER(v->>'card_set') LIKE :search OR LOWER(v->>'parallel') LIKE :search)"
        params['search'] = f'%{search.lower()}%'

    query = f"""
        SELECT sc.player_name, sc.card_year, sc.card_number,
               v->>'parallel' as parallel,
               v->>'card_set' as card_set,
               (v->>'ungraded')::numeric as price,
               v->>'grade_9' as grade_9,
               v->>'psa_10' as psa_10,
               v->>'volume' as volume,
               v->>'url' as scp_url,
               sc.created_at
        FROM scp_cache sc, jsonb_array_elements(sc.variants) v
        WHERE (v->>'ungraded')::numeric BETWEEN :min_p AND :max_p
          AND v->>'volume' IS NOT NULL AND v->>'volume' != ''
          AND {vol_clause}
          AND LOWER(v->>'volume') NOT LIKE '%rare%'
          AND LOWER(v->>'volume') NOT LIKE '%1 sale per year%'
          AND LOWER(v->>'volume') NOT LIKE '%2 sales per year%'
          {search_clause}
        ORDER BY {sort_clause}
        LIMIT :lim OFFSET :off
    """

    rows = db.execute(text(query), params).fetchall()

    # Count total
    count_query = f"""
        SELECT COUNT(*) FROM scp_cache sc, jsonb_array_elements(sc.variants) v
        WHERE (v->>'ungraded')::numeric BETWEEN :min_p AND :max_p
          AND v->>'volume' IS NOT NULL AND v->>'volume' != ''
          AND {vol_clause}
          AND LOWER(v->>'volume') NOT LIKE '%rare%'
          AND LOWER(v->>'volume') NOT LIKE '%1 sale per year%'
          AND LOWER(v->>'volume') NOT LIKE '%2 sales per year%'
          {search_clause}
    """
    total = db.execute(text(count_query), params).scalar() or 0

    cards = []
    for r in rows:
        cards.append({
            'player_name': r[0],
            'card_year': r[1],
            'card_number': r[2],
            'parallel': r[3] or 'Base',
            'card_set': r[4] or '',
            'price': float(r[5]) if r[5] else None,
            'grade_9': float(r[6]) if r[6] else None,
            'psa_10': float(r[7]) if r[7] else None,
            'volume': r[8],
            'scp_url': r[9],
            'last_updated': r[10].isoformat() if r[10] else None,
        })

    return {
        'total': total,
        'offset': offset,
        'limit': limit,
        'cards': cards,
    }


@router.get("/market/stats")
def get_market_stats(db: Session = Depends(get_db)):
    """Quick stats on the market data."""
    stats = db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE LOWER(v->>'volume') LIKE '%per day%') as daily,
            COUNT(*) FILTER (WHERE LOWER(v->>'volume') LIKE '%per week%') as weekly,
            COUNT(*) FILTER (WHERE LOWER(v->>'volume') LIKE '%per month%') as monthly,
            COUNT(DISTINCT sc.player_name) as players
        FROM scp_cache sc, jsonb_array_elements(sc.variants) v
        WHERE v->>'volume' IS NOT NULL AND v->>'volume' != ''
          AND (v->>'ungraded')::numeric > 5
          AND LOWER(v->>'volume') NOT LIKE '%rare%'
          AND LOWER(v->>'volume') NOT LIKE '%1 sale per year%'
          AND LOWER(v->>'volume') NOT LIKE '%2 sales per year%'
    """)).fetchone()

    return {
        'daily_volume_cards': stats[0] or 0,
        'weekly_volume_cards': stats[1] or 0,
        'monthly_volume_cards': stats[2] or 0,
        'unique_players': stats[3] or 0,
    }
