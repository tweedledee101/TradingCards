#!/usr/bin/env python3
"""Final validation: simulate actual pipeline with cheapest-match + graded filter."""
import sys, os, json, re
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

# Also get old DB results for comparison
old_opps = db.execute(text(
    "SELECT DISTINCT ON (ebay_item_id) buy_price, scp_price, ebay_item_id, player_name, card_year, card_number "
    "FROM opportunities ORDER BY ebay_item_id, profit DESC"
)).fetchall()
old_total = len(old_opps)
old_real = 0
for o in old_opps:
    vs = card_variants.get((o.player_name, o.card_year, o.card_number), [])
    if vs:
        closest = min(vs, key=lambda v: abs(v['price'] - float(o.buy_price)))
        if closest['price'] - float(o.buy_price) - float(o.buy_price) * FEE >= MIN_PROFIT:
            old_real += 1

seen = set(); total = 0; real = 0

for cr in cache_rows:
    results = cr.results
    if isinstance(results, str): results = json.loads(results)
    if not results: continue
    for listing in results:
        title = listing.get('title', ''); tl = title.lower()
        price = float(listing.get('price', 0) or 0)
        iid = listing.get('ebay_item_id', '')
        if not iid or iid in seen or price <= 0 or price > 200: continue
        if any(j in tl for j in JUNK): continue
        # GRADED FILTER
        if any(g in tl for g in GRADED): continue

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

        # ANY keyword match (same as current pipeline)
        matching = []
        for v in vs:
            if v['parallel'] == 'Base': continue
            if v['keywords'] and any(kw in tl for kw in v['keywords'] if len(kw) >= 3):
                matching.append(v)
        if not matching: continue

        # CHEAPEST matching variant = conservative SCP price
        cheapest = min(matching, key=lambda v: v['price'])
        effective_scp = cheapest['price']

        profit = effective_scp - price - (price * FEE)
        roi = (profit / price * 100) if price > 0 else 0
        if profit < MIN_PROFIT or roi < MIN_ROI: continue

        # Sanity check: effective_scp / closest ratio
        if len(vs) >= 2:
            closest = min(vs, key=lambda v: abs(v['price'] - price))
            pvc = effective_scp / max(closest['price'], 1)
            if pvc > 3.0: continue

        seen.add(iid); total += 1

        # Validate: is it real?
        closest = min(vs, key=lambda v: abs(v['price'] - price))
        rp = closest['price'] - price - (price * FEE)
        if rp >= MIN_PROFIT: real += 1

acc = real / max(total, 1) * 100
old_acc = old_real / max(old_total, 1) * 100

print(f"{'=' * 60}")
print(f"FINAL VALIDATION")
print(f"{'=' * 60}")
print(f"OLD (today DB):  {old_real:4d} real / {old_total:5d} total = {old_acc:.1f}%")
print(f"NEW (simulated): {real:4d} real / {total:5d} total = {acc:.1f}%")
print(f"")
print(f"Real opps change:  {old_real} -> {real} ({'+' if real > old_real else ''}{real - old_real})")
print(f"Accuracy change:   {old_acc:.1f}% -> {acc:.1f}%")
print(f"False positives:   {old_total - old_real} -> {total - real} ({(total-real)-(old_total-old_real):+d})")
print(f"")

more_real = real >= old_real * 1.10
more_accurate = acc >= old_acc + 10
print(f"10%+ more real opps:  {'PASS' if more_real else 'FAIL'} ({real} vs {int(old_real * 1.10)} needed)")
print(f"10+ pts more accurate: {'PASS' if more_accurate else 'FAIL'} ({acc:.1f}% vs {old_acc + 10:.1f}% needed)")
print(f"")
print(f"SHIP: {'YES' if more_real and more_accurate else 'NO'}")
print(f"{'=' * 60}")

db.close()
