"""Integration tests need PostgreSQL; ``DATABASE_URL`` should point at RDS or local."""

from __future__ import annotations

import os
from pathlib import Path


def pytest_configure(config) -> None:
    if os.environ.get("DATABASE_URL"):
        return
    root = Path(__file__).resolve().parents[2]
    env_file = root / "backend" / ".env"
    if not env_file.is_file():
        return
    try:
        from dotenv import dotenv_values
    except ImportError:
        return
    data = dotenv_values(env_file)
    url = data.get("DATABASE_URL")
    if url:
        os.environ["DATABASE_URL"] = str(url).strip()
