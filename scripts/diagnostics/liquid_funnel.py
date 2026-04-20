#!/usr/bin/env python3
"""Check how many liquid SCP variants were actually searched on eBay."""
import sys, os, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.utils.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Get all liquid variants
rows = db.execute(text("""
    SELECT sc.player_name, sc.card_year, sc.card_number, v->>'parallel' as parallel,
           v->>'card_set' as card_set, (v->>'ungraded')::numeric as price, v->>'volume' as volume
    FROM scp_cache sc, jsonb_array_elements(sc.variants) v
    WHERE v->>'volume' IS NOT NULL AND v->>'volume' != ''
    AND (v->>'ungraded')::numeric BETWEEN 20 AND 1000
    AND (LOWER(v->>'volume') LIKE '%per day%' OR LOWER(v->>'volume') LIKE '%per week%')
""")).fetchall()

# Dedupe by (player, year, number, parallel)
seen = set()
liquid = []
for r in rows:
    key = (r.player_name.strip(), r.card_year, (r.card_number or '').strip(), (r.parallel or 'Base').strip())
    if key not in seen:
        seen.add(key)
        liquid.append(r)

# Get all cached eBay search queries
cache_rows = db.execute(text("SELECT search_query, result_count FROM ebay_search_cache")).fetchall()
cache_queries = {r.search_query.lower().strip(): r.result_count for r in cache_rows}

# Build the same query the pipeline would build for each liquid variant
searched = 0
searched_with_results = 0
not_searched = 0
not_searched_examples = []

for r in liquid:
    parts = [r.player_name.strip()]
    if r.card_year:
        parts.append(str(r.card_year))
    if r.card_set:
        parts.append(r.card_set)
    if r.card_number:
        parts.append(f"#{r.card_number}")
    par = (r.parallel or 'Base').strip()
    if par != 'Base':
        parts.append(par)
    query = ' '.join(parts).lower().strip()

    if query in cache_queries:
        searched += 1
        if cache_queries[query] > 0:
            searched_with_results += 1
    else:
        not_searched += 1
        if len(not_searched_examples) < 15:
            not_searched_examples.append(f"  ${float(r.price):>7.2f} | {r.volume:<20s} | {' '.join(parts)}")

db.close()

print(f"LIQUID CARD FUNNEL ANALYSIS")
print(f"=" * 60)
print(f"Total liquid variants (daily/weekly):  {len(liquid)}")
print(f"Searched on eBay:                      {searched} ({searched*100//max(len(liquid),1)}%)")
print(f"  -> with results:                     {searched_with_results}")
print(f"  -> dead (0 results):                 {searched - searched_with_results}")
print(f"NOT searched yet:                      {not_searched} ({not_searched*100//max(len(liquid),1)}%)")
print()
if not_searched_examples:
    print(f"Examples of liquid cards NOT yet searched:")
    for ex in not_searched_examples:
        print(ex)
