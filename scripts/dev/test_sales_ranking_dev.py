#!/usr/bin/env python3
"""Test: can dev DB rank players by sales now?"""
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

# Point at dev
dev_url = os.environ["DATABASE_URL"].replace("/trading_cards", "/trading_cards_dev")
os.environ["DATABASE_URL"] = dev_url

from backend.utils.database import SessionLocal
from backend.discover_players import fetch_hot_players_from_sales

db = SessionLocal()
results = fetch_hot_players_from_sales(db, ["Baseball"], 30, 20)
print(f"Sales-based ranking (30d lookback) returned {len(results)} players:")
for name, sport, count in results[:15]:
    print(f"  {name:30s} {sport:12s} {count} sales")

if not results:
    print("\n  Trying 365d lookback...")
    results = fetch_hot_players_from_sales(db, ["Baseball"], 365, 20)
    print(f"  365d returned {len(results)} players")
    for name, sport, count in results[:10]:
        print(f"    {name:30s} {sport:12s} {count} sales")

db.close()
