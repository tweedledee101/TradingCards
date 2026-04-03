#!/usr/bin/env python3
"""
Summarize recent GitHub Actions runs (failures, conclusions) without opening the UI.

Auth (first that works):
  - GITHUB_TOKEN or GH_TOKEN (classic PAT: repo scope, or fine-grained: Actions read)
  - gh auth token  (after: gh auth login)

Usage:
  python3 scripts/summarize_github_actions.py
  python3 scripts/summarize_github_actions.py --repo tweedledee101/TradingCards --limit 15
  python3 scripts/summarize_github_actions.py --workflow pipeline.yml auction-pipeline.yml
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _token() -> Optional[str]:
    for key in ("GITHUB_TOKEN", "GH_TOKEN"):
        t = os.environ.get(key, "").strip()
        if t:
            return t
    try:
        out = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _get(url: str, token: str) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def _iso_age(iso: str) -> str:
    try:
        # 2026-03-27T12:00:00Z
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        sec = int((now - dt).total_seconds())
        if sec < 3600:
            return f"{sec // 60}m ago"
        if sec < 86400:
            return f"{sec // 3600}h ago"
        return f"{sec // 86400}d ago"
    except Exception:
        return iso


def workflow_runs(
    repo: str, workflow_file: str, token: str, limit: int
) -> List[Dict[str, Any]]:
    q = f"per_page={min(limit, 100)}"
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_file}/runs?{q}"
    data = _get(url, token)
    return data.get("workflow_runs") or []


def run_jobs(repo: str, run_id: int, token: str) -> List[Dict[str, Any]]:
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100"
    data = _get(url, token)
    return data.get("jobs") or []


def _run_repo(r: Dict[str, Any], default: str) -> str:
    repo = r.get("repository")
    if isinstance(repo, dict) and repo.get("full_name"):
        return repo["full_name"]
    return default


def print_run_header(
    workflow_file: str,
    runs: List[Dict[str, Any]],
    limit: int,
    repo: str,
    token: str,
) -> None:
    print(f"\n{'=' * 72}")
    print(f"Workflow file: {workflow_file}  (last {len(runs)} run(s), showing up to {limit})")
    print("=" * 72)
    if not runs:
        print("  (no runs returned — wrong filename or no permissions?)")
        return
    for r in runs[:limit]:
        cid = r.get("conclusion") or "—"
        sid = r.get("status") or "—"
        mark = "OK " if cid == "success" else "!! " if cid == "failure" else "   "
        print(
            f"{mark}{_iso_age(r.get('created_at', '')):>8}  "
            f"conclusion={cid:<12} status={sid:<12}  "
            f"#{r.get('run_number')}  {r.get('event', '')}"
        )
        print(f"         {r.get('html_url', '')}")
        if cid == "failure":
            print("         --- failed steps (if any) ---")
            try:
                for job in run_jobs(_run_repo(r, repo), r["id"], token):
                    if job.get("conclusion") != "failure":
                        continue
                    print(f"         job: {job.get('name')} ({job.get('conclusion')})")
                    for step in job.get("steps") or []:
                        if step.get("conclusion") == "failure":
                            print(
                                f"           - {step.get('name')}: "
                                f"{step.get('conclusion')} (number {step.get('number')})"
                            )
            except urllib.error.HTTPError as e:
                print(f"         (could not load jobs: HTTP {e.code})")
            except Exception as ex:
                print(f"         (could not load jobs: {ex})")


def main() -> int:
    p = argparse.ArgumentParser(description="Summarize GitHub Actions runs")
    p.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY", "tweedledee101/TradingCards"),
        help="owner/repo (default: GITHUB_REPOSITORY or tweedledee101/TradingCards)",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=12,
        help="max runs per workflow to display",
    )
    p.add_argument(
        "--workflow",
        nargs="*",
        default=[
            "pipeline.yml",
            "auction-pipeline.yml",
            "card-data-pipeline.yml",
            "daily-report.yml",
        ],
        help="workflow file names under .github/workflows/",
    )
    args = p.parse_args()
    token = _token()
    if not token:
        print(
            "No GitHub auth: set GITHUB_TOKEN (or GH_TOKEN) with repo/actions read, "
            "or run: gh auth login",
            file=sys.stderr,
        )
        return 1

    repo = args.repo.strip()
    for wf in args.workflow:
        try:
            runs = workflow_runs(repo, wf, token, args.limit)
            print_run_header(wf, runs, args.limit, repo, token)
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode()[:500]
            except Exception:
                pass
            print(f"\n!! {wf}: HTTP {e.code} {e.reason}\n   {body}", file=sys.stderr)
        except Exception as e:
            print(f"\n!! {wf}: {e}", file=sys.stderr)

    print("\n" + "=" * 72)
    print("Tip: Trending uses `sales` from Card Data Pipeline (card-data-pipeline.yml),")
    print("     not the Opportunity Pipeline (pipeline.yml). See PIPELINE-OPS.md.")
    print("=" * 72 + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
