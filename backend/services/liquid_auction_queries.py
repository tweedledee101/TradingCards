"""
Build targeted eBay auction queries from liquid SCP cache entries.

Instead of spraying 300+ broad queries ("baseball card /99"), this reads
the scp_cache for cards with known volume (daily/weekly sales) and builds
precise queries like "Bobby Witt Jr. 2026 Topps 1991 Chrome #91C-19 Orange".

Each query targets a specific card we already have SCP pricing for, so:
- 1 API call = auctions for a card we KNOW has a market
- Step 3 SCP validation is a fast cache hit, not Selenium
- 210x more efficient per API call (Session 85 finding)
"""
from __future__ import annotations

import json
import re
from typing import List, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session


# Volume strings that indicate liquid cards (daily or weekly sales)
_LIQUID_VOLUME_PATTERNS = ('%per day%', '%per week%')

# Volume strings that are too thin to bother
_DEAD_VOLUME = {'rare', '1 sale per year', '2 sales per year'}


def fetch_liquid_cards(
    db: Session,
    *,
    min_price: float = 5.0,
    max_price: float = 1000.0,
    limit: int = 2000,
) -> List[dict]:
    """Return SCP cache variants with daily/weekly volume in the price range.

    Each row has: player_name, card_year, card_number, parallel, card_set,
    price (ungraded), volume, scp_url.
    """
    rows = db.execute(text("""
        SELECT DISTINCT ON (sc.player_name, sc.card_year, sc.card_number, v->>'parallel')
               sc.player_name,
               sc.card_year,
               sc.card_number,
               v->>'parallel' as parallel,
               v->>'card_set' as card_set,
               (v->>'ungraded')::numeric as price,
               v->>'volume' as volume,
               v->>'url' as scp_url,
               v->>'grade_9' as grade_9,
               v->>'psa_10' as psa_10
        FROM scp_cache sc, jsonb_array_elements(sc.variants) v
        WHERE v->>'volume' IS NOT NULL
          AND v->>'volume' != ''
          AND (v->>'ungraded')::numeric BETWEEN :min_p AND :max_p
          AND (LOWER(v->>'volume') LIKE :vol1 OR LOWER(v->>'volume') LIKE :vol2)
        ORDER BY sc.player_name, sc.card_year, sc.card_number, v->>'parallel',
                 CASE WHEN LOWER(v->>'volume') LIKE '%%per day%%' THEN 0 ELSE 1 END,
                 (v->>'ungraded')::numeric DESC
        LIMIT :lim
    """), {
        'min_p': min_price,
        'max_p': max_price,
        'vol1': _LIQUID_VOLUME_PATTERNS[0],
        'vol2': _LIQUID_VOLUME_PATTERNS[1],
        'lim': limit,
    }).fetchall()

    return [dict(r._mapping) for r in rows]


def build_ebay_query(card: dict) -> str:
    """Build a precise eBay search string from a liquid card dict."""
    parts = [card['player_name'].strip()]
    if card.get('card_year'):
        parts.append(str(card['card_year']))
    cs = (card.get('card_set') or '').strip()
    if cs and cs.lower() not in ('unknown', 'base', ''):
        parts.append(cs)
    cn = (card.get('card_number') or '').strip()
    if cn:
        parts.append(f'#{cn}')
    par = (card.get('parallel') or 'Base').strip()
    if par and par != 'Base':
        parts.append(par)
    return ' '.join(parts)


def build_liquid_auction_queries(
    db: Session,
    *,
    min_price: float = 5.0,
    max_price: float = 1000.0,
    limit: int = 2000,
) -> Tuple[List[str], List[dict], dict]:
    """Build eBay queries from liquid SCP cards.

    Returns:
        (queries, cards, meta) where cards[i] corresponds to queries[i]
        so Step 3 can instantly look up the SCP price.
    """
    cards = fetch_liquid_cards(db, min_price=min_price, max_price=max_price, limit=limit)

    queries = []
    matched_cards = []
    seen = set()

    for card in cards:
        q = build_ebay_query(card)
        q_key = q.lower()
        if q_key in seen:
            continue
        seen.add(q_key)
        queries.append(q)
        matched_cards.append(card)

    meta = {
        'source': 'scp_cache_liquid',
        'total_liquid_variants': len(cards),
        'unique_queries': len(queries),
        'price_range': [min_price, max_price],
    }
    return queries, matched_cards, meta
