#!/usr/bin/env python3
"""
Summarize BIN pipeline **per-SCP-variation eBay stats** from the latest ``opportunity_finder`` job.

``find_opportunities.py`` stores ``ebay_variation_stats`` in ``job_runs.results_summary``:
for each variation: ``listings_fetched``, ``opportunities_raw``, ``passed_profit_roi`` (meets
``--min-profit`` / ``--min-roi``), and the Browse ``query`` string.

Use this to see which queries pull inventory vs dead ends — same idea as
``diagnose_auction_query_efficiency.py`` for auctions.

  DATABASE_URL=postgresql://... python3 scripts/diagnose_bin_ebay_variation_stats.py
  python3 scripts/diagnose_bin_ebay_variation_stats.py --job-id 123
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text

from backend.utils.database import SessionLocal


def _parse_summary(raw):
    if not raw:
        return None
    try:
        return json.loads(raw) if isinstance(raw, str) else dict(raw)
    except json.JSONDecodeError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose BIN eBay variation stats from job_runs")
    parser.add_argument("--job-id", type=int, default=None)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.job_id:
            row = db.execute(
                text(
                    """
                    SELECT id, results_summary, completed_at
                    FROM job_runs
                    WHERE id = :jid AND job_name = 'opportunity_finder'
                    """
                ),
                {"jid": args.job_id},
            ).mappings().first()
        else:
            row = db.execute(
                text(
                    """
                    SELECT id, results_summary, completed_at
                    FROM job_runs
                    WHERE job_name = 'opportunity_finder'
                      AND status = 'completed'
                      AND results_summary IS NOT NULL
                    ORDER BY id DESC
                    LIMIT 1
                    """
                )
            ).mappings().first()

        if not row:
            print("No completed opportunity_finder job with results_summary found.", file=sys.stderr)
            return 1

        s = _parse_summary(row["results_summary"])
        print(f"=== opportunity_finder job id={row['id']} completed_at={row.get('completed_at')} ===\n")
        if not s:
            print("Could not parse results_summary.")
            return 1

        print(
            f"variations_checked: {s.get('variations_checked')} | "
            f"opportunities_found: {s.get('opportunities_found')} | "
            f"ebay_listings_fetched_total: {s.get('ebay_listings_fetched_total')} | "
            f"variations_with_opportunities: {s.get('variations_with_opportunities')} | "
            f"skip_auction_chain: {s.get('skip_auction_chain')}\n"
        )

        stats = s.get("ebay_variation_stats") or []
        if not stats:
            print("No ebay_variation_stats (older pipeline build). Re-run find_opportunities.py.")
            return 0

        print(f"Per-variation rows: {len(stats)}\n")

        with_hits = [x for x in stats if int(x.get("passed_profit_roi") or 0) > 0]
        print(f"--- Variations with ≥1 stored opportunity ({len(with_hits)}) ---")
        for x in sorted(with_hits, key=lambda r: int(r.get("passed_profit_roi") or 0), reverse=True)[:25]:
            print(
                f"  hit={x.get('passed_profit_roi')} raw={x.get('opportunities_raw')} "
                f"fetched={x.get('listings_fetched')} | {(x.get('query') or '')[:85]!r}"
            )

        no_fetch = [x for x in stats if int(x.get("listings_fetched") or 0) == 0 and not x.get("ebay_error")]
        print(f"\n--- Zero listings returned (sample 15 of {len(no_fetch)}) ---")
        for x in no_fetch[:15]:
            print(f"  {(x.get('query') or '')[:90]!r}")

        high_fetch_no_hit = [
            x for x in stats
            if int(x.get("listings_fetched") or 0) >= 30 and int(x.get("passed_profit_roi") or 0) == 0
        ]
        print(
            f"\n--- High fetch (≥30) but no qualifying opportunity ({len(high_fetch_no_hit)}) — filters/economics ---"
        )
        for x in sorted(high_fetch_no_hit, key=lambda r: int(r.get("listings_fetched") or 0), reverse=True)[:20]:
            print(
                f"  fetched={x.get('listings_fetched')} raw_opp={x.get('opportunities_raw')} "
                f"scp=${x.get('scp_price')} | {(x.get('query') or '')[:75]!r}"
            )

        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
