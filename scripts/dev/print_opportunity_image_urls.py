#!/usr/bin/env python3
"""
Print real listing image URLs already stored in **opportunities** (`image_url` + `listing_image_urls`).

Uses `backend/.env` → same `DATABASE_URL` as the API / pipelines.

Examples:
  python scripts/dev/print_opportunity_image_urls.py --limit 5
  URL=$(python scripts/dev/print_opportunity_image_urls.py --limit 1 | head -1)
  # Same newest row every time? Skip it and use the next card with a URL:
  URL=$(python scripts/dev/print_opportunity_image_urls.py --limit 1 --skip 1 | head -1)
  python scripts/dev/collectors_edge_photo_run.py --image-url "$URL" --keep-open 25

  # One-shot (no $URL):  collectors_edge_photo_run.py --from-db

  python scripts/dev/print_opportunity_image_urls.py --limit 3 --json-queue > /tmp/q.json
  python scripts/vision_retry_scp_from_images.py --from-recent-opportunities 5 --dry-run
  python scripts/vision_retry_scp_from_images.py --json /tmp/q.json --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / "backend" / ".env")

from backend.utils.database import SessionLocal
from backend.utils.opportunity_image_urls import iter_opportunity_image_rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Print stored opportunity image URLs from PostgreSQL.")
    p.add_argument("--limit", type=int, default=10, help="Max opportunities to emit (skip rows with no URL).")
    p.add_argument(
        "--skip",
        type=int,
        default=0,
        help="Skip the first N opportunities that have image URLs (newest first). Use 1 to avoid repeating the same top row.",
    )
    p.add_argument(
        "--listing-type",
        choices=("all", "auction", "buy_it_now"),
        default="all",
        help="Filter by opportunities.listing_type.",
    )
    p.add_argument(
        "--json-queue",
        action="store_true",
        help="Emit one JSON array for vision_retry_scp_from_images.py --json.",
    )
    args = p.parse_args(argv)

    db = SessionLocal()
    try:
        batch: list[dict] = []
        emitted = 0
        for url, meta, all_urls in iter_opportunity_image_rows(
            db,
            listing_type=args.listing_type,
            skip=args.skip,
            limit=args.limit,
        ):
            emitted += 1
            if args.json_queue:
                batch.append(
                    {
                        "ebay_item_id": meta.get("ebay_item_id") or str(meta["opportunity_id"]),
                        "title": (meta.get("ebay_title") or "")[:240],
                        "image_urls": all_urls,
                    }
                )
            else:
                print(url)

        if args.json_queue:
            print(json.dumps(batch, indent=2))

        if emitted == 0:
            print(
                "No rows emitted (no http image_url / listing_image_urls, or --skip past the end of the pool). "
                "Run a BIN or auction pipeline that stores images, lower --skip, or check DATABASE_URL.",
                file=sys.stderr,
            )
            return 1
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
