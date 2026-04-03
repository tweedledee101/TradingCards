#!/usr/bin/env python3
"""
Remove ended auction rows from opportunities (listing_type = auction, end_time in the past).

Keeps BIN rows untouched. Use after audit shows large ended_still_stored.

  python3 scripts/cleanup_stale_auction_opportunities.py --dry-run
  python3 scripts/cleanup_stale_auction_opportunities.py
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from backend.utils.database import SessionLocal


def main():
    parser = argparse.ArgumentParser(description="Delete stale auction opportunity rows")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print count only, do not delete",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        now = datetime.now()
        row = db.execute(
            text(
                """
                SELECT COUNT(*) AS n
                FROM opportunities
                WHERE listing_type = 'auction'
                  AND end_time IS NOT NULL
                  AND end_time < :now
                """
            ),
            {"now": now},
        ).mappings().first()
        n = row["n"] or 0
        if args.dry_run:
            print(f"Would delete {n} stale auction opportunity row(s) (end_time < now)")
            return
        if n == 0:
            print("No stale auction rows to delete")
            return
        db.execute(
            text(
                """
                DELETE FROM opportunities
                WHERE listing_type = 'auction'
                  AND end_time IS NOT NULL
                  AND end_time < :now
                """
            ),
            {"now": now},
        )
        db.commit()
        print(f"Deleted {n} stale auction opportunity row(s)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
