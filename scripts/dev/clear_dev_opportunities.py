#!/usr/bin/env python3
"""Clear dev opportunities and stale job_runs for a fresh pipeline comparison."""
import os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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

dev_url = os.environ.get("DATABASE_URL_DEV", "") or os.environ["DATABASE_URL"].replace("/trading_cards", "/trading_cards_dev")
conn = psycopg2.connect(dev_url)
cur = conn.cursor()

cur.execute("DELETE FROM opportunities")
conn.commit()
cur.execute("SELECT count(*) FROM opportunities")
print(f"Dev opportunities after clear: {cur.fetchone()[0]}")

cur.execute("UPDATE job_runs SET status='cancelled' WHERE status='running'")
conn.commit()

conn.close()
print("Ready for fresh dev pipeline run")
