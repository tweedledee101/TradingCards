#!/usr/bin/env python3
"""Hypothesis test: price-proximity vs keyword matching for SCP variant identification.

For each opportunity, we have:
- eBay title (contains the actual parallel name)
- Buy price
- All SCP variants for that card#

Method A (current): match by ANY keyword overlap with pipeline's chosen parallel
Method B (proposed): match to SCP variant with price closest to buy price
Method C (hybrid): match to SCP variant where ALL keywords match title AND price is closest

Ground truth: extract the actual parallel from the eBay title by checking which
SCP variant name appears most completely in the title.
"""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.utils.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

opps = db.execute(text("""
    SELECT DISTINCT ON (ebay_url)
        player_name, card_year, card_number, parallel as pipeline_parallel,
        buy_price, scp_price, ebay_title, listing_type
    FROM opportunities
    WHERE listing_type = 'buy_it_now'
    ORDER BY ebay_url, profit DESC
""")).fetchall()

GRADED = ['psa ', 'bgs ', 'sgc ', 'cgc ', 'fcgs ', 'gem mint',
          'mint 10', 'mint 9', ' graded ', 'psa10', 'psa 10']


def variant_keywords(parallel):
    return set(w.lower() for w in re.split(r'[^a-zA-Z0-9]+', parallel) if len(w) >= 3)


def title_match_score(title_lower, variant_kws):
    """What fraction of variant keywords appear in the title?"""
    if not variant_kws:
        return 0
    return sum(1 for kw in variant_kws if kw in title_lower) / len(variant_kws)


correct_a = 0  # current method (pipeline's parallel)
correct_b = 0  # price proximity
correct_c = 0  # hybrid (all keywords + closest price)
correct_ground = 0  # ground truth identifiable
total = 0
skipped = 0

for opp in opps:
    buy = float(opp.buy_price)
    title = (opp.ebay_title or "").lower()
    pipeline_par = opp.pipeline_parallel or "Base"

    if any(g in title for g in GRADED):
        skipped += 1
        continue

    rows = db.execute(text(
        "SELECT variants FROM scp_cache WHERE player_name ILIKE :p AND card_year = :y AND card_number ILIKE :n"
    ), {"p": opp.player_name, "y": opp.card_year, "n": opp.card_number}).fetchall()

    variants = []
    for row in rows:
        v = row[0]
        if isinstance(v, str):
            v = json.loads(v)
        if isinstance(v, list):
            for x in v:
                p = x.get('ungraded') or 0
                if p and float(p) > 0:
                    par = x.get('parallel', 'Base')
                    variants.append({
                        'parallel': par,
                        'price': float(p),
                        'keywords': variant_keywords(par),
                    })

    if len(variants) < 2:
        skipped += 1
        continue

    total += 1

    # Ground truth: which SCP variant name best matches the eBay title?
    best_ground_score = 0
    ground_truth = None
    for v in variants:
        score = title_match_score(title, v['keywords'])
        # Bonus for price being in the right ballpark (within 2x of buy)
        if v['price'] > 0 and 0.3 <= buy / v['price'] <= 3.0:
            score += 0.1
        if score > best_ground_score:
            best_ground_score = score
            ground_truth = v

    if not ground_truth or best_ground_score < 0.5:
        # Can't determine ground truth
        skipped += 1
        total -= 1
        continue

    correct_ground += 1
    gt_price = ground_truth['price']

    # Method A: pipeline's parallel (current)
    pipeline_match = None
    for v in variants:
        if abs(v['price'] - float(opp.scp_price)) < 1:
            pipeline_match = v
            break
    a_correct = pipeline_match and abs(pipeline_match['price'] - gt_price) < gt_price * 0.2
    if a_correct:
        correct_a += 1

    # Method B: closest price to buy
    price_match = min(variants, key=lambda v: abs(v['price'] - buy))
    b_correct = abs(price_match['price'] - gt_price) < gt_price * 0.2
    if b_correct:
        correct_b += 1

    # Method C: all keywords match + closest price
    full_kw_matches = [v for v in variants if v['keywords'] and all(kw in title for kw in v['keywords'])]
    if full_kw_matches:
        hybrid_match = min(full_kw_matches, key=lambda v: abs(v['price'] - buy))
    else:
        hybrid_match = price_match  # fallback
    c_correct = abs(hybrid_match['price'] - gt_price) < gt_price * 0.2
    if c_correct:
        correct_c += 1

    # Show disagreements
    if not a_correct and (b_correct or c_correct):
        print(f"  {opp.player_name} {opp.card_year} #{opp.card_number}")
        print(f"    Title: {opp.ebay_title[:75]}")
        print(f"    Ground truth: [{ground_truth['parallel']}] ${gt_price:.2f}")
        print(f"    Method A (pipeline): [{pipeline_match['parallel'] if pipeline_match else '?'}] ${float(opp.scp_price):.2f} {'OK' if a_correct else 'WRONG'}")
        print(f"    Method B (price):    [{price_match['parallel']}] ${price_match['price']:.2f} {'OK' if b_correct else 'WRONG'}")
        print(f"    Method C (hybrid):   [{hybrid_match['parallel']}] ${hybrid_match['price']:.2f} {'OK' if c_correct else 'WRONG'}")
        print()

print(f"\n{'=' * 70}")
print(f"RESULTS: {total} BIN listings tested (skipped {skipped} graded/insufficient)")
print(f"  Method A (current pipeline):     {correct_a}/{total} = {correct_a/max(total,1)*100:.1f}%")
print(f"  Method B (price proximity):      {correct_b}/{total} = {correct_b/max(total,1)*100:.1f}%")
print(f"  Method C (all keywords + price): {correct_c}/{total} = {correct_c/max(total,1)*100:.1f}%")
print(f"{'=' * 70}")

db.close()
