"""Nova Act probe case file + runner dry-run (no API)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CASES_JSON = REPO_ROOT / "scripts" / "dev" / "nova_act_probe_cases.json"
RUNNER = REPO_ROOT / "scripts" / "dev" / "run_nova_act_probe_cases.py"


def test_nova_act_probe_cases_json_schema() -> None:
    data = json.loads(CASES_JSON.read_text(encoding="utf-8"))
    cases = data["cases"]
    assert len(cases) >= 3
    for c in cases:
        assert "id" in c and "listing_url" in c and "expected_identity" in c


@pytest.mark.skipif(not RUNNER.is_file(), reason="runner missing")
def test_run_nova_act_probe_cases_dry_run() -> None:
    proc = subprocess.run(
        [sys.executable, str(RUNNER), "--dry-run"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Total cases:" in proc.stdout
