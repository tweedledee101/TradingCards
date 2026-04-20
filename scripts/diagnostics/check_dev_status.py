#!/usr/bin/env python3
"""Quick diagnostic: what exists in prod DB vs dev DB right now."""
import os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Load .env
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

def check_db(label, url):
    try:
        conn = psycopg2.connect(url, connect_timeout=10)
        cur = conn.cursor()

        cur.execute("SELECT current_database()")
        dbname = cur.fetchone()[0]

        cur.execute("SELECT count(*) FROM schema_migrations")
        mig = cur.fetchone()[0]

        cur.execute("SELECT count(*) FROM opportunities")
        opps = cur.fetchone()[0]

        cur.execute("SELECT listing_type, count(*) FROM opportunities GROUP BY listing_type")
        by_type = dict(cur.fetchall())

        cur.execute("SELECT max(created_at) FROM opportunities")
        latest_opp = cur.fetchone()[0]

        cur.execute("SELECT count(*) FROM cards")
        cards = cur.fetchone()[0]

        cur.execute("SELECT count(*) FROM market_rates")
        rates = cur.fetchone()[0]

        cur.execute("SELECT count(*) FROM sold_comps")
        comps = cur.fetchone()[0]

        cur.execute("SELECT count(*) FROM sales")
        sales = cur.fetchone()[0]

        cur.execute("SELECT count(DISTINCT player_name) FROM cards")
        players = cur.fetchone()[0]

        conn.close()

        print(f"\n=== {label} (db: {dbname}) ===")
        print(f"  Migrations:    {mig}")
        print(f"  Cards:         {cards} ({players} players)")
        print(f"  Sales:         {sales}")
        print(f"  Market rates:  {rates}")
        print(f"  Sold comps:    {comps}")
        print(f"  Opportunities: {opps}")
        for t, c in by_type.items():
            print(f"    {t}: {c}")
        print(f"  Latest opp:    {latest_opp}")
        return True
    except psycopg2.OperationalError as e:
        err = str(e).strip().split("\n")[0]
        print(f"\n=== {label} ===")
        print(f"  CONNECTION FAILED: {err}")
        return False
    except Exception as e:
        err = str(e).strip().split("\n")[0]
        print(f"\n=== {label} ===")
        print(f"  ERROR: {err}")
        return False

print("Checking databases...")
check_db("PRODUCTION", prod_url)
check_db("DEV", dev_url)
