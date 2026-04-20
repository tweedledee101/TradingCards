#!/usr/bin/env python3
"""
After **Collectors Edge** photo flow, look up **our** SCP catalog row from the saved JSON.

CE establishes an independent read from the **image**; this script maps CE extraction to
``find_scp_match_for_vision`` (same relaxed matching as ``vision_retry_scp_from_images.py``).
You still **manually** confirm the eBay photo, CE identity, and SCP product image agree before
trading on the row.

Usage (use a **real** path — the lines below with ``path/to`` are documentation only):

  python3 scripts/scp_lookup_from_ce_json.py scripts/dev/_collectors_edge_artifacts/some_run.json
  python3 scripts/scp_lookup_from_ce_json.py --latest-ce-artifact
  # Passing a ce_explore_….json batch file opens the newest embedded collectors_edge_*.json inside it.
  python3 scripts/scp_lookup_from_ce_json.py artifact.json --prefer-db-year
  python3 scripts/scp_lookup_from_ce_json.py /path/to/artifact.json --player "Mike Trout" --year 2011 --number US175

Set ``CE_ARTIFACT_DIR`` to change where ``--latest-ce-artifact`` searches (default:
``scripts/dev/_collectors_edge_artifacts``).

Requires DB URL (same as API) and ``backend/.env`` if used locally.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / "backend" / ".env")

from backend.services.scp_db_match import (
    catalog_card_number_hints_for_player,
    find_scp_match_for_vision,
    vision_scp_miss_hint,
)
from backend.utils.ce_scp_identity import (
    enrich_identity_guess_from_ce_payload,
    find_latest_usable_ce_json,
    guess_identity_from_ce_extracted,
    merged_from_ce_artifact,
    resolve_explicit_ce_json_path,
)
from backend.utils.database import SessionLocal

_DEFAULT_CE_DIR = _ROOT / "scripts" / "dev" / "_collectors_edge_artifacts"


def _looks_like_doc_placeholder(p: Path) -> bool:
    s = str(p).lower().replace("\\", "/")
    if "path/to/" in s or s.endswith("path/to"):
        return True
    if "/full/path/" in s or s.startswith("/full/path"):
        return True
    if "from/ce/" in s or s.endswith("/from/ce/output.json"):
        return True
    if p.name.lower() in ("example.json", "placeholder.json"):
        return True
    return False


def _resolve_json_path(json_path: Path | None, latest: bool) -> tuple[Path, str]:
    if latest:
        root = Path(os.environ.get("CE_ARTIFACT_DIR", str(_DEFAULT_CE_DIR)))
        found, via = find_latest_usable_ce_json(root)
        if found is None:
            print(
                f"No usable CE photo JSON under {root} ({via}).\n"
                f"Need ``collectors_edge_*.json`` from ``collectors_edge_photo_run.py``, or a "
                f"``ce_explore_*.json`` that references existing ``artifact_json`` paths.\n"
                f"See PIPELINE-OPS.md — or pass the path printed as ``JSON: ...`` after a CE run.\n"
                f"Override search dir: export CE_ARTIFACT_DIR=/your/artifact/folder",
                file=sys.stderr,
            )
            raise SystemExit(2)
        return found, via
    if json_path is None:
        print(
            "Missing JSON path. Examples:\n"
            f"  python3 scripts/scp_lookup_from_ce_json.py {_DEFAULT_CE_DIR}/<file>.json\n"
            "  python3 scripts/scp_lookup_from_ce_json.py --latest-ce-artifact",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if _looks_like_doc_placeholder(json_path):
        print(
            f"{json_path!s} looks like a documentation placeholder, not a real file.\n"
            f"Use the .json path printed after `collectors_edge_photo_run.py` finishes, e.g. under:\n"
            f"  {_DEFAULT_CE_DIR}/\n"
            "Or: python3 scripts/scp_lookup_from_ce_json.py --latest-ce-artifact",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if not json_path.is_file():
        print(
            f"No such file: {json_path.resolve()}\n"
            "After a CE run, the script prints `JSON: ...` — pass that full path.\n"
            "Or try: python3 scripts/scp_lookup_from_ce_json.py --latest-ce-artifact",
            file=sys.stderr,
        )
        raise SystemExit(2)
    resolved, src_name = resolve_explicit_ce_json_path(json_path)
    if resolved is None:
        print(
            f"{json_path}: {src_name}\n"
            "For batch reports use a path under artifact_json, or --latest-ce-artifact.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if src_name:
        return resolved, f"(resolved from explore report {src_name})"
    return resolved, ""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="SCP DB lookup from Collectors Edge artifact JSON.")
    p.add_argument(
        "json_path",
        nargs="?",
        type=Path,
        default=None,
        help="CE photo_run artifact .json (path printed at end of collectors_edge_photo_run.py)",
    )
    p.add_argument(
        "--latest-ce-artifact",
        action="store_true",
        help=(
            f"Use newest collectors_edge_*.json under CE_ARTIFACT_DIR or {_DEFAULT_CE_DIR} "
            "(or follow ce_explore_*.json → artifact_json)"
        ),
    )
    p.add_argument("--player", help="Override player name")
    p.add_argument("--year", type=int, help="Override card year")
    p.add_argument("--number", metavar="N", help="Override card number (e.g. US175)")
    p.add_argument("--parallel", default="Base", help="Parallel (default Base)")
    p.add_argument("--card-set", default="", help="Optional set hint")
    p.add_argument(
        "--prefer-db-year",
        action="store_true",
        help="Use database_opportunity.card_year when present (listing/pipeline year vs CE headline)",
    )
    args = p.parse_args(argv)

    if args.latest_ce_artifact and args.json_path is not None:
        print("Use either a JSON path or --latest-ce-artifact, not both.", file=sys.stderr)
        return 2
    if not args.latest_ce_artifact and args.json_path is None:
        print("Provide a JSON file path or --latest-ce-artifact.", file=sys.stderr)
        return 2

    path, via_note = _resolve_json_path(
        args.json_path if not args.latest_ce_artifact else None,
        args.latest_ce_artifact,
    )

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {path}: {e}", file=sys.stderr)
        return 2

    merged = merged_from_ce_artifact(raw)
    g = guess_identity_from_ce_extracted(merged)
    g = enrich_identity_guess_from_ce_payload(raw, g)

    player = (args.player or g["player_name"] or "").strip()
    year = args.year if args.year is not None else g["card_year"]
    if args.prefer_db_year and args.year is None:
        opp = raw.get("database_opportunity")
        if isinstance(opp, dict) and opp.get("card_year") is not None:
            try:
                year = int(opp["card_year"])
            except (TypeError, ValueError):
                pass
    cn = (args.number or g["card_number"] or "").strip()
    parallel = (args.parallel or "Base").strip()
    if args.parallel == "Base" and (g.get("parallel") or "").strip() not in ("", "Base"):
        parallel = str(g["parallel"]).strip()
    card_set = (args.card_set or g["card_set"] or "").strip()

    line = f"Using CE artifact: {path}"
    if via_note:
        line += f" {via_note}"
    print(line, flush=True)
    if g.get("source_headline"):
        print(f"CE headline (trimmed): {g['source_headline']!r}", flush=True)
    print(
        f"Using identity: player={player!r} year={year!r} #{cn!r} parallel={parallel!r}",
        flush=True,
    )

    if not player or not cn:
        print(
            "Incomplete identity — pass --player and --number (and --year) explicitly.",
            file=sys.stderr,
        )
        return 2

    db = SessionLocal()
    try:
        hit = find_scp_match_for_vision(db, player, year, cn, parallel, card_set)
        if hit and hit.get("scp_price") is not None:
            mode = hit.get("db_match_mode")
            print(
                f"HIT  SCP ${hit['scp_price']:.2f}  parallel={hit.get('matched_parallel')!r}  "
                f"url={hit.get('scp_url')!r}  db_match={mode!r}"
            )
            if hit.get("db_match_note"):
                print(f"     note: {hit['db_match_note']}")
            return 0
        hint = vision_scp_miss_hint(db, player, year, cn, hint_context="ce_lookup")
        print(f"MISS  {hint}")
        sample, sample_note = catalog_card_number_hints_for_player(db, player, cn)
        if sample:
            print(f"  What *is* in your DB for {player!r} {sample_note}:", flush=True)
            print(f"    {sample}", flush=True)
        elif sample_note:
            print(f"  {sample_note}", flush=True)
        opp = raw.get("database_opportunity")
        if isinstance(opp, dict):
            su = opp.get("scp_url")
            if su:
                print(f"  Pipeline scp_url on opportunity row: {su}", flush=True)
            eu = opp.get("ebay_url")
            if eu:
                print(f"  eBay: {eu}", flush=True)
            if opp.get("card_year") is not None and year is not None:
                try:
                    ocy, uy = int(opp["card_year"]), int(year)
                except (TypeError, ValueError):
                    ocy, uy = None, None
                if ocy is not None and uy is not None and ocy != uy:
                    print(
                        f"Note: opportunity row has card_year={ocy} but lookup used {uy} "
                        f"(CE headline). Retry with --prefer-db-year or --year {ocy}.",
                        flush=True,
                    )
        safe_p = (player or "").replace("'", "''")
        print(
            "  psql (peer auth example): "
            f"sudo -u postgres psql -d trading_cards -c \""
            f"SELECT card_year, card_number, parallel FROM cards "
            f"WHERE lower(player_name) = lower('{safe_p}') "
            f"ORDER BY card_year, card_number LIMIT 50;\"",
            flush=True,
        )
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
