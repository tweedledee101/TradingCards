#!/usr/bin/env python3
"""
Rank auction Browse queries by **new unique listings** per call (from last completed job).

Uses ``job_runs.results_summary.step1_query_stats`` written by ``find_auction_opportunities.py``.
Helps answer: which ``q`` strings burn API quota for little deduped coverage vs ``ebay_total_hint``.

  DATABASE_URL=postgresql://... python3 scripts/diagnose_auction_query_efficiency.py
  python3 scripts/diagnose_auction_query_efficiency.py --job-id 12345
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    parser = argparse.ArgumentParser(description="Diagnose auction Browse query efficiency from job_runs")
    parser.add_argument("--job-id", type=int, default=None, help="Specific auction_finder job id")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.job_id:
            row = db.execute(
                text(
                    """
                    SELECT id, results_summary, completed_at
                    FROM job_runs
                    WHERE id = :jid AND job_name = 'auction_finder'
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
                    WHERE job_name = 'auction_finder'
                      AND status = 'completed'
                      AND results_summary IS NOT NULL
                    ORDER BY id DESC
                    LIMIT 1
                    """
                )
            ).mappings().first()

        if not row:
            print("No completed auction_finder job with results_summary found.", file=sys.stderr)
            return 1

        sid = row["id"]
        summary = _parse_summary(row["results_summary"])
        print(f"=== auction_finder job id={sid} completed_at={row.get('completed_at')} ===\n")

        if not summary:
            print("Could not parse results_summary JSON.")
            return 1

        vqm = summary.get("value_query_meta") or {}
        if vqm:
            print("value_query_meta:", json.dumps(vqm, default=str))
            print()

        stats = summary.get("step1_query_stats") or []
        if not stats:
            print("No step1_query_stats in summary (older pipeline build). Re-run find_auction_opportunities.py.")
            return 0

        n = len(stats)
        total_pages = sum(int(s.get("pages") or 0) for s in stats)
        total_new = sum(int(s.get("new_after_dedupe") or 0) for s in stats)
        print(f"Queries: {n} | Browse search GETs: {total_pages} | New-after-dedupe (sum per q): {total_new}")
        print(f"auctions_searched (unique ids): {summary.get('auctions_searched')}")
        print(f"qualified: {summary.get('qualified')} | opportunities_found: {summary.get('opportunities_found')}\n")

        # Lowest marginal yield first (many rows but few new = overlapping universe)
        ranked = sorted(
            stats,
            key=lambda s: (int(s.get("new_after_dedupe") or 0), int(s.get("items_returned") or 0)),
        )
        print("--- Lowest new_after_dedupe (consider trimming or rotating) ---")
        for s in ranked[:15]:
            q = (s.get("query") or "")[:90]
            print(
                f"  new={s.get('new_after_dedupe')} rows={s.get('items_returned')} "
                f"pages={s.get('pages')} total≈{s.get('ebay_total_hint')} | {q!r}"
            )

        print("\n--- Highest new_after_dedupe (keep / emulate) ---")
        for s in sorted(stats, key=lambda x: int(x.get("new_after_dedupe") or 0), reverse=True)[:15]:
            q = (s.get("query") or "")[:90]
            print(
                f"  new={s.get('new_after_dedupe')} rows={s.get('items_returned')} "
                f"pages={s.get('pages')} total≈{s.get('ebay_total_hint')} | {q!r}"
            )

        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
