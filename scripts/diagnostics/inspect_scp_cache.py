#!/usr/bin/env python3
"""Inspect scp_cache structure to understand what data is available."""
import json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
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

dev_url = os.environ["DATABASE_URL"].replace("/trading_cards", "/trading_cards_dev")
os.environ["DATABASE_URL"] = dev_url

from backend.utils.database import SessionLocal
from backend.models import SCPCache
from sqlalchemy import func

db = SessionLocal()

# Sample entry
sample = db.query(SCPCache).limit(1).first()
if sample:
    print(f"player: {sample.player_name}")
    print(f"year: {sample.card_year}")
    print(f"number: {sample.card_number}")
    v = sample.variants
    if isinstance(v, str):
        v = json.loads(v)
    print(f"variants type: {type(v).__name__}, count: {len(v) if isinstance(v, list) else 'not list'}")
    if isinstance(v, list) and v:
        print(f"first variant keys: {list(v[0].keys()) if isinstance(v[0], dict) else 'not dict'}")
        print(json.dumps(v[0], indent=2, default=str))

# Stats
players = db.query(func.count(func.distinct(SCPCache.player_name))).scalar()
total = db.query(func.count(SCPCache.id)).scalar()
print(f"\nscp_cache: {total} entries, {players} unique players")

# Player list
player_list = db.query(SCPCache.player_name, func.count(SCPCache.id)).group_by(SCPCache.player_name).order_by(func.count(SCPCache.id).desc()).all()
print("\nPlayers in cache:")
for name, cnt in player_list[:25]:
    print(f"  {name:30s} {cnt} entries")

db.close()
