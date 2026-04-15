"""CE Variant Correction -- find the correct SCP entry using CE's visual identification.

CE can reliably identify card COLOR and variant type from images (Green vs Blue vs Aqua,
Refractor vs Raywave, etc.) even when it gets the year wrong. Use this to look up the
CORRECT SCP cache entry and recalculate profit.

Uses CE price as an additional signal: if CE price and corrected SCP price agree,
confidence is high that we found the right card.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from backend.utils.database import SessionLocal


# Words that don't help distinguish parallels
_NOISE_WORDS = frozenset({
    'card', 'cards', 'baseball', 'topps', 'panini', 'bowman', 'rookie', 'rc',
    'sp', 'ssp', 'parallel', 'insert', 'series', 'chrome', 'update', 'heritage',
    'stadium', 'club', 'finest', 'select', 'prizm', 'optic', 'mosaic',
    'the', 'of', 'and', 'a', 'an', 'in', 'for', 'from',
})


def _variant_keywords(variant_text: str) -> set[str]:
    """Extract meaningful keywords from a variant description."""
    if not variant_text:
        return set()
    words = re.split(r'[^a-zA-Z0-9]+', variant_text.lower())
    return {w for w in words if w and len(w) >= 2 and w not in _NOISE_WORDS}


def _score_variant_match(ce_keywords: set[str], scp_parallel: str) -> float:
    """Score how well CE variant keywords match an SCP parallel name. 0-1."""
    scp_kw = _variant_keywords(scp_parallel)
    if not ce_keywords or not scp_kw:
        return 0.0
    overlap = ce_keywords & scp_kw
    # Score by fraction of CE keywords found in SCP (CE is usually more specific)
    return len(overlap) / len(ce_keywords) if ce_keywords else 0.0


def find_corrected_scp_entry(
    player_name: str,
    card_year: int,
    card_number: str,
    ce_variant: str,
    ce_card_name: str,
    ce_price: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """Find the SCP cache entry that best matches CE's visual identification.

    Returns dict with: parallel, scp_price, scp_url, match_score, match_method,
    ce_price_agreement (bool).
    Returns None if no good match found.
    """
    if not player_name or not card_number:
        return None

    # Combine CE variant + card name for keyword extraction
    ce_text = f"{ce_variant or ''} {ce_card_name or ''}"
    ce_kw = _variant_keywords(ce_text)
    if not ce_kw:
        return None

    db = SessionLocal()
    try:
        rows = db.execute(
            text(
                "SELECT variants FROM scp_cache "
                "WHERE player_name ILIKE :player "
                "AND card_year = :yr "
                "AND card_number ILIKE :cn"
            ),
            {"player": player_name, "yr": card_year, "cn": card_number},
        ).fetchall()
    finally:
        db.close()

    if not rows:
        return None

    # Score each SCP variant against CE's identification
    candidates: List[Tuple[float, Dict[str, Any]]] = []
    for row in rows:
        variants = row[0]
        if isinstance(variants, str):
            variants = json.loads(variants)
        if not isinstance(variants, list):
            continue
        for v in variants:
            price = v.get('ungraded') or 0
            if not price or float(price) <= 0:
                continue
            parallel = v.get('parallel', 'Base')
            score = _score_variant_match(ce_kw, parallel)

            # Boost score if CE price is close to this SCP price
            price_f = float(price)
            ce_price_close = False
            if ce_price and ce_price > 0 and price_f > 0:
                ratio = ce_price / price_f
                if 0.3 <= ratio <= 3.0:
                    ce_price_close = True
                    score += 0.2  # bonus for price agreement
                if 0.7 <= ratio <= 1.5:
                    score += 0.2  # strong price agreement

            candidates.append((score, {
                'parallel': parallel,
                'scp_price': price_f,
                'scp_url': v.get('url'),
                'grade_9': v.get('grade_9'),
                'psa_10': v.get('psa_10'),
                'match_score': round(score, 3),
                'ce_price_agreement': ce_price_close,
                'scp_parallel_keywords': list(_variant_keywords(parallel)),
                'ce_keywords_used': list(ce_kw),
            }))

    if not candidates:
        return None

    # Sort by score descending, then by price (prefer entries with price closer to CE)
    candidates.sort(key=lambda x: (-x[0], abs((x[1]['scp_price'] - (ce_price or 0)))))

    best_score, best = candidates[0]
    if best_score < 0.3:
        # No meaningful keyword overlap -- can't confidently match
        return None

    # If there are multiple candidates with similar scores, flag ambiguity
    close_candidates = [c for s, c in candidates if s >= best_score - 0.1]
    best['ambiguous'] = len(close_candidates) > 1
    best['candidates_considered'] = len(candidates)
    best['close_alternatives'] = len(close_candidates)

    return best


def recalculate_opportunity(
    buy_price: float,
    corrected_scp_price: float,
    ce_price: Optional[float] = None,
    sold_comps_median: Optional[float] = None,
    sold_comps_count: int = 0,
    fee_rate: float = 0.13,
    min_profit: float = 10.0,
) -> Dict[str, Any]:
    """Recalculate profit using all available price signals.

    Priority: 130point sold comps (real sales) > SCP > CE estimate.
    """
    # Best reference price: prefer 130point if we have 3+ sales
    if sold_comps_median and sold_comps_count >= 3:
        reference_price = sold_comps_median
        price_source = '130point'
    elif corrected_scp_price > 0:
        reference_price = corrected_scp_price
        price_source = 'scp_corrected'
    elif ce_price and ce_price > 0:
        reference_price = ce_price
        price_source = 'ce'
    else:
        return {'is_profitable': False, 'reason': 'no_reference_price'}

    fees = buy_price * fee_rate
    profit = reference_price - buy_price - fees
    roi = (profit / buy_price * 100) if buy_price > 0 else 0

    result = {
        'reference_price': round(reference_price, 2),
        'price_source': price_source,
        'buy_price': round(buy_price, 2),
        'fees': round(fees, 2),
        'corrected_profit': round(profit, 2),
        'corrected_roi': round(roi, 1),
        'is_profitable': profit >= min_profit,
    }

    # All price signals for transparency
    if corrected_scp_price > 0:
        result['scp_price'] = round(corrected_scp_price, 2)
    if ce_price and ce_price > 0:
        result['ce_price'] = round(ce_price, 2)
    if sold_comps_median:
        result['sold_comps_median'] = round(sold_comps_median, 2)
        result['sold_comps_count'] = sold_comps_count

    # Confidence: how many sources agree?
    prices = [p for p in [corrected_scp_price, ce_price, sold_comps_median] if p and p > 0]
    if len(prices) >= 2:
        # Check if all available prices are within 50% of each other
        mn, mx = min(prices), max(prices)
        spread = (mx - mn) / mn if mn > 0 else 999
        result['price_spread'] = round(spread, 3)
        if spread < 0.3:
            result['confidence'] = 'high'
        elif spread < 0.5:
            result['confidence'] = 'medium'
        else:
            result['confidence'] = 'low'
    elif len(prices) == 1:
        result['confidence'] = 'low'

    return result


def full_variant_correction(
    player_name: str,
    card_year: int,
    card_number: str,
    buy_price: float,
    pipeline_scp_price: float,
    pipeline_parallel: str,
    ce_variant: Optional[str],
    ce_card_name: Optional[str],
    ce_price: Optional[float] = None,
) -> Dict[str, Any]:
    """Full correction flow: CE variant -> SCP lookup -> 130point confirmation.

    Returns a dict with corrected pricing, confidence, and whether the
    opportunity is real or a false positive from wrong parallel matching.
    """
    result: Dict[str, Any] = {
        'pipeline_parallel': pipeline_parallel,
        'pipeline_scp_price': pipeline_scp_price,
        'ce_variant': ce_variant,
        'ce_price': ce_price,
    }

    # Step 1: Use CE variant to find correct SCP entry
    scp_match = find_corrected_scp_entry(
        player_name, card_year, card_number,
        ce_variant or '', ce_card_name or '', ce_price,
    )
    corrected_scp = pipeline_scp_price  # default to pipeline if no correction
    if scp_match:
        corrected_scp = scp_match['scp_price']
        result['scp_correction'] = scp_match

    # Step 2: Query 130point for the CE-identified variant
    sold_median = None
    sold_count = 0
    try:
        from backend.scrapers.oneThirtyPoint_scraper import OneThirtyPointScraper
        scraper = OneThirtyPointScraper()
        # Build query from CE's identification
        query_parts = [player_name, str(card_year)]
        if card_number:
            query_parts.append(f'#{card_number}')
        if ce_variant and ce_variant.lower() not in ('base', ''):
            query_parts.append(ce_variant)
        query = ' '.join(query_parts)
        sales = scraper.search(query)
        if sales:
            sold_median = scraper.median_price(sales)
            sold_count = len(sales)
            result['sold_comps_query'] = query
            result['sold_comps_median'] = sold_median
            result['sold_comps_count'] = sold_count
    except Exception as e:
        result['sold_comps_error'] = str(e)[:100]

    # Step 3: Recalculate with all signals
    calc = recalculate_opportunity(
        buy_price=buy_price,
        corrected_scp_price=corrected_scp,
        ce_price=ce_price,
        sold_comps_median=sold_median,
        sold_comps_count=sold_count,
    )
    result['calculation'] = calc

    # Step 4: Verdict
    if calc['is_profitable'] and calc.get('confidence') in ('high', 'medium'):
        result['verdict'] = 'real_opportunity'
    elif calc['is_profitable'] and calc.get('confidence') == 'low':
        result['verdict'] = 'possible_opportunity'
    elif not calc['is_profitable'] and pipeline_scp_price > corrected_scp * 1.5:
        result['verdict'] = 'wrong_parallel_match'
    else:
        result['verdict'] = 'not_profitable'

    return result


if __name__ == "__main__":
    import time

    tests = [
        {
            'desc': 'Ohtani #200 (pipeline: Blue Rainbow $193, CE: Green Rainbow Foil $45, eBay: $59.99)',
            'player': 'Shohei Ohtani', 'year': 2026, 'number': '200',
            'buy': 59.99, 'pipe_scp': 193.58, 'pipe_parallel': 'Blue Rainbow',
            'ce_variant': 'Green Rainbow Foil', 'ce_card': 'Shohei Ohtani - Green Rainbow Foil', 'ce_price': 45.0,
        },
        {
            'desc': 'Nolan Ryan #352 (pipeline: Red Refractor $199, CE: Red Atomic $60, eBay: $60)',
            'player': 'Nolan Ryan', 'year': 2022, 'number': '352',
            'buy': 60.0, 'pipe_scp': 199.0, 'pipe_parallel': 'Red Refractor',
            'ce_variant': 'Red Atomic Refractor', 'ce_card': 'Nolan Ryan Red Atomic Refractor', 'ce_price': 60.0,
        },
        {
            'desc': 'Ohtani Heritage #290 (pipeline: Dark Yellow $194, CE: Base $0.90, eBay: $62.50)',
            'player': 'Shohei Ohtani', 'year': 2026, 'number': '290',
            'buy': 62.50, 'pipe_scp': 194.0, 'pipe_parallel': 'Dark Yellow Bordered',
            'ce_variant': 'Base', 'ce_card': 'Shohei Ohtani - DH-P NL All-Stars', 'ce_price': 0.90,
        },
    ]

    for t in tests:
        print(f"=== {t['desc']} ===")
        result = full_variant_correction(
            player_name=t['player'], card_year=t['year'], card_number=t['number'],
            buy_price=t['buy'], pipeline_scp_price=t['pipe_scp'],
            pipeline_parallel=t['pipe_parallel'],
            ce_variant=t['ce_variant'], ce_card_name=t['ce_card'], ce_price=t['ce_price'],
        )
        calc = result['calculation']
        print(f"  Verdict: {result['verdict']}")
        print(f"  Reference: ${calc['reference_price']:.2f} ({calc['price_source']})")
        print(f"  Profit: ${calc['corrected_profit']:.2f} | Confidence: {calc.get('confidence', 'n/a')}")
        if 'sold_comps_median' in result:
            print(f"  130point: ${result['sold_comps_median']:.2f} ({result['sold_comps_count']} sales)")
        if 'scp_correction' in result:
            sc = result['scp_correction']
            print(f"  SCP corrected: [{sc['parallel']}] ${sc['scp_price']:.2f} (score {sc['match_score']})")
        print()
        time.sleep(2)
