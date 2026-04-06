#!/usr/bin/env python3
"""Re-evaluate persisted pipeline_listing_skips (comps + identity text) — marks audit_result."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

import re

from backend.models import PipelineListingSkip
from backend.services.bin_opportunity_verification import sold_comp_summary_for_identity
from backend.utils.database import SessionLocal


def _player_from_card_label(label: str) -> str:
    if not label:
        return ""
    m = re.match(r"^(.+?)\s+(\d{4})\s+", label.strip())
    return m.group(1).strip() if m else label.strip().split("  ")[0][:120]


def main() -> None:
    p = argparse.ArgumentParser(description="Audit pipeline_listing_skips rows")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--pipeline", type=str, default="opportunity_finder")
    args = p.parse_args()

    with SessionLocal() as db:
        rows = (
            db.query(PipelineListingSkip)
            .filter(PipelineListingSkip.pipeline == args.pipeline)
            .filter(PipelineListingSkip.audited_at.is_(None))
            .order_by(PipelineListingSkip.id.desc())
            .limit(args.limit)
            .all()
        )
        for sk in rows:
            title = (sk.ebay_title or "")[:500]
            label = sk.pipeline_card_label or ""
            player = _player_from_card_label(label)
            num_m = re.search(r"#([\w\-]+)", label)
            cn = num_m.group(1) if num_m else None
            yr_m = re.search(r"\b(19|20)\d{2}\b", label)
            cy = int(yr_m.group(0)) if yr_m else None

            cs = sold_comp_summary_for_identity(
                db,
                player_name=player,
                card_year=cy,
                card_number=cn,
            )
            result = {
                "audited_at": datetime.utcnow().isoformat() + "Z",
                "heuristic_player_guess": player,
                "sold_comps_count": cs.count,
                "note": "Full CE audit: use collectors_edge_photo_run with ebay_item_id image fetch",
                "ebay_title_sample": title[:240],
            }
            sk.audit_result = result
            sk.audited_at = datetime.utcnow()
        db.commit()
        print(f"Audited {len(rows)} skip row(s).")


if __name__ == "__main__":
    main()
