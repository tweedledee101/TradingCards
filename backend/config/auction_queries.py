"""
Browse search strings for ``find_auction_opportunities`` (auction-only, category 261328 elsewhere).

Split out so we can tune **coverage vs API budget** without editing the main script.
Product-line queries target high-listing-volume product words (e.g. Topps Chrome) that
generic ``baseball card /99`` strings often miss.
"""

from __future__ import annotations

# Parallel / attribute / premium-product queries (sport-generic phrasing + “baseball”).
BASEBALL_VALUE_QUERIES_CORE: list[str] = [
    'baseball card /25',
    'baseball card /50',
    'baseball card /75',
    'baseball card /99',
    'baseball card /150',
    'baseball card /199',
    'baseball card /250',
    'baseball card /299',
    'baseball card autograph numbered',
    'baseball card auto rookie',
    'baseball card on card auto',
    'baseball card refractor numbered',
    'baseball card gold refractor',
    'baseball card sapphire',
    'baseball card superfractor',
    'baseball rookie card auto',
    'baseball 1st bowman chrome auto',
    'baseball bowman chrome refractor',
    'baseball card patch relic numbered',
    'baseball card game used auto',
    'topps tier one baseball',
    'topps tribute baseball',
    'topps museum collection baseball',
    'topps luminaries baseball',
    'topps inception baseball auto',
    'bowman sterling baseball auto',
    'topps gold label baseball',
    'panini national treasures baseball',
    'panini immaculate baseball',
    'panini flawless baseball',
]

# One expansion per (template × year). Keep templates short for Browse ``q``.
_BASEBALL_PRODUCT_LINE_TEMPLATES: list[str] = [
    '{y} Topps Chrome baseball',
    '{y} Topps Series 1 baseball',
    '{y} Topps Update baseball',
    '{y} Bowman baseball',
    '{y} Bowman Chrome baseball',
    '{y} Topps Stadium Club baseball',
    '{y} Topps Finest baseball',
    '{y} Topps Allen Ginter baseball',
]


def baseball_product_line_queries(years: list[int]) -> list[str]:
    """e.g. 2025 + Topps Chrome — surfaces huge live populations generic queries skip."""
    ys = sorted({int(y) for y in years if y is not None})
    out: list[str] = []
    for y in ys:
        for t in _BASEBALL_PRODUCT_LINE_TEMPLATES:
            out.append(t.format(y=y))
    return out


def build_baseball_value_queries(
    years: list[int],
    *,
    include_product_lines: bool = True,
    product_line_year_cap: int | None = 3,
) -> tuple[list[str], dict]:
    """
    Returns (queries, meta).

    ``product_line_year_cap``: use at most this many **latest** years from ``years``
    for product-line expansion (limits extra Browse calls). None = all years.
    """
    meta: dict = {
        'product_lines': False,
        'product_line_years_used': [],
        'parallel_queries': len(BASEBALL_VALUE_QUERIES_CORE),
    }
    out: list[str] = []

    if include_product_lines and years:
        ys = sorted({int(y) for y in years if y is not None})
        if product_line_year_cap is not None and len(ys) > product_line_year_cap:
            ys = ys[-product_line_year_cap:]
        meta['product_lines'] = True
        meta['product_line_years_used'] = list(ys)
        out.extend(baseball_product_line_queries(ys))

    out.extend(BASEBALL_VALUE_QUERIES_CORE)
    meta['total_value_queries'] = len(out)
    return out, meta
