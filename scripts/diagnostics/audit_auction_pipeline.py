#!/usr/bin/env python3
"""
Data-driven audit: auction opportunities + last auction_finder job summaries.

Run against RDS (or local) with DATABASE_URL set:
  DATABASE_URL=postgresql://... python3 scripts/audit_auction_pipeline.py

Prints:
  - Rows the UI would show (listing_type=auction, not ended)
  - Stale rows (ended but still in table)
  - Latest job_runs for job_name='auction_finder' with parsed funnel JSON
  - error_log rows for source auction_finder (last 7 days)

Use this to validate hypotheses (e.g. "we lose everyone at step2 no_card_number")
instead of guessing from code alone.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

# Repo root on path
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


NUMERIC_FUNNEL_KEYS = (
    "auctions_searched",
    "qualified",
    "opportunities_found",
    "detail_lookups",
    "db_hits",
    "cache_hits",
    "selenium_hits",
    "sold_comp_hits",
    "ebay_comp_hits",
    "no_scp_or_rejected",
    "step3_no_pricing",
    "step3_no_pricing_after_primary",
    "step3_no_pricing_after_sold_comps",
    "step3_bin_sanity",
    "step3_low_volume",
    "step3_below_min_profit",
)


def _print_funnel_compare(new_id, s_new, old_id, s_old):
    print(f"\n=== Funnel delta: run {new_id} (newer) − run {old_id} (older) ===\n")
    if not s_new or not s_old:
        print("  (need parsed results_summary on both runs)")
        return

    def nval(x):
        return int(x) if x is not None else 0

    for k in NUMERIC_FUNNEL_KEYS:
        vn, vo = s_new.get(k), s_old.get(k)
        if vn is None and vo is None:
            continue
        d = nval(vn) - nval(vo)
        print(f"  {k}: {vn} vs {vo}  ({d:+d})")

    sn = s_new.get("step2_skip_reasons") or {}
    so = s_old.get("step2_skip_reasons") or {}
    if sn or so:
        print("  step2_skip_reasons (newer vs older, delta):")
        for sk in sorted(set(sn) | set(so)):
            a, b = nval(sn.get(sk)), nval(so.get(sk))
            delta = a - b
            print(f"    {sk}: {sn.get(sk, 0)} vs {so.get(sk, 0)}  ({delta:+d})")


def main():
    parser = argparse.ArgumentParser(description="Audit auction opportunities and job_runs funnel")
    parser.add_argument(
        "--compare",
        action="store_true",
        help="After listing runs, print numeric delta between the two most recent completed summaries",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        now = datetime.now()
        print("=== Opportunities table: auctions (what /api/auctions serves) ===\n")

        row = db.execute(
            text(
                """
                SELECT
                    COUNT(*) FILTER (
                        WHERE end_time IS NULL OR end_time > :now
                    ) AS active_ui,
                    COUNT(*) FILTER (
                        WHERE end_time IS NOT NULL AND end_time <= :now
                    ) AS ended_still_stored,
                    COUNT(*) AS total_auction_rows
                FROM opportunities
                WHERE listing_type = 'auction'
                """
            ),
            {"now": now},
        ).mappings().first()
        print(f"  Active (end_time null or future): {row['active_ui']}")
        print(f"  Ended but still in DB:            {row['ended_still_stored']}")
        print(f"  Total auction rows:               {row['total_auction_rows']}")

        print("\n=== Latest auction_finder job_runs (funnel in results_summary) ===\n")
        runs = db.execute(
            text(
                """
                SELECT id, status, started_at, completed_at, error_message, results_summary, parameters
                FROM job_runs
                WHERE job_name = 'auction_finder'
                ORDER BY id DESC
                LIMIT 8
                """
            )
        ).mappings().all()

        if not runs:
            print("  (no job_runs for auction_finder — pipeline may never have completed against this DB)")
        parsed_pair = []
        for r in runs:
            print(f"--- run id={r['id']} status={r['status']} started={r['started_at']} ---")
            if r["error_message"]:
                print(f"  error_message: {r['error_message'][:500]}")
            params = r["parameters"]
            if params:
                try:
                    print(f"  parameters: {params[:300]}..." if len(params) > 300 else f"  parameters: {params}")
                except TypeError:
                    print(f"  parameters: {params}")
            raw = r["results_summary"]
            if not raw:
                print("  results_summary: (null)")
                print()
                continue
            s = _parse_summary(raw)
            if s is None:
                print(f"  results_summary (raw): {raw[:400]}")
                print()
                continue
            if args.compare and len(parsed_pair) < 2:
                parsed_pair.append((r["id"], s))
            print("  results_summary (parsed):")
            for k in NUMERIC_FUNNEL_KEYS + ("no_scp_match",):
                if k in s:
                    print(f"    {k}: {s[k]}")
            if "step2_skip_reasons" in s:
                print("    step2_skip_reasons:")
                for sk, sv in sorted(s["step2_skip_reasons"].items(), key=lambda x: -x[1]):
                    print(f"      {sk}: {sv}")
            s2v = s.get("step2_skip_vision_queue_sample")
            if isinstance(s2v, list) and s2v:
                print(
                    f"    step2_skip_vision_queue_sample: {len(s2v)} listings "
                    f"(metadata skips w/ images → merged into vision_post_pipeline_queue_sample)"
                )
            if "parameters" in s:
                print(f"    run_parameters: {s['parameters']}")
            q = s.get("no_scp_vision_queue_sample")
            if isinstance(q, list):
                print(f"    no_scp_vision_queue_sample: {len(q)} listings (legacy; see vision_post_pipeline_queue_sample)")
            elif q is not None:
                print(f"    no_scp_vision_queue_sample: (unexpected type {type(q).__name__})")
            vpp = s.get("vision_post_pipeline_queue_sample")
            if isinstance(vpp, list):
                print(
                    f"    vision_post_pipeline_queue_sample: {len(vpp)} listings "
                    f"(post-pipeline Nova — scripts/vision_retry_scp_from_images.py)"
                )
            elif vpp is not None:
                print(f"    vision_post_pipeline_queue_sample: (unexpected type {type(vpp).__name__})")
            sq = s.get("step1_query_stats")
            if isinstance(sq, list) and sq:
                print(
                    f"    step1_query_stats: {len(sq)} Browse queries — "
                    f"python3 scripts/diagnose_auction_query_efficiency.py --job-id {r['id']}"
                )
            print()

        if args.compare and len(parsed_pair) >= 2:
            new_id, s_new = parsed_pair[0]
            old_id, s_old = parsed_pair[1]
            _print_funnel_compare(new_id, s_new, old_id, s_old)
        elif args.compare:
            print("\n=== --compare: need at least two runs with valid JSON results_summary ===\n")

        print("=== error_log: auction_finder, last 7 days (WARN+) ===\n")
        errs = db.execute(
            text(
                """
                SELECT level, category, COUNT(*) AS n
                FROM error_log
                WHERE source = 'auction_finder'
                  AND timestamp > NOW() - INTERVAL '7 days'
                GROUP BY level, category
                ORDER BY n DESC
                LIMIT 30
                """
            )
        ).mappings().all()
        if not errs:
            print("  (no rows — logger may not persist INFO, or no recent warnings)")
        for e in errs:
            print(f"  {e['level']:7} {e['category'] or '-':20} {e['n']}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
