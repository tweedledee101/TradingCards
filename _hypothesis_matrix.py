#!/usr/bin/env python3
"""Comprehensive hypothesis testing: find the best filtering strategy.

Tests multiple approaches against 2,889 cached eBay searches to find
the combination that maximizes REAL opportunities while minimizing false positives.

Each hypothesis is tested independently and results compared.
"""
import sys, os, json, re
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.utils.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

FEE = 0.13
MIN_PROFIT = 10.0
MIN_ROI = 20.0
MAX_BUDGET = 200.0

GRADED = ['psa ', 'bgs ', 'sgc ', 'cgc ', 'fcgs ', 'gem mint',
          'mint 10', 'mint 9', ' graded ', 'psa10', 'psa 10',
          'bgs 10', 'sgc 10', 'cgc 10', 'grade 10', 'grade 9']
JUNK = ['you pick', 'pick your', 'complete your set', 'pick a card',
        'lot of', 'mystery', 'repack', 'break', 'digital', 'bunt',
        'replica', 'reprint', 'project 2020', 'custom card', 'aceo']


def vkw(parallel):
    return set(w.lower() for w in re.split(r'[^a-zA-Z0-9]+', parallel) if len(w) >= 3)


# Load data
players = [
    "Mike Trout","Juan Soto","Aaron Judge","Bobby Witt Jr","Fernando Tatis Jr",
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
    "Coby Mayo","Brooks Lee","Masyn Winn",
]

card_variants = {}
for player in players:
    rows = db.execute(text(
        "SELECT player_name, card_year, card_number, variants FROM scp_cache WHERE player_name ILIKE :p"
    ), {"p": player}).fetchall()
    for row in rows:
        if ',' in (row.player_name or ''):
            continue
        v = row.variants
        if isinstance(v, str): v = json.loads(v)
        if not isinstance(v, list): continue
        key = (player, row.card_year, row.card_number)
        if key not in card_variants:
            card_variants[key] = []
        for x in v:
            p = x.get('ungraded') or 0
            if p and 5 <= float(p) <= 1000:
                par = x.get('parallel', 'Base')
                card_variants[key].append({
                    'parallel': par, 'price': float(p), 'keywords': vkw(par),
                })

# Load cached listings
cache_rows = db.execute(text("SELECT search_query, results FROM ebay_search_cache")).fetchall()

# Build flat list of (listing, matched_card_key, variants)
all_listings = []
for cr in cache_rows:
    results = cr.results
    if isinstance(results, str): results = json.loads(results)
    if not results: continue
    for listing in results:
        title = listing.get('title', '')
        tl = title.lower()
        price = float(listing.get('price', 0) or 0)
        lt = listing.get('listing_type', 'buy_it_now')
        iid = listing.get('ebay_item_id', '')
        if price <= 0 or price > MAX_BUDGET: continue
        if any(j in tl for j in JUNK): continue

        for (player, year, number), variants in card_variants.items():
            if not variants: continue
            pl = player.lower()
            if pl.split()[0] not in tl: continue
            if str(year) not in title: continue
            if number:
                nc = str(number).replace('#','').strip()
                if nc and (f'#{nc}' in title or f'# {nc}' in title or nc in tl):
                    all_listings.append({
                        'title': title, 'tl': tl, 'price': price, 'lt': lt,
                        'iid': iid, 'player': player, 'year': year, 'number': number,
                        'variants': variants,
                    })
                    break

print(f"Total matched listings: {len(all_listings)}")


def is_real(listing, scp_price):
    """Check if opportunity is real: closest variant to buy price still shows profit."""
    variants = listing['variants']
    closest = min(variants, key=lambda v: abs(v['price'] - listing['price']))
    real_profit = closest['price'] - listing['price'] - (listing['price'] * FEE)
    return real_profit >= MIN_PROFIT


def run_hypothesis(name, filter_fn):
    """Run a hypothesis: apply filter_fn to each listing, count results."""
    seen = set()
    raw = 0
    real = 0
    for L in all_listings:
        result = filter_fn(L)
        if result is None:
            continue
        scp_price, parallel = result
        profit = scp_price - L['price'] - (L['price'] * FEE)
        if profit < MIN_PROFIT or (profit / L['price'] * 100) < MIN_ROI:
            continue
        if L['iid'] in seen:
            continue
        seen.add(L['iid'])
        raw += 1
        if is_real(L, scp_price):
            real += 1
    acc = real / max(raw, 1) * 100
    print(f"  {name:50s} | raw={raw:5d} | real={real:4d} | acc={acc:5.1f}%")
    return raw, real, acc


print(f"\n{'=' * 80}")
print(f"HYPOTHESIS TESTS")
print(f"{'=' * 80}\n")

# H0: Baseline (any keyword match, no graded filter)
def h0(L):
    for v in L['variants']:
        if v['parallel'] != 'Base':
            if not v['keywords'] or not any(kw in L['tl'] for kw in v['keywords']):
                continue
        profit = v['price'] - L['price'] - (L['price'] * FEE)
        if profit >= MIN_PROFIT:
            return v['price'], v['parallel']
    return None

# H1: + graded filter
def h1(L):
    if any(g in L['tl'] for g in GRADED): return None
    return h0(L)

# H2: + ALL keywords (not any)
def h2(L):
    if any(g in L['tl'] for g in GRADED): return None
    tw = set(re.split(r'[^a-zA-Z0-9]+', L['tl']))
    for v in L['variants']:
        if v['parallel'] != 'Base':
            if not v['keywords'] or not all(kw in tw or kw in L['tl'] for kw in v['keywords']):
                continue
        profit = v['price'] - L['price'] - (L['price'] * FEE)
        if profit >= MIN_PROFIT:
            return v['price'], v['parallel']
    return None

# H3: graded filter + sanity check (reject when closest variant is <50% of matched)
def h3(L):
    if any(g in L['tl'] for g in GRADED): return None
    for v in L['variants']:
        if v['parallel'] != 'Base':
            if not v['keywords'] or not any(kw in L['tl'] for kw in v['keywords']):
                continue
        profit = v['price'] - L['price'] - (L['price'] * FEE)
        if profit >= MIN_PROFIT:
            # Sanity: is there a cheaper variant closer to buy price?
            closest = min(L['variants'], key=lambda x: abs(x['price'] - L['price']))
            if closest['price'] < v['price'] * 0.5 and abs(closest['price'] - L['price']) < L['price'] * 0.5:
                continue  # wrong parallel
            return v['price'], v['parallel']
    return None

# H4: graded + sanity with looser threshold
def h4(L):
    if any(g in L['tl'] for g in GRADED): return None
    for v in L['variants']:
        if v['parallel'] != 'Base':
            if not v['keywords'] or not any(kw in L['tl'] for kw in v['keywords']):
                continue
        profit = v['price'] - L['price'] - (L['price'] * FEE)
        if profit >= MIN_PROFIT:
            closest = min(L['variants'], key=lambda x: abs(x['price'] - L['price']))
            if closest['price'] < v['price'] * 0.6 and abs(closest['price'] - L['price']) < L['price'] * 0.4:
                continue
            return v['price'], v['parallel']
    return None

# H5: graded + for BIN only: reject if buy < 40% of SCP (too cheap = wrong card)
def h5(L):
    if any(g in L['tl'] for g in GRADED): return None
    for v in L['variants']:
        if v['parallel'] != 'Base':
            if not v['keywords'] or not any(kw in L['tl'] for kw in v['keywords']):
                continue
        profit = v['price'] - L['price'] - (L['price'] * FEE)
        if profit >= MIN_PROFIT:
            if L['lt'] == 'buy_it_now' and L['price'] < v['price'] * 0.40:
                continue  # BIN too cheap = probably wrong card
            return v['price'], v['parallel']
    return None

# H6: graded + BIN floor 40% + sanity check
def h6(L):
    if any(g in L['tl'] for g in GRADED): return None
    for v in L['variants']:
        if v['parallel'] != 'Base':
            if not v['keywords'] or not any(kw in L['tl'] for kw in v['keywords']):
                continue
        profit = v['price'] - L['price'] - (L['price'] * FEE)
        if profit >= MIN_PROFIT:
            if L['lt'] == 'buy_it_now' and L['price'] < v['price'] * 0.40:
                continue
            closest = min(L['variants'], key=lambda x: abs(x['price'] - L['price']))
            if closest['price'] < v['price'] * 0.5 and abs(closest['price'] - L['price']) < L['price'] * 0.5:
                continue
            return v['price'], v['parallel']
    return None

# H7: graded + BIN floor 50% (tighter) + sanity
def h7(L):
    if any(g in L['tl'] for g in GRADED): return None
    for v in L['variants']:
        if v['parallel'] != 'Base':
            if not v['keywords'] or not any(kw in L['tl'] for kw in v['keywords']):
                continue
        profit = v['price'] - L['price'] - (L['price'] * FEE)
        if profit >= MIN_PROFIT:
            if L['lt'] == 'buy_it_now' and L['price'] < v['price'] * 0.50:
                continue
            closest = min(L['variants'], key=lambda x: abs(x['price'] - L['price']))
            if closest['price'] < v['price'] * 0.5 and abs(closest['price'] - L['price']) < L['price'] * 0.5:
                continue
            return v['price'], v['parallel']
    return None

# H8: ALL keywords + graded + sanity (the combined approach but keeping more)
def h8(L):
    if any(g in L['tl'] for g in GRADED): return None
    tw = set(re.split(r'[^a-zA-Z0-9]+', L['tl']))
    # Try ALL keywords first
    for v in L['variants']:
        if v['parallel'] != 'Base':
            if not v['keywords'] or not all(kw in tw or kw in L['tl'] for kw in v['keywords']):
                continue
        profit = v['price'] - L['price'] - (L['price'] * FEE)
        if profit >= MIN_PROFIT:
            return v['price'], v['parallel']
    # Fallback: any keyword but with sanity check
    for v in L['variants']:
        if v['parallel'] != 'Base':
            if not v['keywords'] or not any(kw in L['tl'] for kw in v['keywords']):
                continue
        profit = v['price'] - L['price'] - (L['price'] * FEE)
        if profit >= MIN_PROFIT:
            closest = min(L['variants'], key=lambda x: abs(x['price'] - L['price']))
            if closest['price'] < v['price'] * 0.5 and abs(closest['price'] - L['price']) < L['price'] * 0.5:
                continue
            return v['price'], v['parallel']
    return None

# H9: graded + BIN floor 40% + auction gets looser matching (any keyword ok for auctions)
def h9(L):
    if any(g in L['tl'] for g in GRADED): return None
    tw = set(re.split(r'[^a-zA-Z0-9]+', L['tl']))
    for v in L['variants']:
        if v['parallel'] != 'Base':
            if L['lt'] == 'buy_it_now':
                # BIN: require ALL keywords
                if not v['keywords'] or not all(kw in tw or kw in L['tl'] for kw in v['keywords']):
                    continue
            else:
                # Auction: any keyword ok
                if not v['keywords'] or not any(kw in L['tl'] for kw in v['keywords']):
                    continue
        profit = v['price'] - L['price'] - (L['price'] * FEE)
        if profit >= MIN_PROFIT:
            if L['lt'] == 'buy_it_now' and L['price'] < v['price'] * 0.40:
                continue
            return v['price'], v['parallel']
    return None

# H10: H9 + sanity check on BIN only (auctions skip sanity since bid != value)
def h10(L):
    if any(g in L['tl'] for g in GRADED): return None
    tw = set(re.split(r'[^a-zA-Z0-9]+', L['tl']))
    for v in L['variants']:
        if v['parallel'] != 'Base':
            if L['lt'] == 'buy_it_now':
                if not v['keywords'] or not all(kw in tw or kw in L['tl'] for kw in v['keywords']):
                    continue
            else:
                if not v['keywords'] or not any(kw in L['tl'] for kw in v['keywords']):
                    continue
        profit = v['price'] - L['price'] - (L['price'] * FEE)
        if profit >= MIN_PROFIT:
            if L['lt'] == 'buy_it_now':
                if L['price'] < v['price'] * 0.40:
                    continue
                closest = min(L['variants'], key=lambda x: abs(x['price'] - L['price']))
                if closest['price'] < v['price'] * 0.5 and abs(closest['price'] - L['price']) < L['price'] * 0.5:
                    continue
            return v['price'], v['parallel']
    return None

results = []
for name, fn in [
    ("H0: baseline (any kw, no filters)", h0),
    ("H1: + graded filter", h1),
    ("H2: + ALL keywords", h2),
    ("H3: graded + sanity check", h3),
    ("H4: graded + looser sanity", h4),
    ("H5: graded + BIN floor 40%", h5),
    ("H6: graded + BIN floor 40% + sanity", h6),
    ("H7: graded + BIN floor 50% + sanity", h7),
    ("H8: ALL kw first, fallback any+sanity", h8),
    ("H9: BIN=ALL kw, auction=any kw, BIN floor", h9),
    ("H10: H9 + BIN sanity (auction no sanity)", h10),
]:
    raw, real, acc = run_hypothesis(name, fn)
    results.append((name, raw, real, acc))

print(f"\n{'=' * 80}")
print(f"SUMMARY (sorted by real opportunities found)")
print(f"{'=' * 80}")
results.sort(key=lambda x: (-x[2], -x[3]))
for name, raw, real, acc in results:
    bar = '#' * int(acc / 2)
    print(f"  {real:4d} real / {raw:5d} raw ({acc:5.1f}%) | {name}")

db.close()
