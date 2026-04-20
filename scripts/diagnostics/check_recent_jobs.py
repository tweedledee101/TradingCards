#!/usr/bin/env python3
"""Check recent job_runs in prod and dev databases."""
import os, sys
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
dev_url = os.environ.get("DATABASE_URL_DEV", "") or prod_url.replace("/trading_cards", "/trading_cards_dev")

def check_jobs(label, url):
    try:
        conn = psycopg2.connect(url, connect_timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT job_name, status, started_at, completed_at, items_processed
            FROM job_runs ORDER BY started_at DESC LIMIT 8
        """)
        rows = cur.fetchall()
        conn.close()
        print(f"\n=== {label} recent job_runs ===")
        if not rows:
            print("  (no jobs)")
            return
        for r in rows:
            name, status, started, completed, items = r
            print(f"  {name:30s} {status:12s} {str(started)[:19]}  items={items}")
    except Exception as e:
        print(f"\n=== {label} ===")
        print(f"  ERROR: {str(e).strip().split(chr(10))[0]}")

check_jobs("PRODUCTION", prod_url)
check_jobs("DEV", dev_url)
