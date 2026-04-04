#!/usr/bin/env python3
"""
Run multiple Nova Act listing-visual probes from nova_act_probe_cases.json.

Use this to sanity-check whether vision-based matching behaves on real listings
(baseline vs deliberately wrong expected, vague-title picks, slabs).

  # Validate case file + list cases (no API, no browser)
  python scripts/dev/run_nova_act_probe_cases.py --dry-run

  # Enable cases in JSON (set \"enabled\": true) and fill listing_url, then:
  python3.12 scripts/dev/run_nova_act_probe_cases.py --headless

Edit cases: scripts/dev/nova_act_probe_cases.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

_CASES_PATH = Path(__file__).resolve().parent / "nova_act_probe_cases.json"
_PROBE_PATH = Path(__file__).resolve().parent / "nova_act_listing_visual_probe.py"

_spec = importlib.util.spec_from_file_location("nova_act_listing_visual_probe", _PROBE_PATH)
probe = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(probe)


_RANK = {"high": 3, "medium": 2, "low": 1, "unclear": 0}


def _load_cases(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data.get("cases")
    if not isinstance(cases, list):
        raise ValueError("JSON root must have a 'cases' array")
    for i, c in enumerate(cases):
        if not isinstance(c, dict):
            raise ValueError(f"cases[{i}] must be an object")
        for key in ("id", "listing_url", "expected_identity"):
            if key not in c:
                raise ValueError(f"cases[{i}] missing {key!r}")
    return cases


def _check_threshold(
    conf: str,
    at_least: str | None,
    at_most: str | None,
) -> tuple[bool, str]:
    r = _RANK.get(conf, -1)
    if at_least is not None:
        need = _RANK.get(at_least, -1)
        if r < need:
            return False, f"confidence {conf!r} < required {at_least!r}"
    if at_most is not None:
        cap = _RANK.get(at_most, 99)
        if r > cap:
            return False, f"confidence {conf!r} > allowed {at_most!r}"
    return True, "ok"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Run Nova Act probe cases from JSON.")
    p.add_argument(
        "--cases",
        type=Path,
        default=_CASES_PATH,
        help="Path to nova_act_probe_cases.json",
    )
    p.add_argument("--headless", action="store_true")
    p.add_argument("--max-steps", type=int, default=28)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Load and print cases only (no Nova Act)",
    )
    p.add_argument(
        "--only",
        default="",
        help="Comma-separated case ids to run (must also be enabled in JSON unless --force)",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Run matching --only ids even if enabled is false in JSON",
    )
    args = p.parse_args(argv)

    try:
        all_cases = _load_cases(args.cases)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"Error loading cases: {e}", file=sys.stderr)
        return 2

    only_set = {x.strip() for x in args.only.split(",") if x.strip()}

    def want_run(c: dict) -> bool:
        if only_set and c["id"] not in only_set:
            return False
        if c.get("enabled") is True:
            return True
        if args.force and only_set and c["id"] in only_set:
            return True
        return False

    to_run = [c for c in all_cases if want_run(c)]

    if args.dry_run:
        print(f"Cases file: {args.cases}")
        print(f"Total cases: {len(all_cases)}")
        print(f"Selected to run: {len(to_run)}")
        for c in all_cases:
            sel = "RUN" if c in to_run else "skip"
            url_ok = "yes" if (c.get("listing_url") or "").strip().startswith("http") else "no"
            print(
                f"  [{sel:4}] {c['id']}: enabled={c.get('enabled')} url_ok={url_ok} "
                f"{c.get('notes', '')[:70]}"
            )
        if len(to_run) == 0:
            print(
                "\n--- Why Selected to run is 0 ---\n"
                "  A case runs only if:\n"
                "    • \"enabled\": true in the JSON,  OR  you pass --only <id> --force\n"
                "    • \"listing_url\" is a full eBay item URL (https://www.ebay.com/itm/...)\n"
                "    • \"expected_identity\" is non-empty\n"
                "\n"
                "  Next steps:\n"
                f"    1. Edit: {args.cases}\n"
                "    2. For case 01: set listing_url, expected_identity, and \"enabled\": true\n"
                "    3. Run (use Python 3.10+): python3.12 scripts/dev/run_nova_act_probe_cases.py --headless\n"
                "\n"
                "  Or keep enabled false, fill URL + expected, then one-shot:\n"
                "    python3.12 scripts/dev/run_nova_act_probe_cases.py "
                "--only 01_baseline_photo_matches_expected --force --headless\n"
            )
        return 0

    if not to_run:
        print(
            "No cases to run. Edit nova_act_probe_cases.json: set enabled true and real listing_url,\n"
            "or pass --only id1,id2 --force with URLs filled in.",
            file=sys.stderr,
        )
        return 2

    probe._load_nova_env()
    if not os.getenv("NOVA_ACT_API_KEY"):
        print("NOVA_ACT_API_KEY / NOVA_API_KEY missing (backend/.env or export).", file=sys.stderr)
        return 2
    if not probe._nova_act_python_ok():
        print("Python 3.10+ required for nova-act.", file=sys.stderr)
        return 2
    if not probe._nova_act_available():
        print("nova_act not installed for this interpreter.", file=sys.stderr)
        return 2

    failures = 0
    for c in to_run:
        cid = c["id"]
        url = (c.get("listing_url") or "").strip()
        exp = (c.get("expected_identity") or "").strip()
        if not url.startswith("http"):
            print(f"SKIP {cid}: invalid or empty listing_url", file=sys.stderr)
            failures += 1
            continue
        if not exp:
            print(f"SKIP {cid}: empty expected_identity", file=sys.stderr)
            failures += 1
            continue

        print(f"\n=== {cid} ===\n{url}\nexpected: {exp}\n")
        try:
            assessment = probe.run_listing_visual_assessment(
                url,
                exp,
                headless=args.headless,
                max_steps=args.max_steps,
            )
        except probe.ProbeError as e:
            print(f"FAIL {cid}: {e}", file=sys.stderr)
            failures += 1
            continue
        except Exception as e:
            print(f"FAIL {cid}: {e}", file=sys.stderr)
            failures += 1
            continue

        body = assessment.model_dump()
        print(json.dumps(body, indent=2))

        lo = c.get("want_confidence_at_least")
        hi = c.get("want_confidence_at_most")
        if lo is not None or hi is not None:
            ok, msg = _check_threshold(
                assessment.match_confidence,
                str(lo) if lo else None,
                str(hi) if hi else None,
            )
            if not ok:
                print(f"THRESHOLD FAIL {cid}: {msg}", file=sys.stderr)
                failures += 1
            else:
                print(f"THRESHOLD OK {cid}: {msg}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
