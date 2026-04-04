"""Smoke test for the Nova Act listing visual probe (no API key required)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "dev" / "nova_act_listing_visual_probe.py"


@pytest.mark.skipif(not SCRIPT.is_file(), reason="probe script missing")
def test_nova_act_listing_visual_probe_dry_run_exits_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "ListingVisualAssessment" in proc.stdout or "match_confidence" in proc.stdout
