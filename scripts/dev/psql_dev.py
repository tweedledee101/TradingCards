#!/usr/bin/env python3
"""
Run psql against the dev database URL (same resolution as migrate.py --dev).

Uses DATABASE_URL_DEV from backend/.env if set; otherwise derives …/trading_cards_dev
from DATABASE_URL (or local default postgres URL if DATABASE_URL is unset).

Examples:
  python3 scripts/psql_dev.py -c "\\d cards"
  python3 scripts/psql_dev.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from backend.utils.dev_postgres import DEFAULT_DEV_DATABASE, resolve_dev_database_url

LOCAL_FALLBACK = "postgresql://postgres:postgres@localhost:5432/trading_cards"


def main() -> int:
    load_dotenv(ROOT / "backend" / ".env")
    prod = (os.environ.get("DATABASE_URL") or "").strip() or LOCAL_FALLBACK
    url, src = resolve_dev_database_url(
        explicit_dev=os.environ.get("DATABASE_URL_DEV"),
        prod_url=prod,
        default_dev_db=DEFAULT_DEV_DATABASE,
    )
    if not url:
        print("error: could not resolve dev DB URL", file=sys.stderr)
        return 2
    if src == "derived from DATABASE_URL":
        print(f"# {src}", file=sys.stderr)
    argv = ["psql", url, *sys.argv[1:]]
    os.execvp("psql", argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
