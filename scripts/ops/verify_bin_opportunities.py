#!/usr/bin/env python3
"""Post-ingest BIN verification: sold_comps vs SCP + deferred CE hook (no Playwright here)."""
from __future__ import annotations

import argparse
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from sqlalchemy import or_

from backend.models import Opportunity
from backend.services.bin_opportunity_verification import verify_bin_opportunity_row
from backend.utils.database import SessionLocal


def main() -> None:
    p = argparse.ArgumentParser(description="Update verification_* on BIN opportunities from sold_comps")
    p.add_argument("--limit", type=int, default=200, help="Max rows to process")
    p.add_argument(
        "--only-pending",
        action="store_true",
        help="Only rows where verification_status = pending (default: also refresh pending)",
    )
    p.add_argument("--min-id", type=int, default=0)
    args = p.parse_args()

    with SessionLocal() as db:
        q = db.query(Opportunity).filter(
            or_(Opportunity.listing_type == "buy_it_now", Opportunity.listing_type.is_(None))
        )
        if args.only_pending:
            q = q.filter(Opportunity.verification_status == "pending")
        q = q.filter(Opportunity.id >= args.min_id)
        q = q.order_by(Opportunity.id.desc()).limit(args.limit)
        rows = q.all()
        n = 0
        for opp in rows:
            patch = verify_bin_opportunity_row(db, opp)
            prev = dict(opp.verification_detail or {})
            merged = {**prev, **patch["verification_detail"]}
            opp.verification_status = patch["verification_status"]
            opp.verification_detail = merged
            n += 1
        db.commit()
        print(f"Updated {n} BIN opportunity row(s).")


if __name__ == "__main__":
    main()
