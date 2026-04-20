#!/usr/bin/env python3
"""
Copy reference data from prod (trading_cards) to dev (trading_cards_dev) on the same RDS instance.

Copies: cards, sales, market_rates, sold_comps, scp_cache
Does NOT copy: opportunities, job_runs, error_log (those are pipeline output, not input)

Usage:
  python3 scripts/copy_prod_reference_to_dev.py --dry-run
  python3 scripts/copy_prod_reference_to_dev.py
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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

TABLES = ["cards", "sales", "market_rates", "sold_comps", "scp_cache", "active_listings"]


def get_count(conn, table):
    cur = conn.cursor()
    cur.execute(f"SELECT count(*) FROM {table}")
    return cur.fetchone()[0]


def copy_table(prod_conn, dev_conn, table, dry_run=False):
    prod_count = get_count(prod_conn, table)
    dev_count = get_count(dev_conn, table)

    if prod_count == 0:
        print(f"  {table}: prod has 0 rows, skipping")
        return

    print(f"  {table}: prod={prod_count:,}, dev={dev_count:,}", end="")

    if dev_count > 0:
        if dry_run:
            print(f" -> would TRUNCATE dev + copy {prod_count:,} rows")
            return
        print(f" -> TRUNCATING dev...", end="", flush=True)
        dev_cur = dev_conn.cursor()
        dev_cur.execute(f"TRUNCATE {table} CASCADE")
        dev_conn.commit()

    if dry_run:
        print(f" -> would copy {prod_count:,} rows")
        return

    print(f" -> copying {prod_count:,} rows...", end="", flush=True)

    # Get column names from prod
    prod_cur = prod_conn.cursor()
    prod_cur.execute(f"SELECT * FROM {table} LIMIT 0")
    columns = [desc[0] for desc in prod_cur.description]
    col_list = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))

    # Read all from prod
    prod_cur.execute(f"SELECT {col_list} FROM {table}")
    rows = prod_cur.fetchall()

    # Insert into dev in batches
    dev_cur = dev_conn.cursor()
    batch_size = 1000
    inserted = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        args_str = ",".join(
            dev_cur.mogrify(f"({placeholders})", row).decode() for row in batch
        )
        dev_cur.execute(f"INSERT INTO {table} ({col_list}) VALUES {args_str}")
        inserted += len(batch)

    dev_conn.commit()
    final = get_count(dev_conn, table)
    print(f" done ({final:,} rows)")


def main():
    parser = argparse.ArgumentParser(description="Copy reference data from prod to dev DB")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without changing anything")
    args = parser.parse_args()

    prod_url = os.environ.get("DATABASE_URL", "")
    dev_url = os.environ.get("DATABASE_URL_DEV", "") or prod_url.replace("/trading_cards", "/trading_cards_dev")

    if not prod_url:
        print("error: DATABASE_URL not set", file=sys.stderr)
        return 1

    print(f"{'DRY RUN - ' if args.dry_run else ''}Copying reference data from prod -> dev")
    print(f"  prod: .../{prod_url.rsplit('/', 1)[-1]}")
    print(f"  dev:  .../{dev_url.rsplit('/', 1)[-1]}")
    print()

    try:
        prod_conn = psycopg2.connect(prod_url, connect_timeout=15)
        dev_conn = psycopg2.connect(dev_url, connect_timeout=15)
    except Exception as e:
        print(f"Connection failed: {e}", file=sys.stderr)
        return 1

    for table in TABLES:
        try:
            copy_table(prod_conn, dev_conn, table, dry_run=args.dry_run)
        except Exception as e:
            print(f"\n  ERROR on {table}: {e}")
            dev_conn.rollback()

    # Summary
    print("\nDev DB after copy:")
    dev_cur = dev_conn.cursor()
    for table in TABLES + ["opportunities"]:
        try:
            dev_cur.execute(f"SELECT count(*) FROM {table}")
            c = dev_cur.fetchone()[0]
            print(f"  {table}: {c:,}")
        except Exception:
            dev_conn.rollback()
            print(f"  {table}: (error)")

    prod_conn.close()
    dev_conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
