#!/usr/bin/env python3
"""
Collectors Edge **exploration** harness: sample different DB cohorts, run the photo probe
with conservative spacing, and write a JSON report. Intended to learn what CE is good at
(baseline vs weak SCP / QA rows) without hammering the site.

**Polite defaults:** small samples, cooldown between cohort subprocesses (sequential mode), headless.

**Parallelism:** each cohort is still a **full Playwright/Chromium** run (not a lightweight API thread).
``--max-parallel 2`` starts up to two cohort subprocesses at once (more RAM/CPU; be careful not to hammer CE).

Examples:
  # List cohorts and sample ids only (no browser):
  python scripts/dev/collectors_edge_explore.py --dry-run

  # Run CE once per cohort (90s cooldown between cohorts):
  python scripts/dev/collectors_edge_explore.py --execute --cooldown-seconds 90

  # Narrow cohorts, 2 listings per cohort in one browser session each:
  python scripts/dev/collectors_edge_explore.py --execute --cohorts weak_scp_url,scp_or_qa_gap --per-cohort 2

  # Two cohorts at once, 8s between process starts, no between-job sleep:
  python scripts/dev/collectors_edge_explore.py --execute --max-parallel 2 --launch-stagger-seconds 8 --cooldown-seconds 0
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _summarize_artifacts_since(out_dir: Path, since: float) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for p in sorted(out_dir.glob("collectors_edge_*.json"), key=lambda x: x.stat().st_mtime):
        if p.stat().st_mtime < since:
            continue
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        db = j.get("database_opportunity") or {}
        parsed = j.get("parsed") or {}
        analysis = j.get("ce_pipeline_analysis") or {}
        rows.append(
            {
                "artifact_json": str(p),
                "opportunity_id": db.get("opportunity_id"),
                "median_usd": parsed.get("median_usd"),
                "confidence_pct": parsed.get("confidence_pct"),
                "edge_strength": parsed.get("edge_strength"),
                "suggested_qa_flags": analysis.get("suggested_qa_flags"),
                "player_alignment": (analysis.get("matching_hints") or {}).get("player_alignment"),
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    from dotenv import load_dotenv

    from backend.utils.collectors_edge_cohorts import (
        cohort_row_summary,
        iter_cohort_plan,
        list_cohort_names,
    )
    from backend.utils.database import SessionLocal

    ap = argparse.ArgumentParser(
        description="Sample opportunity cohorts and optionally run Collectors Edge photo probe.",
    )
    ap.add_argument(
        "--cohorts",
        default="baseline,weak_scp_url,scp_or_qa_gap,auction,qa_attention",
        help="Comma-separated cohort names (see --list-cohorts).",
    )
    ap.add_argument(
        "--per-cohort",
        type=int,
        default=1,
        metavar="N",
        help="How many opportunities to sample per cohort (keep small; default 1).",
    )
    ap.add_argument(
        "--scan-cap",
        type=int,
        default=600,
        help="Max recent rows to scan per cohort when sampling (default 600).",
    )
    ap.add_argument(
        "--cooldown-seconds",
        type=float,
        default=90.0,
        help="Sequential mode only: pause after each cohort subprocess (default 90). Ignored when --max-parallel > 1.",
    )
    ap.add_argument(
        "--max-parallel",
        type=int,
        default=1,
        metavar="N",
        help="Run up to N cohort photo_run subprocesses at the same time (each owns Chromium; RAM heavy). Default 1.",
    )
    ap.add_argument(
        "--launch-stagger-seconds",
        type=float,
        default=0.0,
        metavar="SEC",
        help="When --max-parallel > 1: sleep i*stagger before starting job i (spreads load on CE). Default 0; try 5–15.",
    )
    ap.add_argument(
        "--between-cards-seconds",
        type=float,
        default=25.0,
        help="--pause-between-cards for photo_run when a cohort has 2+ ids (default 25).",
    )
    ap.add_argument("--settle-ms", type=int, default=8000)
    ap.add_argument(
        "--headed",
        action="store_true",
        help="Run browser visibly (default: headless).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print cohort samples only; do not invoke Playwright.",
    )
    ap.add_argument(
        "--execute",
        action="store_true",
        help="Run collectors_edge_photo_run.py per cohort (requires Playwright + Chromium).",
    )
    ap.add_argument(
        "--list-cohorts",
        action="store_true",
        help="Print cohort keys and exit.",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=_REPO_ROOT / "scripts" / "dev" / "_collectors_edge_artifacts",
        help="Artifact directory (same as photo_run).",
    )
    ap.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Write exploration report JSON (default: out-dir/ce_explore_<utc>.json).",
    )
    ap.add_argument(
        "--merge-qa-to-db",
        action="store_true",
        help="Forward --merge-qa-to-db to collectors_edge_photo_run (merge CE flags into opportunities).",
    )
    ap.add_argument(
        "--allow-duplicate-ids-across-cohorts",
        action="store_true",
        help="Allow the same opportunity id in multiple cohorts in one batch (default: dedupe).",
    )
    args = ap.parse_args(argv)

    if args.list_cohorts:
        print("Cohort keys:", ", ".join(list_cohort_names()))
        return 0

    cohorts = [c.strip() for c in args.cohorts.split(",") if c.strip()]
    for c in cohorts:
        if c not in list_cohort_names():
            print(f"Unknown cohort {c!r}. Use --list-cohorts.", file=sys.stderr)
            return 2

    if args.execute and args.dry_run:
        print("Use only one of --execute or --dry-run.", file=sys.stderr)
        return 2

    if not args.execute and not args.dry_run:
        print(
            "Choose --dry-run (sample ids only) or --execute (run CE). "
            "Showing samples as dry-run.",
            file=sys.stderr,
        )
        args.dry_run = True

    load_dotenv(_REPO_ROOT / "backend" / ".env")
    db = SessionLocal()
    plan: list[tuple[str, list[int]]] = []
    try:
        for name, ids in iter_cohort_plan(
            db,
            cohorts,
            per_cohort=max(1, args.per_cohort),
            scan_cap=max(50, args.scan_cap),
            dedupe_globally=not args.allow_duplicate_ids_across_cohorts,
        ):
            plan.append((name, ids))
    finally:
        db.close()

    n_plan = len(plan)
    mp = max(1, args.max_parallel)
    if mp > 4:
        print(
            f"[explore] Warning: --max-parallel={mp} is aggressive for CE + your machine; 2–3 is usually enough.",
            file=sys.stderr,
            flush=True,
        )
    if args.execute and n_plan:
        cool_m = max(0, n_plan - 1) * (args.cooldown_seconds / 60.0)
        if mp == 1:
            print(
                f"\n[explore] Plan: {n_plan} cohort subprocess(es), sequential. "
                f"Each CE photo run is often ~1–3 min (upload + ~30–90s analysis + settle + save). "
                f"Cooldown between cohorts: {args.cooldown_seconds:.0f}s (~{cool_m:.1f} min total sleep). "
                f"Ctrl+C aborts; safe to re-run.",
                flush=True,
            )
        else:
            print(
                f"\n[explore] Plan: {n_plan} cohort subprocess(es), up to {mp} concurrent Chromium instances. "
                f"Launch stagger: {args.launch_stagger_seconds:.1f}s between starts. "
                f"Subprocess stdout/stderr may interleave. Respect CE rate limits.",
                flush=True,
            )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = args.report or (args.out_dir / f"ce_explore_{stamp}.json")
    report: dict[str, object] = {
        "started_at_utc": stamp,
        "cohorts_requested": cohorts,
        "per_cohort": args.per_cohort,
        "dry_run": bool(args.dry_run),
        "executed": bool(args.execute),
        "merge_qa_to_db": bool(args.merge_qa_to_db),
        "dedupe_ids_across_cohorts": not args.allow_duplicate_ids_across_cohorts,
        "cooldown_seconds": args.cooldown_seconds,
        "max_parallel": mp,
        "launch_stagger_seconds": args.launch_stagger_seconds,
        "runs": [],
    }

    photo_script = _REPO_ROOT / "scripts" / "dev" / "collectors_edge_photo_run.py"
    out_dir_resolved = args.out_dir.expanduser().resolve()

    run_rows: list[dict[str, object]] = []
    pending_execute: list[tuple[int, list[str]]] = []

    for idx, (cohort, ids) in enumerate(plan):
        entry: dict[str, object] = {"cohort": cohort, "opportunity_ids": ids, "row_summaries": []}
        db2 = SessionLocal()
        try:
            for oid in ids:
                summ = cohort_row_summary(db2, oid)
                if summ:
                    entry["row_summaries"].append(summ)
        finally:
            db2.close()

        print(f"\n=== [{idx + 1}/{n_plan}] Cohort {cohort!r} → ids {ids} ===", flush=True)
        for s in entry["row_summaries"]:
            print(
                f"  id={s['opportunity_id']} has_scp_url={s['has_scp_url']} "
                f"flagged={s['flagged']} qa={s['qa_status']!r} type={s['listing_type']!r} "
                f"player={s['player_name']!r}",
                flush=True,
            )

        if args.dry_run:
            run_rows.append(entry)
            continue

        if not ids:
            entry["skipped"] = "no rows matched cohort with listing images"
            run_rows.append(entry)
            continue

        cmd = [
            sys.executable,
            str(photo_script),
            "--from-db",
            "--opportunity-ids",
            ",".join(str(i) for i in ids),
            "--settle-ms",
            str(args.settle_ms),
            "--keep-open",
            "0",
            "--out-dir",
            str(args.out_dir),
        ]
        if len(ids) > 1:
            cmd += [
                "--pause-between-cards",
                str(max(0.0, args.between_cards_seconds)),
            ]
        else:
            cmd += ["--pause-between-cards", "0"]
        if not args.headed:
            cmd.append("--headless")
        if args.merge_qa_to_db:
            cmd.append("--merge-qa-to-db")

        entry["command"] = cmd
        run_rows.append(entry)
        pending_execute.append((len(run_rows) - 1, cmd))

    report["runs"] = run_rows

    if args.execute and pending_execute:

        def _run_subprocess(job: tuple[int, list[str], float]) -> tuple[int, int, list[dict[str, object]], float]:
            run_index, cmd, stagger = job
            if stagger > 0:
                time.sleep(stagger)
            cohort = str(run_rows[run_index].get("cohort", ""))
            print(f"[explore] START cohort={cohort!r} pid-slot (parallel={mp > 1})", flush=True)
            since = time.time()
            t0 = time.time()
            r = subprocess.run(cmd, cwd=str(_REPO_ROOT))
            dt = time.time() - t0
            arts = _summarize_artifacts_since(out_dir_resolved, since)
            print(
                f"[explore] DONE cohort={cohort!r} exit={r.returncode} wall_s={dt:.0f}",
                flush=True,
            )
            return run_index, r.returncode, arts, dt

        if mp == 1:
            for i, (run_index, cmd) in enumerate(pending_execute):
                print("  Running:", " ".join(cmd[:6]), "...", flush=True)
                print(
                    "  [explore] Long pause after ‘Identify & Value’ is normal (CE analyzing).",
                    flush=True,
                )
                ri, code, arts, _dt = _run_subprocess((run_index, cmd, 0.0))
                run_rows[ri]["exit_code"] = code
                run_rows[ri]["artifacts"] = arts
                run_rows[ri]["wall_seconds"] = round(_dt, 2)
                if i < len(pending_execute) - 1 and args.cooldown_seconds > 0:
                    print(
                        f"\nCooldown {args.cooldown_seconds:.0f}s before next cohort…\n",
                        flush=True,
                    )
                    time.sleep(args.cooldown_seconds)
        else:
            jobs = [
                (run_index, cmd, float(i) * max(0.0, args.launch_stagger_seconds))
                for i, (run_index, cmd) in enumerate(pending_execute)
            ]
            print(
                "[explore] Parallel mode: subprocess output below may be interleaved.\n",
                flush=True,
            )
            with ThreadPoolExecutor(max_workers=mp) as pool:
                futures = [pool.submit(_run_subprocess, j) for j in jobs]
                for fut in as_completed(futures):
                    run_index, code, arts, dt = fut.result()
                    run_rows[run_index]["exit_code"] = code
                    run_rows[run_index]["artifacts"] = arts
                    run_rows[run_index]["wall_seconds"] = round(dt, 2)

    # Roll-up for quick scanning (did CE return a median? player_alignment hints?)
    art_rows: list[dict[str, object]] = []
    for run in report["runs"]:
        if isinstance(run, dict):
            art_rows.extend(run.get("artifacts") or [])
    likely_ok = sum(
        1
        for a in art_rows
        if a.get("median_usd") is not None
        and a.get("player_alignment") == "likely_match"
    )
    report["summary"] = {
        "cohorts_in_plan": len(plan),
        "artifact_rows_captured": len(art_rows),
        "count_median_and_likely_player_match": likely_ok,
        "note": "Compare weak_scp / scp_or_qa_gap cohorts vs baseline using artifact JSON + ce_pipeline_analysis on disk.",
    }

    report_path = report_path.expanduser().resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nWrote report: {report_path}", flush=True)
    if art_rows:
        print(
            f"Summary: {report['summary']['artifact_rows_captured']} artifact row(s); "
            f"{likely_ok} with median + likely player match.",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
