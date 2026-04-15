#!/usr/bin/env python3
"""End-to-end simulation: SCP cache + eBay search cache + combined method.

No API calls. Uses today's cached data to simulate what the pipeline would
produce with the combined matching method.

Runs both the OLD method and NEW method on the same data for comparison.
"""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.utils.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

FEE = 0.13
MIN_PROFIT = 10.0
MIN_ROI = 20.0
MIN_SCP = 5.0
MAX_SCP = 1000.0
MAX_BUDGET = 200.0

GRADED = ['psa ', 'bgs ', 'sgc ', 'cgc ', 'fcgs ', 'gem mint',
          'mint 10', 'mint 9', ' graded ', 'psa10', 'psa 10',
          'bgs 10', 'sgc 10', 'cgc 10']
JUNK = ['you pick', 'pick your', 'complete your set', 'pick a card',
        'lot of', 'mystery', 'repack', 'break', 'digital', 'bunt',
        'replica', 'reprint', 'project 2020', 'custom card', 'aceo']


def variant_keywords(parallel):
    return set(w.lower() for w in re.split(r'[^a-zA-Z0-9]+', parallel) if len(w) >= 3)


def title_match_score(title_lower, kws):
    if not kws: return 0
    return sum(1 for kw in kws if kw in title_lower) / len(kws)


# Load all SCP variations for our 60 players
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

print(f"Loading SCP cache for {len(players)} players...")
# For each player, get all SCP variations grouped by card identity (year + number)
card_variants = {}  # key: (player, year, number) -> list of variants
for player in players:
    rows = db.execute(text(
        "SELECT player_name, card_year, card_number, variants FROM scp_cache WHERE player_name ILIKE :p"
    ), {"p": player}).fetchall()
    for row in rows:
        if ',' in (row.player_name or ''):
            continue  # skip multi-player
        variants = row.variants
        if isinstance(variants, str):
            variants = json.loads(variants)
        if not isinstance(variants, list):
            continue
        key = (player, row.card_year, row.card_number)
        if key not in card_variants:
            card_variants[key] = []
        for v in variants:
            price = v.get('ungraded') or 0
            if price and MIN_SCP <= float(price) <= MAX_SCP:
                par = v.get('parallel', 'Base')
                card_variants[key].append({
                    'parallel': par,
                    'price': float(price),
                    'keywords': variant_keywords(par),
                    'url': v.get('url'),
                })

print(f"Loaded {len(card_variants)} unique card identities with {sum(len(v) for v in card_variants.values())} total variants")

# Load cached eBay search results
print(f"Loading eBay search cache...")
cache_rows = db.execute(text("SELECT search_query, results FROM ebay_search_cache")).fetchall()
print(f"Loaded {len(cache_rows)} cached searches")

# Build a map: for each listing, extract player/year/number from the query
# and match against SCP variants
old_method_opps = []
new_method_opps = []
listings_checked = 0
listings_passed_filters = 0

for cache_row in cache_rows:
    query = cache_row.search_query or ""
    results = cache_row.results
    if isinstance(results, str):
        results = json.loads(results)
    if not results:
        continue

    for listing in results:
        title = listing.get('title', '')
        title_lower = title.lower()
        price = float(listing.get('price', 0) or 0)
        lt = listing.get('listing_type', 'buy_it_now')
        item_id = listing.get('ebay_item_id', '')

        if price <= 0 or price > MAX_BUDGET:
            continue
        if any(j in title_lower for j in JUNK):
            continue
        if any(g in title_lower for g in GRADED):
            continue

        listings_checked += 1

        # Find which card identity this listing belongs to
        # Try to match against our SCP card_variants
        matched_key = None
        for (player, year, number), variants in card_variants.items():
            if not variants:
                continue
            pl = player.lower()
            yr = str(year)
            # Player name in title?
            if pl.split()[0] not in title_lower:
                continue
            # Year in title?
            if yr not in title:
                continue
            # Card number in title?
            if number:
                num_clean = str(number).replace('#', '').strip()
                if num_clean and (f'#{num_clean}' in title or f'# {num_clean}' in title or num_clean in title_lower):
                    matched_key = (player, year, number)
                    break

        if not matched_key:
            continue

        variants = card_variants[matched_key]
        if not variants:
            continue

        listings_passed_filters += 1
        player, year, number = matched_key
        title_words = set(re.split(r'[^a-zA-Z0-9]+', title_lower))

        # === OLD METHOD: for each variant, check if ANY keyword matches ===
        for v in variants:
            if v['parallel'] != 'Base':
                kws = list(v['keywords'])
                if not kws or not any(kw in title_lower for kw in kws):
                    continue
            profit = v['price'] - price - (price * FEE)
            if profit >= MIN_PROFIT and (profit / price * 100) >= MIN_ROI:
                old_method_opps.append({
                    'player': player, 'year': year, 'number': number,
                    'parallel': v['parallel'], 'scp_price': v['price'],
                    'buy': price, 'profit': round(profit, 2), 'type': lt,
                    'title': title[:80], 'item_id': item_id,
                })
                break  # one opp per listing per variant set

        # === NEW METHOD: combined approach ===
        # Find best keyword+price match
        full_matches = [v for v in variants if v['keywords'] and
                       all(kw in title_words or kw in title_lower for kw in v['keywords'])]
        if full_matches:
            hybrid = min(full_matches, key=lambda v: abs(v['price'] - price))
        else:
            hybrid = min(variants, key=lambda v: abs(v['price'] - price))

        # For BIN: use hybrid if it disagrees with best-profit variant
        if lt == 'buy_it_now':
            # Find the most profitable variant that keyword-matches
            profitable_matches = []
            for v in variants:
                if v['parallel'] != 'Base' and v['keywords']:
                    if not all(kw in title_words or kw in title_lower for kw in v['keywords']):
                        continue
                profit_v = v['price'] - price - (price * FEE)
                if profit_v >= MIN_PROFIT:
                    profitable_matches.append((v, profit_v))

            if profitable_matches:
                best_v, best_profit = max(profitable_matches, key=lambda x: x[1])
                # Sanity: is the hybrid (price-closest) match much cheaper?
                if hybrid['price'] < best_v['price'] * 0.6:
                    # Hybrid says this card is cheaper -- pipeline would be wrong
                    # Use hybrid price instead
                    real_profit = hybrid['price'] - price - (price * FEE)
                    if real_profit >= MIN_PROFIT:
                        new_method_opps.append({
                            'player': player, 'year': year, 'number': number,
                            'parallel': hybrid['parallel'], 'scp_price': hybrid['price'],
                            'buy': price, 'profit': round(real_profit, 2), 'type': lt,
                            'title': title[:80], 'item_id': item_id,
                        })
                else:
                    # Hybrid and best-profit agree (or are close) -- real opportunity
                    new_method_opps.append({
                        'player': player, 'year': year, 'number': number,
                        'parallel': best_v['parallel'], 'scp_price': best_v['price'],
                        'buy': price, 'profit': round(best_profit, 2), 'type': lt,
                        'title': title[:80], 'item_id': item_id,
                    })

        # For auctions: use best full-keyword match
        elif lt == 'auction':
            if full_matches:
                best = max(full_matches, key=lambda v: v['price'])
                profit = best['price'] - price - (price * FEE)
                if profit >= MIN_PROFIT:
                    new_method_opps.append({
                        'player': player, 'year': year, 'number': number,
                        'parallel': best['parallel'], 'scp_price': best['price'],
                        'buy': price, 'profit': round(profit, 2), 'type': lt,
                        'title': title[:80], 'item_id': item_id,
                    })

# Dedupe by item_id
def dedupe(opps):
    seen = set()
    out = []
    for o in opps:
        if o['item_id'] not in seen:
            seen.add(o['item_id'])
            out.append(o)
    return out

old_deduped = dedupe(old_method_opps)
new_deduped = dedupe(new_method_opps)

# Validate both against closest-variant ground truth
def validate(opps):
    real = 0
    for o in opps:
        key = (o['player'], o['year'], o['number'])
        variants = card_variants.get(key, [])
        if not variants:
            continue
        closest = min(variants, key=lambda v: abs(v['price'] - o['buy']))
        real_profit = closest['price'] - o['buy'] - (o['buy'] * FEE)
        if real_profit >= MIN_PROFIT:
            real += 1
    return real

old_real = validate(old_deduped)
new_real = validate(new_deduped)

print(f"\n{'=' * 70}")
print(f"END-TO-END SIMULATION RESULTS")
print(f"{'=' * 70}")
print(f"Listings checked: {listings_checked}")
print(f"Passed basic filters: {listings_passed_filters}")
print(f"")
print(f"OLD METHOD (any keyword):")
print(f"  Raw opportunities: {len(old_deduped)}")
print(f"  Validated real:    {old_real}")
print(f"  Accuracy:          {old_real}/{len(old_deduped)} = {old_real/max(len(old_deduped),1)*100:.1f}%")
print(f"")
print(f"NEW METHOD (combined):")
print(f"  Raw opportunities: {len(new_deduped)}")
print(f"  Validated real:    {new_real}")
print(f"  Accuracy:          {new_real}/{len(new_deduped)} = {new_real/max(len(new_deduped),1)*100:.1f}%")
print(f"")
print(f"IMPROVEMENT:")
print(f"  Real opps: {old_real} -> {new_real} ({'+' if new_real > old_real else ''}{new_real - old_real})")
print(f"  Accuracy:  {old_real/max(len(old_deduped),1)*100:.1f}% -> {new_real/max(len(new_deduped),1)*100:.1f}%")
print(f"{'=' * 70}")

# Show new method's top opportunities
if new_deduped:
    new_deduped.sort(key=lambda x: -x['profit'])
    bin_count = sum(1 for o in new_deduped if o['type'] == 'buy_it_now')
    auc_count = len(new_deduped) - bin_count
    print(f"\nNew method breakdown: {bin_count} BIN + {auc_count} auction")

db.close()
