#!/usr/bin/env python3
"""
Compare values the UI would see from prod vs dev API (same routes, different DB).

Unauthenticated:
  GET /health  → includes postgres_db_name so you can confirm which database each host uses.

Authenticated (Bearer JWT — same Cognito user works for both if callback URLs allow dev UI):
  GET /api/opportunities-stats
  GET /api/opportunities?limit=5

Usage:
  export COGNITO_ACCESS_TOKEN="eyJ..."
  python3 scripts/compare_dev_prod_api.py

  python3 scripts/compare_dev_prod_api.py \\
    --prod-url https://api.ragnarokgamez.com \\
    --dev-url https://dev-api.ragnarokgamez.com \\
    --token "$COGNITO_ACCESS_TOKEN"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Optional


def _get(url: str, token: Optional[str] = None, timeout: float = 60.0) -> tuple[int, Any]:
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(err)
        except json.JSONDecodeError:
            return e.code, err


def _print_block(title: str, data: Any) -> None:
    print(f"\n=== {title} ===")
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2, default=str))
    else:
        print(data)


def main() -> int:
    p = argparse.ArgumentParser(description="Compare prod vs dev API responses")
    p.add_argument("--prod-url", default="https://api.ragnarokgamez.com")
    p.add_argument("--dev-url", default="https://dev-api.ragnarokgamez.com")
    p.add_argument(
        "--token",
        default=os.environ.get("COGNITO_ACCESS_TOKEN", ""),
        help="JWT for authenticated routes (or set COGNITO_ACCESS_TOKEN)",
    )
    args = p.parse_args()
    prod = args.prod_url.rstrip("/")
    dev = args.dev_url.rstrip("/")

    for label, base in (("PROD", prod), ("DEV", dev)):
        code, data = _get(f"{base}/health")
        _print_block(f"{label} GET /health (HTTP {code})", data)

    tok = (args.token or "").strip()
    if not tok:
        print(
            "\n(No --token / COGNITO_ACCESS_TOKEN — skipping /api/opportunities-stats and /api/opportunities)",
            file=sys.stderr,
        )
        return 0

    for label, base in (("PROD", prod), ("DEV", dev)):
        code, data = _get(f"{base}/api/opportunities-stats", tok)
        _print_block(f"{label} GET /api/opportunities-stats (HTTP {code})", data)

    for label, base in (("PROD", prod), ("DEV", dev)):
        code, data = _get(f"{base}/api/opportunities?limit=5", tok)
        if isinstance(data, dict) and "opportunities" in data:
            opps = data.get("opportunities") or []
            slim = [
                {
                    "id": o.get("id"),
                    "player_name": o.get("player_name"),
                    "buy_price": float(o["buy_price"]) if o.get("buy_price") is not None else None,
                    "scp_price": float(o["scp_price"]) if o.get("scp_price") is not None else None,
                    "price_source": o.get("price_source"),
                    "listing_type": o.get("listing_type"),
                }
                for o in opps[:5]
            ]
            data = {**data, "opportunities": slim, "_note": "first 5 rows summarized for diff"}
        _print_block(f"{label} GET /api/opportunities?limit=5 (HTTP {code})", data)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
