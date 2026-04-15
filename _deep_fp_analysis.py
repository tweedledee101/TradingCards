#!/usr/bin/env python3
"""Deep analysis of false positives that survive cheapest-match + graded + sanity.
Find patterns to eliminate more without losing real opportunities."""
import sys, os, json, re
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.utils.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
FEE = 0.13; MIN_PROFIT = 10.0; MIN_ROI = 20.0
GRADED = ['psa ', 'bgs ', 'sgc ', 'cgc ', 'fcgs ', 'gem mint',
          'mint 10', 'mint 9', ' graded ', 'psa10', 'psa 10',
          'bgs 10', 'sgc 10', 'cgc 10', 'grade 10', 'grade 9']
JUNK = ['you pick', 'pick your', 'complete your set', 'pick a card',
        'lot of', 'mystery', 'repack', 'break', 'digital', 'bunt',
        'replica', 'reprint', 'project 2020', 'custom card', 'aceo']
def vkw(p):
    return set(w.lower() for w in re.split(r'[^a-zA-Z0-9]+', p) if len(w) >= 3)

players = ["Mike Trout","Juan Soto","Aaron Judge","Bobby Witt Jr","Fernando Tatis Jr",
    "Julio Rodriguez","Elly De La Cruz","Ronald Acuna Jr","Shohei Ohtani",
    "Ken Griffey Jr","Mookie Betts","Paul Skenes","Corbin Carroll","Derek Jeter",
    "Adley Rutschman","James Wood","Jackson Chourio","Marcelo Mayer",
    "Gunnar Henderson","Nolan Ryan","Freddie Freeman","Yoshinobu Yamamoto",
    "Jackson Merrill","Dylan Crews","Jasson Dominguez","Corey Seager",
    "Junior Caminero","Cal Ripken Jr","Roman Anthony","Jackson Holliday",
    "Roki Sasaki","Nick Gonzales","Nick Kurtz","David Wright","Trea Turner",
    "Colton Cowser","Jordan Walker","Evan Carter","Ichiro Suzuki",
    "Jac Caglianone","Luisangel Acuna","Mike Piazza","Matt Shaw","Jacob Wilson",
    "Wyatt Langford","Manny Machado","Chipper Jones","Vladimir Guerrero Jr",
    "Charlie Condon","Travis Bazzana","Yordan Alvarez","Drew Gilbert",
    "Frank Thomas","Spencer Strider","Bryce Harper","Kyle Tucker","Oneil Cruz",
    "Coby Mayo","Brooks Lee","Masyn Winn"]

card_variants = {}
for player in players:
    rows = db.execute(text(
        "SELECT player_name, card_year, card_number, variants FROM scp_cache WHERE player_name ILIKE :p"
    ), {"p": player}).fetchall()
    for row in rows:
        if ',' in (row.player_name or ''): continue
        v = row.variants
        if isinstance(v, str): v = json.loads(v)
        if not isinstance(v, list): continue
        key = (player, row.card_year, row.card_number)
        if key not in card_variants: card_variants[key] = []
        for x in v:
            p = x.get('ungraded') or 0
            if p and 5 <= float(p) <= 1000:
                par = x.get('parallel', 'Base')
                card_variants[key].append({'parallel': par, 'price': float(p), 'keywords': list(vkw(par))})

cache_rows = db.execute(text("SELECT search_query, results FROM ebay_search_cache")).fetchall()

reals = []
falses = []

seen = set()
for cr in cache_rows:
    results = cr.results
    if isinstance(results, str): results = json.loads(results)
    if not results: continue
    for listing in results:
        title = listing.get('title', ''); tl = title.lower()
        price = float(listing.get('price', 0) or 0)
        iid = listing.get('ebay_item_id', '')
        if not iid or iid in seen or price <= 0 or price > 200: continue
        if any(j in tl for j in JUNK) or any(g in tl for g in GRADED): continue
        mk = None
        for (pl, yr, num), vs in card_variants.items():
            if not vs or pl.lower().split()[0] not in tl or str(yr) not in title: continue
            if num:
                nc = str(num).replace('#','').strip()
                if nc and (f'#{nc}' in title or f'# {nc}' in title or nc in tl):
                    mk = (pl, yr, num); break
        if not mk: continue
        vs = card_variants[mk]
        if not vs: continue
        tw = set(re.split(r'[^a-zA-Z0-9]+', tl))

        matching = []
        for v in vs:
            if v['parallel'] == 'Base': continue
            if v['keywords'] and any(kw in tl for kw in v['keywords'] if len(kw) >= 3):
                matching.append(v)
        if not matching: continue

        cheapest = min(matching, key=lambda v: v['price'])
        effective_scp = cheapest['price']
        profit = effective_scp - price - (price * FEE)
        roi = (profit / price * 100) if price > 0 else 0
        if profit < MIN_PROFIT or roi < MIN_ROI: continue

        # Sanity check
        closest = min(vs, key=lambda v: abs(v['price'] - price))
        gap = abs(closest['price'] - price) / max(price, 1)
        pvc = effective_scp / max(closest['price'], 1)
        par_kw_count = len(cheapest.get('keywords', []))
        if par_kw_count <= 1:
            tg, tp = 0.85, 1.15
        else:
            tg, tp = 0.75, 1.25
        if gap < tg and pvc > tp: continue

        seen.add(iid)
        rp = closest['price'] - price - (price * FEE)
        is_real = rp >= MIN_PROFIT

        entry = {
            'buy': price, 'effective_scp': effective_scp,
            'closest_price': closest['price'], 'closest_parallel': closest['parallel'],
            'chosen_parallel': cheapest['parallel'],
            'chosen_kw_count': par_kw_count,
            'num_matching': len(matching),
            'num_variants': len(vs),
            'ratio_scp_buy': effective_scp / max(price, 1),
            'ratio_scp_closest': effective_scp / max(closest['price'], 1),
            'profit_claimed': round(profit, 2),
            'profit_real': round(rp, 2),
            'title': title[:80],
        }
        if is_real:
            reals.append(entry)
        else:
            falses.append(entry)

print(f"Real: {len(reals)}, False: {len(falses)}")
print()

# What ratio of effective_scp to closest_price do false positives have?
print("=== effective_scp / closest_price ratio ===")
for label, data in [("REAL", reals), ("FALSE", falses)]:
    ratios = sorted([d['ratio_scp_closest'] for d in data])
    if ratios:
        p25 = ratios[len(ratios)//4]
        p50 = ratios[len(ratios)//2]
        p75 = ratios[3*len(ratios)//4]
        print(f"  {label}: p25={p25:.2f}x p50={p50:.2f}x p75={p75:.2f}x max={ratios[-1]:.2f}x")

print()
print("=== effective_scp / buy_price ratio ===")
for label, data in [("REAL", reals), ("FALSE", falses)]:
    ratios = sorted([d['ratio_scp_buy'] for d in data])
    if ratios:
        p25 = ratios[len(ratios)//4]
        p50 = ratios[len(ratios)//2]
        p75 = ratios[3*len(ratios)//4]
        print(f"  {label}: p25={p25:.2f}x p50={p50:.2f}x p75={p75:.2f}x max={ratios[-1]:.2f}x")

print()
print("=== keyword count of chosen parallel ===")
for label, data in [("REAL", reals), ("FALSE", falses)]:
    c = Counter(d['chosen_kw_count'] for d in data)
    print(f"  {label}: {dict(sorted(c.items()))}")

print()
print("=== number of keyword-matching variants ===")
for label, data in [("REAL", reals), ("FALSE", falses)]:
    c = Counter(d['num_matching'] for d in data)
    top5 = c.most_common(5)
    print(f"  {label}: {dict(top5)}")

# Test: what if we cap the scp/buy ratio?
print()
print("=== FILTER: cap effective_scp / buy ratio ===")
for max_ratio in [2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0, 10.0]:
    fp_killed = sum(1 for f in falses if f['ratio_scp_buy'] > max_ratio)
    real_killed = sum(1 for r in reals if r['ratio_scp_buy'] > max_ratio)
    rem_real = len(reals) - real_killed
    rem_total = (len(reals) + len(falses)) - fp_killed - real_killed
    acc = rem_real / max(rem_total, 1) * 100
    print(f"  scp/buy <= {max_ratio:4.1f}x: kills {fp_killed:3d} FP + {real_killed:2d} real -> {rem_real:3d} real / {rem_total:4d} = {acc:5.1f}%")

# Test: what if we cap effective_scp / closest ratio?
print()
print("=== FILTER: cap effective_scp / closest ratio ===")
for max_ratio in [1.3, 1.5, 1.8, 2.0, 2.5, 3.0, 4.0, 5.0]:
    fp_killed = sum(1 for f in falses if f['ratio_scp_closest'] > max_ratio)
    real_killed = sum(1 for r in reals if r['ratio_scp_closest'] > max_ratio)
    rem_real = len(reals) - real_killed
    rem_total = (len(reals) + len(falses)) - fp_killed - real_killed
    acc = rem_real / max(rem_total, 1) * 100
    print(f"  scp/closest <= {max_ratio:4.1f}x: kills {fp_killed:3d} FP + {real_killed:2d} real -> {rem_real:3d} real / {rem_total:4d} = {acc:5.1f}%")

# Test: what if we require more keyword matches?
print()
print("=== FILTER: require N+ matching variants (more agreement = more confidence) ===")
for min_matches in [1, 2, 3, 5, 8]:
    fp_killed = sum(1 for f in falses if f['num_matching'] < min_matches)
    real_killed = sum(1 for r in reals if r['num_matching'] < min_matches)
    rem_real = len(reals) - real_killed
    rem_total = (len(reals) + len(falses)) - fp_killed - real_killed
    acc = rem_real / max(rem_total, 1) * 100
    print(f"  {min_matches}+ matching variants: kills {fp_killed:3d} FP + {real_killed:2d} real -> {rem_real:3d} real / {rem_total:4d} = {acc:5.1f}%")

# COMBINED: best filters together
print()
print("=== COMBINED FILTERS ===")
for scp_closest_max in [2.0, 2.5, 3.0]:
    for scp_buy_max in [4.0, 5.0, 6.0, 8.0]:
        fp_killed = sum(1 for f in falses if f['ratio_scp_closest'] > scp_closest_max or f['ratio_scp_buy'] > scp_buy_max)
        real_killed = sum(1 for r in reals if r['ratio_scp_closest'] > scp_closest_max or r['ratio_scp_buy'] > scp_buy_max)
        rem_real = len(reals) - real_killed
        rem_total = (len(reals) + len(falses)) - fp_killed - real_killed
        acc = rem_real / max(rem_total, 1) * 100
        if rem_real >= 99 and acc >= 45:
            print(f"  scp/closest<={scp_closest_max} OR scp/buy<={scp_buy_max}: {rem_real} real / {rem_total} = {acc:.1f}% ***")
        elif rem_real >= 99 and acc >= 35:
            print(f"  scp/closest<={scp_closest_max} OR scp/buy<={scp_buy_max}: {rem_real} real / {rem_total} = {acc:.1f}%")

db.close()
