#!/usr/bin/env python3
"""Hypothesis 2: Use pipeline match, but reject when hybrid disagrees and is closer to buy price.

This should keep the 60.8% correct identifications from Method A while catching
the 39.2% wrong ones by checking if Method C found a better match.
"""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.utils.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

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
MIN_PROFIT = 10.0


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


total = 0
real_opps = 0
false_pos = 0
rejected_correctly = 0
rejected_wrongly = 0
no_data = 0

real_list = []

for opp in opps:
    buy = float(opp.buy_price)
    scp = float(opp.scp_price)
    profit = float(opp.profit)
    title = (opp.ebay_title or "").lower()
    lt = opp.listing_type

    if any(g in title for g in GRADED):
        continue

    variants = get_variants(db, opp.player_name, opp.card_year, opp.card_number)
    if len(variants) < 2:
        no_data += 1
        continue

    total += 1

    # Pipeline's match
    pipeline_price = scp

    # Hybrid match: all keywords in title + closest price
    title_words = set(re.split(r'[^a-zA-Z0-9]+', title))
    full_matches = [v for v in variants if v['keywords'] and all(kw in title_words or kw in title for kw in v['keywords'])]

    if full_matches:
        hybrid = min(full_matches, key=lambda v: abs(v['price'] - buy))
    else:
        hybrid = min(variants, key=lambda v: abs(v['price'] - buy))

    hybrid_price = hybrid['price']

    # Decision: is the pipeline's match trustworthy?
    # If hybrid found a different variant AND hybrid's price is much closer to buy price,
    # the pipeline probably matched wrong.
    pipeline_gap = abs(pipeline_price - buy)
    hybrid_gap = abs(hybrid_price - buy)

    # For BIN: if hybrid price is closer to buy AND pipeline is >1.5x hybrid, reject pipeline
    if lt == 'buy_it_now' and hybrid_gap < pipeline_gap and pipeline_price > hybrid_price * 1.5:
        # Pipeline match is suspicious -- use hybrid price for profit calc
        corrected_profit = hybrid_price - buy - (buy * FEE)
        if corrected_profit >= MIN_PROFIT:
            real_opps += 1
            real_list.append({
                'player': opp.player_name, 'year': opp.card_year, 'number': opp.card_number,
                'buy': buy, 'hybrid_parallel': hybrid['parallel'], 'hybrid_price': hybrid_price,
                'profit': round(corrected_profit, 2), 'title': opp.ebay_title[:75],
                'type': lt,
            })
        else:
            rejected_correctly += 1
    # For auctions: can't use price proximity (bid != value), trust keyword match more
    elif lt == 'auction':
        if full_matches:
            best_match = max(full_matches, key=lambda v: v['price'])
            corrected_profit = best_match['price'] - buy - (buy * FEE)
            if corrected_profit >= MIN_PROFIT:
                real_opps += 1
                real_list.append({
                    'player': opp.player_name, 'year': opp.card_year, 'number': opp.card_number,
                    'buy': buy, 'hybrid_parallel': best_match['parallel'], 'hybrid_price': best_match['price'],
                    'profit': round(corrected_profit, 2), 'title': opp.ebay_title[:75],
                    'type': lt,
                })
            else:
                rejected_correctly += 1
        else:
            # No keyword match for auction -- can't identify, skip
            rejected_correctly += 1
    else:
        # Pipeline and hybrid agree, or pipeline is cheaper -- trust pipeline
        if profit >= MIN_PROFIT:
            real_opps += 1
            real_list.append({
                'player': opp.player_name, 'year': opp.card_year, 'number': opp.card_number,
                'buy': buy, 'hybrid_parallel': opp.pipeline_parallel, 'hybrid_price': pipeline_price,
                'profit': round(profit, 2), 'title': opp.ebay_title[:75],
                'type': lt,
            })
        else:
            false_pos += 1

print(f"Combined method results:")
print(f"  Total tested: {total} (skipped {no_data} no data)")
print(f"  Opportunities found: {real_opps}")
print(f"  Rejected (no profit after correction): {rejected_correctly}")
print(f"  BIN vs Auction breakdown:")

bin_opps = [r for r in real_list if r['type'] == 'buy_it_now']
auc_opps = [r for r in real_list if r['type'] == 'auction']
print(f"    BIN: {len(bin_opps)}")
print(f"    Auction: {len(auc_opps)}")

if real_list:
    real_list.sort(key=lambda x: -x['profit'])
    print(f"\nTop opportunities:")
    for r in real_list[:15]:
        tag = 'AUC' if r['type'] == 'auction' else 'BIN'
        print(f"  [{tag}] {r['player']} {r['year']} #{r['number']} [{r['hybrid_parallel']}]")
        print(f"       Buy ${r['buy']:.2f} | SCP ${r['hybrid_price']:.2f} | Profit ${r['profit']:.2f}")
        print(f"       {r['title']}")

db.close()
