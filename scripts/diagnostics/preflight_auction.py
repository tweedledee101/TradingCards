#!/usr/bin/env python3
"""Pre-flight: test every assumption the auction pipeline depends on."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'backend', '.env'))

from contextlib import closing
from sqlalchemy import text

failures = []

# 1. DB connection
print("1. RDS connection...", end=" ", flush=True)
try:
    from backend.utils.database import SessionLocal
    with closing(SessionLocal()) as db:
        r = db.execute(text("SELECT current_database(), NOW()::text")).first()
        print(f"OK ({r[0]})")
except Exception as e:
    print(f"FAIL: {e}")
    failures.append("DB connection")

# 2. Liquid card queries from scp_cache
print("2. Liquid card queries...", end=" ", flush=True)
try:
    from backend.services.liquid_auction_queries import build_liquid_auction_queries
    with closing(SessionLocal()) as db:
        queries, cards, meta = build_liquid_auction_queries(db, min_price=5, max_price=1000, limit=10)
        total = meta.get('total_liquid_variants', 0)
        print(f"OK ({len(queries)} queries from {total} liquid variants)")
        if queries:
            print(f"   Sample: {queries[0]!r}")
        if not queries:
            print("   WARNING: 0 liquid queries -- scp_cache may be empty")
            failures.append("No liquid cards in scp_cache")
except Exception as e:
    print(f"FAIL: {e}")
    failures.append("Liquid query build")

# 3. eBay Browse API (1 call)
print("3. eBay Browse API...", end=" ", flush=True)
try:
    from backend.scrapers.ebay_scraper import EbayScraper
    scraper = EbayScraper()
    q = queries[0] if queries else "baseball card"
    meta_out = {}
    results = scraper.search_auctions_ending_soon(q, hours=168, meta_out=meta_out)
    ebay_total = meta_out.get('ebay_total')
    print(f"OK ({len(results)} results, total~{ebay_total})")
except Exception as e:
    print(f"FAIL: {e}")
    failures.append("eBay Browse API")

# 4. Opportunities table writable
print("4. Opportunities table...", end=" ", flush=True)
try:
    with closing(SessionLocal()) as db:
        count = db.execute(text("SELECT COUNT(*) FROM opportunities WHERE listing_type = 'auction'")).scalar()
        print(f"OK ({count} auction rows currently)")
except Exception as e:
    print(f"FAIL: {e}")
    failures.append("Opportunities table")

# 5. CE verification import
print("5. CE import...", end=" ", flush=True)
try:
    from backend.utils.collectors_edge_result import call_ce_identify_api
    print("OK")
except ImportError as e:
    print(f"FAIL: {e}")
    failures.append("CE import")

# 6. JobTracker
print("6. JobTracker...", end=" ", flush=True)
try:
    from backend.utils.job_tracker import JobTracker
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")
    failures.append("JobTracker")

# 7. find_auction_opportunities.py parses
print("7. Pipeline script parses...", end=" ", flush=True)
try:
    import py_compile
    py_compile.compile(
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'find_auction_opportunities.py'),
        doraise=True
    )
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")
    failures.append("Pipeline parse")

# 8. Known players (MLB API)
print("8. MLB Stats API...", end=" ", flush=True)
try:
    import requests
    resp = requests.get("https://statsapi.mlb.com/api/v1/sports/1/players?season=2026", timeout=10)
    people = resp.json().get('people', [])
    print(f"OK ({len(people)} players for 2026)")
except Exception as e:
    print(f"FAIL: {e}")
    failures.append("MLB API")

print()
if failures:
    print(f"BLOCKED: {len(failures)} failure(s): {', '.join(failures)}")
    sys.exit(1)
else:
    print("All 8 checks passed. Safe to run pipeline.")
