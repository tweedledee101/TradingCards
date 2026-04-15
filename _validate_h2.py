#!/usr/bin/env python3
"""Validate hypothesis 2 results: are the 36 opportunities real?"""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.utils.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Rerun the combined method and validate each result
opps = db.execute(text("""
    SELECT DISTINCT ON (ebay_url)
        player_name, card_year, card_number, parallel as pipeline_parallel,
        buy_price, scp_price, profit, ebay_title, listing_type
    FROM opportunities
    ORDER BY ebay_url, profit DESC
""")).fetchall()

GRADED = ['psa ', 'bgs ', 'sgc ', 'cgc ', 'fcgs ', 'gem mint',
          'mint 10', 'mint 9', ' graded ', 'psa10', 'psa 10']
FEE = 0.13


def variant_keywords(parallel):
    return set(w.lower() for w in re.split(r'[^a-zA-Z0-9]+', parallel) if len(w) >= 3)


def get_variants(db, player, year, number):
    rows = db.execute(text(
        "SELECT variants FROM scp_cache WHERE player_name ILIKE :p AND card_year = :y AND card_number ILIKE :n"
    ), {"p": player, "y": year, "n": number}).fetchall()
    out = []
    for row in rows:
        v = row[0]
        if isinstance(v, str): v = json.loads(v)
        if isinstance(v, list):
            for x in v:
                p = x.get('ungraded') or 0
                if p and float(p) > 0:
                    par = x.get('parallel', 'Base')
                    out.append({'parallel': par, 'price': float(p), 'keywords': variant_keywords(par)})
    return out


def title_match_score(title_lower, variant):
    """How well does this variant match the title? 0-1."""
    if not variant['keywords']:
        return 0
    title_words = set(re.split(r'[^a-zA-Z0-9]+', title_lower))
    matched = sum(1 for kw in variant['keywords'] if kw in title_words or kw in title_lower)
    return matched / len(variant['keywords'])


real = 0
false_pos = 0
results = []

for opp in opps:
    buy = float(opp.buy_price)
    scp = float(opp.scp_price)
    title = (opp.ebay_title or "").lower()
    lt = opp.listing_type

    if any(g in title for g in GRADED):
        continue

    variants = get_variants(db, opp.player_name, opp.card_year, opp.card_number)
    if len(variants) < 2:
        continue

    # Combined method logic (same as hypothesis2)
    title_words = set(re.split(r'[^a-zA-Z0-9]+', title))
    full_matches = [v for v in variants if v['keywords'] and all(kw in title_words or kw in title for kw in v['keywords'])]
    if full_matches:
        hybrid = min(full_matches, key=lambda v: abs(v['price'] - buy))
    else:
        hybrid = min(variants, key=lambda v: abs(v['price'] - buy))

    pipeline_gap = abs(scp - buy)
    hybrid_gap = abs(hybrid['price'] - buy)

    # Determine which price to use
    if lt == 'buy_it_now' and hybrid_gap < pipeline_gap and scp > hybrid['price'] * 1.5:
        use_price = hybrid['price']
        use_parallel = hybrid['parallel']
    elif lt == 'auction' and full_matches:
        best = max(full_matches, key=lambda v: v['price'])
        use_price = best['price']
        use_parallel = best['parallel']
    else:
        use_price = scp
        use_parallel = opp.pipeline_parallel

    profit = use_price - buy - (buy * FEE)
    if profit < 10:
        continue

    # VALIDATION: find the BEST title match among all variants (ground truth proxy)
    best_title_match = max(variants, key=lambda v: title_match_score(title, v))
    best_score = title_match_score(title, best_title_match)

    # Is our chosen variant the same as the best title match?
    chosen_score = title_match_score(title, {'keywords': variant_keywords(use_parallel)})
    price_diff = abs(use_price - best_title_match['price'])
    match_correct = price_diff < best_title_match['price'] * 0.25 or chosen_score >= best_score

    # Real profit based on best title match
    real_profit = best_title_match['price'] - buy - (buy * FEE)

    if match_correct and real_profit >= 10:
        real += 1
        verdict = "REAL"
    elif real_profit >= 10:
        real += 1
        verdict = "REAL (different variant but still profitable)"
    else:
        false_pos += 1
        verdict = "FALSE"

    results.append({
        'player': opp.player_name, 'year': opp.card_year, 'number': opp.card_number,
        'buy': buy, 'chosen': use_parallel, 'chosen_price': use_price,
        'best_title': best_title_match['parallel'], 'best_price': best_title_match['price'],
        'profit_claimed': round(profit, 2), 'profit_real': round(real_profit, 2),
        'verdict': verdict, 'type': lt,
    })

total = len(results)
print(f"Validated {total} opportunities from combined method")
print(f"  REAL: {real} ({real/max(total,1)*100:.1f}%)")
print(f"  FALSE: {false_pos} ({false_pos/max(total,1)*100:.1f}%)")
print(f"\nvs baseline: 9/314 = 2.9%")
print(f"vs new filters only: 8/105 = 7.6%")

results.sort(key=lambda x: -x['profit_real'])
print(f"\nReal opportunities:")
for r in [x for x in results if 'REAL' in x['verdict']][:15]:
    tag = 'AUC' if r['type'] == 'auction' else 'BIN'
    print(f"  [{tag}] {r['player']} {r['year']} #{r['number']} [{r['best_title']}]")
    print(f"       Buy ${r['buy']:.2f} | SCP ${r['best_price']:.2f} | Profit ${r['profit_real']:.2f}")

db.close()
