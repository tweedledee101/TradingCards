#!/usr/bin/env python3
"""
Run find_opportunities.py against the dev database (same as migrate.py --dev).

Uses **DATABASE_URL_DEV** if set; otherwise **DATABASE_URL** with the database name replaced by **trading_cards_dev**.
Ensures the dev database exists (CREATE DATABASE on the same instance) when allowed.

Usage:
  python3 scripts/run_find_opportunities_dev.py --player-rank-source sales --top-players 20 ...
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Repo root on path for backend.*
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.utils.dev_postgres import (
    DEFAULT_DEV_DATABASE,
    ensure_dev_database_exists,
    pg_username_from_url,
    resolve_dev_database_url,
)

LOCAL_FALLBACK = "postgresql://postgres:postgres@localhost:5432/trading_cards"


def _load_env(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        os.environ.setdefault(k, v)


def main() -> int:
    _load_env(ROOT / "backend" / ".env")
    prod = (os.environ.get("DATABASE_URL") or "").strip() or LOCAL_FALLBACK
    dev, src = resolve_dev_database_url(
        explicit_dev=os.environ.get("DATABASE_URL_DEV"),
        prod_url=prod,
        default_dev_db=DEFAULT_DEV_DATABASE,
    )
    if not dev:
        print(
            "error: set DATABASE_URL or DATABASE_URL_DEV in backend/.env",
            file=sys.stderr,
        )
        return 2
    if src == "derived from DATABASE_URL":
        print(f"  ({src}; set DATABASE_URL_DEV for deploy-api-lambda-dev.sh)", flush=True)
    user = pg_username_from_url(dev)
    ok, msg = ensure_dev_database_exists(dev, grant_to_username=user or None)
    print(f"  {msg}", flush=True)
    if not ok:
        return 1
    os.environ["DATABASE_URL"] = dev
    target = ROOT / "find_opportunities.py"
    argv = [sys.executable, str(target), *sys.argv[1:]]
    os.execv(sys.executable, argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
