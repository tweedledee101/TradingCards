#!/usr/bin/env python3
"""Copy scp_cache from prod to dev with JSONB handling."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for raw in (ROOT / "backend" / ".env").read_text().splitlines():
    line = raw.strip()
    if not line or line.startswith("#"):
        continue
    if line.startswith("export "):
        line = line[7:]
    if "=" not in line:
        continue
    k, _, v = line.partition("=")
    os.environ.setdefault(k.strip(), v.strip().strip("\"'"))

import psycopg2
import psycopg2.extras

psycopg2.extras.register_default_jsonb(globally=True, loads=json.loads)

prod_url = os.environ["DATABASE_URL"]
dev_url = os.environ.get("DATABASE_URL_DEV", "") or prod_url.replace("/trading_cards", "/trading_cards_dev")

prod = psycopg2.connect(prod_url)
dev = psycopg2.connect(dev_url)

dev.cursor().execute("TRUNCATE scp_cache")
dev.commit()

pc = prod.cursor()
pc.execute("SELECT * FROM scp_cache LIMIT 0")
cols = [d[0] for d in pc.description]
col_list = ", ".join(cols)

pc.execute(f"SELECT {col_list} FROM scp_cache")
rows = pc.fetchall()
print(f"Read {len(rows)} scp_cache rows from prod")

dc = dev.cursor()
inserted = 0
for row in rows:
    vals = []
    for v in row:
        if isinstance(v, (dict, list)):
            vals.append(json.dumps(v))
        else:
            vals.append(v)
    placeholders = ", ".join(["%s"] * len(vals))
    try:
        dc.execute(f"INSERT INTO scp_cache ({col_list}) VALUES ({placeholders})", vals)
        inserted += 1
    except Exception as e:
        dev.rollback()
        if inserted < 3:
            print(f"  skip row: {e}")

dev.commit()

dc.execute("SELECT count(*) FROM scp_cache")
print(f"Dev scp_cache now: {dc.fetchone()[0]}")
prod.close()
dev.close()
