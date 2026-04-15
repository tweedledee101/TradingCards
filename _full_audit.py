#!/usr/bin/env python3
"""Full audit: for every opportunity, find the SCP variant closest to the eBay buy price.
If the pipeline's SCP price is far from the closest variant, the parallel match is wrong."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.utils.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

opps = db.execute(text("""
    SELECT id, player_name, card_year, card_number, parallel,
        buy_price, scp_price, profit, listing_type, ebay_title
    FROM opportunities ORDER BY profit DESC
""")).fetchall()

print(f"Auditing {len(opps)} opportunities")
print("=" * 80)

real_opps = []
false_positives = []
no_scp_data = []
grade_suspect = []

GRADED_KEYWORDS = ['psa', 'bgs', 'sgc', 'cgc', 'gem mint', 'mint 10', 'mint 9',
                   'graded', 'fcgs', 'grade 10', 'grade 9']

for opp in opps:
    buy = float(opp.buy_price)
    scp = float(opp.scp_price)
    profit = float(opp.profit)
    title = (opp.ebay_title or "").lower()
    parallel = opp.parallel or "Base"

    # Check if graded
    is_graded = any(kw in title for kw in GRADED_KEYWORDS)

    # Get all SCP variants for this card
    scp_rows = db.execute(text(
        "SELECT variants FROM scp_cache WHERE player_name ILIKE :p AND card_year = :y AND card_number ILIKE :n"
    ), {"p": opp.player_name, "y": opp.card_year, "n": opp.card_number}).fetchall()

    all_variants = []
    for row in scp_rows:
        variants = row[0]
        if isinstance(variants, str):
            variants = json.loads(variants)
        if isinstance(variants, list):
            for v in variants:
                price = v.get('ungraded') or 0
                if price and float(price) > 0:
                    all_variants.append({
                        'parallel': v.get('parallel', 'Base'),
                        'price': float(price),
                    })

    if not all_variants:
        no_scp_data.append(opp)
        continue

    # Find closest variant to buy price
    closest = min(all_variants, key=lambda v: abs(v['price'] - buy))
    closest_price = closest['price']

    # Find the pipeline's matched variant
    pipeline_match = None
    for v in all_variants:
        if abs(v['price'] - scp) < 1:
            pipeline_match = v
            break

    # Is the pipeline's SCP price realistic?
    # If closest variant to buy price is within 30% of buy, the card is priced at market
    # If pipeline SCP is >2x the closest variant, pipeline matched wrong parallel
    if closest_price > 0:
        pipeline_ratio = scp / closest_price
    else:
        pipeline_ratio = 999

    # Recalculate profit with closest variant price
    real_profit = closest_price - buy - (buy * 0.13)

    entry = {
        'id': opp.id,
        'player': opp.player_name,
        'year': opp.card_year,
        'number': opp.card_number,
        'parallel_pipeline': parallel,
        'parallel_closest': closest['parallel'],
        'buy': buy,
        'scp_pipeline': scp,
        'scp_closest': closest_price,
        'profit_claimed': profit,
        'profit_real': real_profit,
        'pipeline_ratio': pipeline_ratio,
        'is_graded': is_graded,
        'listing_type': opp.listing_type,
    }

    if is_graded:
        grade_suspect.append(entry)
    elif pipeline_ratio > 2.0 and real_profit < 10:
        false_positives.append(entry)
    elif real_profit >= 10:
        real_opps.append(entry)
    else:
        false_positives.append(entry)

db.close()

# Summary
total = len(opps)
print(f"\nTotal opportunities: {total}")
print(f"No SCP data:        {len(no_scp_data)}")
print(f"Grade suspect:      {len(grade_suspect)} (graded card vs ungraded SCP)")
print(f"False positives:    {len(false_positives)} (wrong parallel match)")
print(f"REAL opportunities: {len(real_opps)} (profit >= $10 at closest variant price)")
print(f"\nAccuracy: {len(real_opps)}/{total} = {len(real_opps)/total*100:.1f}%")

if real_opps:
    real_opps.sort(key=lambda x: -x['profit_real'])
    print(f"\n{'=' * 80}")
    print(f"TOP REAL OPPORTUNITIES (profit recalculated with closest SCP variant):")
    print(f"{'=' * 80}")
    for r in real_opps[:20]:
        print(f"  {r['player']} {r['year']} #{r['number']} [{r['parallel_closest']}]")
        print(f"    Buy ${r['buy']:.2f} | Real SCP ${r['scp_closest']:.2f} | Real Profit ${r['profit_real']:.2f}")
        print(f"    Pipeline said: [{r['parallel_pipeline']}] ${r['scp_pipeline']:.2f} -> ${r['profit_claimed']:.2f}")
        print()

print(f"\n{'=' * 80}")
print(f"FALSE POSITIVE BREAKDOWN:")
fp_by_ratio = {}
for fp in false_positives:
    bucket = "2-3x" if fp['pipeline_ratio'] < 3 else "3-5x" if fp['pipeline_ratio'] < 5 else "5x+"
    fp_by_ratio[bucket] = fp_by_ratio.get(bucket, 0) + 1
for bucket, cnt in sorted(fp_by_ratio.items()):
    print(f"  Pipeline SCP {bucket} of real price: {cnt}")

if grade_suspect:
    print(f"\nGRADE SUSPECTS (graded listings vs ungraded SCP):")
    for g in grade_suspect[:5]:
        print(f"  {g['player']} {g['year']} #{g['number']} -- Buy ${g['buy']:.2f}, SCP ${g['scp_pipeline']:.2f}")
