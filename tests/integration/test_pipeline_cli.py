"""
Smoke tests: pipeline entrypoints parse CLI and exit 0 on --help.
Catches broken argparse / imports without running Selenium or hitting eBay.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

REPO = Path(__file__).resolve().parents[2]


def _run_help(cmd: List[str], *, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": str(REPO)}
    return subprocess.run(
        cmd,
        cwd=cwd or REPO,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )


def test_find_auction_opportunities_help():
    r = _run_help([sys.executable, str(REPO / "find_auction_opportunities.py"), "--help"])
    assert r.returncode == 0, r.stderr
    assert "--hours" in r.stdout
    assert "--dry-run" in r.stdout


def test_find_opportunities_help():
    r = _run_help([sys.executable, str(REPO / "find_opportunities.py"), "--help"])
    assert r.returncode == 0, r.stderr
    assert "--max-budget" in r.stdout


def test_run_pipeline_full_help():
    r = _run_help([sys.executable, "-m", "backend.run_pipeline_full", "--help"])
    assert r.returncode == 0, r.stderr
    assert "--skip-scp" in r.stdout


def test_migrate_help():
    r = _run_help([sys.executable, str(REPO / "migrate.py"), "--help"])
    assert r.returncode == 0, r.stderr
    assert "--rds" in r.stdout


def test_daily_report_import():
    """daily_report has no CLI; ensure module imports (used by scheduled workflow)."""
    import daily_report  # noqa: F401
