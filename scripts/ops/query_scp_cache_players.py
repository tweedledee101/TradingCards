#!/usr/bin/env python3
"""Query SCP cache for top single-player entries by volume."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.utils.database import SessionLocal
from backend.models import SCPCache
from sqlalchemy import func

db = SessionLocal()
rows = (
    db.query(SCPCache.player_name, func.count(SCPCache.id).label('cnt'))
    .filter(func.length(SCPCache.player_name) < 40)
    .filter(~SCPCache.player_name.contains(','))
    .group_by(SCPCache.player_name)
    .order_by(func.count(SCPCache.id).desc())
    .limit(80)
    .all()
)
db.close()
for name, cnt in rows:
    print(f"{cnt:>5}  {name.strip()}")
