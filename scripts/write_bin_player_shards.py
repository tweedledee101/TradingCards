#!/usr/bin/env python3
"""
Split the BIN player list into N shard files for parallel GitHub Actions matrix jobs.

Round-robin balances stars vs depth players across shards (better wall-clock than
contiguous slices when catalog size varies by player).

Usage (CI): same DATABASE_URL + discovery args as find_opportunities.py
  python3 scripts/write_bin_player_shards.py --shards 8 --out-dir bin_shards/

With explicit players (comma-separated):
  python3 scripts/write_bin_player_shards.py --shards 4 --out-dir out/ --players "A,B,C,D"
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Repo root on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Write shard-N.txt files (comma-separated players).")
    parser.add_argument("--shards", type=int, default=8, help="Number of shard files (default: 8)")
    parser.add_argument("--out-dir", type=str, default="bin_shards", help="Output directory")
    parser.add_argument("--players", type=str, default=None, help="Comma-separated names (skip DB discovery)")
    parser.add_argument("--top-players", type=int, default=100)
    parser.add_argument("--sport", type=str, default="Baseball")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--dynamic-seed-limit", type=int, default=50)
    parser.add_argument("--dynamic-seed-days", type=int, default=30)
    parser.add_argument("--max-discovery-candidates", type=int, default=100)
    parser.add_argument("--no-dynamic-seeds", action="store_true")
    parser.add_argument(
        "--player-rank-source",
        type=str,
        choices=("browse", "sold_comps", "sales"),
        default="browse",
    )
    parser.add_argument("--sales-rank-days", type=int, default=7)
    parser.add_argument("--sales-rank-fallback-browse", action="store_true")
    parser.add_argument("--sold-comps-rank-days", type=int, default=30)
    parser.add_argument("--no-sold-comps-fallback-browse", action="store_true")
    args = parser.parse_args()

    if args.shards < 1:
        print("error: --shards must be >= 1", file=sys.stderr)
        return 1

    if args.players:
        names = [p.strip() for p in args.players.split(",") if p.strip()]
    else:
        if not os.environ.get("DATABASE_URL"):
            print("error: DATABASE_URL required when --players not set", file=sys.stderr)
            return 1
        from contextlib import closing

        from backend.discover_players import hot_player_names_for_pipeline
        from backend.models import SessionLocal

        dyn = 0 if args.no_dynamic_seeds else max(0, args.dynamic_seed_limit)
        with closing(SessionLocal()) as db:
            names = hot_player_names_for_pipeline(
                limit=args.top_players,
                sport=args.sport,
                days=args.days,
                db_session=db,
                dynamic_sales_player_limit=dyn,
                dynamic_sales_lookback_days=args.dynamic_seed_days,
                max_discovery_candidates=args.max_discovery_candidates,
                rank_source=args.player_rank_source,
                sales_rank_lookback_days=args.sales_rank_days,
                sales_rank_fallback_browse=bool(args.sales_rank_fallback_browse),
                sold_comps_lookback_days=args.sold_comps_rank_days,
                sold_comps_fallback_browse=not args.no_sold_comps_fallback_browse,
            )

    if not names:
        print("error: zero players to shard", file=sys.stderr)
        return 1

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    buckets: list[list[str]] = [[] for _ in range(args.shards)]
    for idx, name in enumerate(names):
        buckets[idx % args.shards].append(name)

    for i, bucket in enumerate(buckets):
        path = out / f"shard-{i}.txt"
        path.write_text(",".join(bucket), encoding="utf-8")
        print(f"wrote {path} ({len(bucket)} players): {', '.join(bucket[:4])}{'…' if len(bucket) > 4 else ''}")

    print(f"total_players={len(names)} shards={args.shards}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
