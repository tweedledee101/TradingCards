"""SCP variant sanity check for the BIN pipeline.

When the pipeline finds an opportunity where buy_price << scp_price, check if
there's a cheaper SCP variant for the same player/year/card# that better explains
the eBay price. If so, the pipeline matched the wrong parallel.

Example: Pipeline matched "Blue Rainbow" at $193 but the eBay listing at $60 is
actually "Aqua Rainbow" at $56. The cheaper variant is within 30% of the buy price,
so the pipeline's match is wrong.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from sqlalchemy import text


def check_variant_sanity(
    db,
    player_name: str,
    card_year: Optional[int],
    card_number: Optional[str],
    pipeline_scp_price: float,
    buy_price: float,
) -> Optional[Dict[str, Any]]:
    """Check if a cheaper SCP variant better explains the eBay buy price.

    Returns dict with likely_wrong_parallel=True if a cheaper variant is
    closer to the buy price than the pipeline's SCP price.
    Returns None if no data or check passes.
    """
    if not player_name or not card_number or not card_year:
        return None

    rows = db.execute(
        text(
            "SELECT variants FROM scp_cache "
            "WHERE player_name ILIKE :p AND card_year = :y AND card_number ILIKE :n"
        ),
        {"p": player_name, "y": card_year, "n": card_number},
    ).fetchall()

    if not rows:
        return None

    all_variants = []
    for row in rows:
        variants = row[0]
        if isinstance(variants, str):
            variants = json.loads(variants)
        if not isinstance(variants, list):
            continue
        for v in variants:
            price = v.get('ungraded') or 0
            if price and float(price) > 0:
                all_variants.append({
                    'parallel': v.get('parallel', 'Base'),
                    'price': float(price),
                })

    if not all_variants:
        return None

    # Find the variant closest to the buy price
    closest = min(all_variants, key=lambda v: abs(v['price'] - buy_price))

    # If the closest variant is within 40% of buy price AND pipeline SCP is >2x closest,
    # the pipeline probably matched the wrong parallel
    closest_gap = abs(closest['price'] - buy_price)
    closest_ratio = closest_gap / max(buy_price, 1)
    pipeline_vs_closest = pipeline_scp_price / max(closest['price'], 1)

    if closest_ratio < 0.40 and pipeline_vs_closest > 1.67:
        return {
            'likely_wrong_parallel': True,
            'closest_parallel': closest['parallel'],
            'closest_price': closest['price'],
            'closest_gap': round(closest_gap, 2),
            'pipeline_vs_closest_ratio': round(pipeline_vs_closest, 2),
        }

    return None
