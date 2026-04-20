#!/usr/bin/env python3
"""Show dev job_runs parameters and results_summary to understand what ran."""
import os, sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

env_path = ROOT / "backend" / ".env"
if env_path.is_file():
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:]
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip("\"'")
        os.environ.setdefault(k, v)

import psycopg2

prod_url = os.environ.get("DATABASE_URL", "")
dev_url = prod_url.replace("/trading_cards", "/trading_cards_dev")

def show_jobs(label, url):
    try:
        conn = psycopg2.connect(url, connect_timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, job_name, status, started_at, parameters, results_summary
            FROM job_runs ORDER BY started_at DESC LIMIT 4
        """)
        rows = cur.fetchall()
        conn.close()
        print(f"\n{'='*60}")
        print(f"  {label}")
        print(f"{'='*60}")
        for r in rows:
            jid, name, status, started, params, results = r
            print(f"\n  [{jid}] {name} - {status} - {str(started)[:19]}")
            if params:
                p = params if isinstance(params, dict) else json.loads(params) if params else {}
                # Show key params
                interesting = {k: v for k, v in p.items() if k in (
                    'player_rank_source', 'top_players', 'players', 'sport',
                    'dev_strict_listings', 'dev_reconcile_scp_comps',
                    'min_profit', 'max_budget', 'hours', 'bin_replace_scope'
                )}
                if interesting:
                    print(f"    params: {json.dumps(interesting)}")
                else:
                    print(f"    params keys: {list(p.keys())[:10]}")
            if results:
                r = results if isinstance(results, dict) else json.loads(results) if results else {}
                interesting_r = {k: v for k, v in r.items() if k in (
                    'opportunities_found', 'auctions_searched', 'qualified',
                    'step2_skip_reasons', 'step3_no_pricing', 'step3_below_min_profit',
                    'rank_source', 'players_found', 'total_variations',
                    'ebay_listings_fetched_total', 'bin_opportunities', 'auction_opportunities'
                )}
                if interesting_r:
                    print(f"    results: {json.dumps(interesting_r, default=str)}")
                else:
                    print(f"    results keys: {list(r.keys())[:12]}")
    except Exception as e:
        print(f"\n{label}: {e}")

show_jobs("PRODUCTION", prod_url)
show_jobs("DEV", dev_url)
