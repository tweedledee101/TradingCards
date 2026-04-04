"""Map Collectors Edge ``ce_extracted`` merge dict to coarse SCP identity hints (human review)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

def is_ce_photo_run_payload(data: Any) -> bool:
    """True for ``collectors_edge_photo_run`` JSON (top-level ``ce_extracted`` with real content)."""
    if not isinstance(data, dict):
        return False
    ce = data.get("ce_extracted")
    if not isinstance(ce, dict) or not ce:
        return False
    return bool(ce.get("identity")) or isinstance(ce.get("from_body_text"), dict) or bool(ce.get("pricing"))


def path_is_valid_ce_photo_artifact(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return False
    return is_ce_photo_run_payload(data)


def _iter_collectors_edge_json_files(root: Path) -> list[Path]:
    """``collectors_edge_*.json`` (case-insensitive stem on disk)."""
    if not root.is_dir():
        return []
    out: list[Path] = []
    for p in root.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() != ".json":
            continue
        if p.name.lower().startswith("collectors_edge_"):
            out.append(p)
    return out


_SET_BREAK = frozenset(
    """
    topps bowman panini donruss leaf select prizm mosaic chrome sapphire stadium
    club elite draft sterling immaculate national treasures optic rated rookie
    """.split()
)


def merged_from_ce_artifact(data: dict[str, Any]) -> dict[str, Any]:
    """Accept full photo_run payload or a bare ``ce_extracted`` dict."""
    ce = data.get("ce_extracted")
    if isinstance(ce, dict):
        return ce
    return data


def guess_identity_from_ce_extracted(merged: dict[str, Any]) -> dict[str, Any]:
    ident = merged.get("identity") or {}
    headline = (ident.get("analysis_headline") or "").strip()
    years = ident.get("years_in_analysis_headline") or ident.get("years_mentioned") or []
    year = int(years[0]) if years else None
    cands = merged.get("card_number_candidates") or []
    cn = (cands[0] or "").strip().lstrip("#").strip() if cands else ""

    player = ""
    if headline:
        toks = headline.replace("#", " ").split()
        acc: list[str] = []
        for t in toks:
            tl = t.lower().rstrip(".,;:")
            if re.match(r"^(19|20)\d{2}$", tl):
                if year is None:
                    year = int(tl)
                continue
            if tl in _SET_BREAK or tl in ("rc", "sp", "ssp", "auto", "refractor"):
                break
            if re.match(r"^[a-z]{1,4}-[a-z0-9]+$", tl, re.I):
                if not cn:
                    cn = tl.upper() if tl.replace("-", "").isalnum() else tl
                break
            if t.isdigit() and len(t) <= 4 and not cn:
                cn = t
                continue
            acc.append(t)
        player = " ".join(acc).strip()

    return {
        "player_name": player,
        "card_year": year,
        "card_number": cn,
        "parallel": "Base",
        "card_set": "",
        "source_headline": headline[:240],
    }


def enrich_identity_guess_from_ce_payload(payload: dict[str, Any], g: dict[str, Any]) -> dict[str, Any]:
    """
    When CE headline parsing stops at set names (no # on-card), use ``database_opportunity``
    from the same photo_run JSON (player / year / # / parallel from our pipeline row).
    """
    out = dict(g)
    opp = payload.get("database_opportunity")
    if not isinstance(opp, dict):
        return out
    if not (out.get("player_name") or "").strip() and opp.get("player_name"):
        out["player_name"] = str(opp["player_name"]).strip()
    if out.get("card_year") is None and opp.get("card_year") is not None:
        try:
            out["card_year"] = int(opp["card_year"])
        except (TypeError, ValueError):
            pass
    if not (out.get("card_number") or "").strip() and opp.get("card_number"):
        out["card_number"] = str(opp["card_number"]).strip().lstrip("#").strip()
    if not (out.get("card_set") or "").strip() and opp.get("card_set"):
        out["card_set"] = str(opp["card_set"]).strip()
    par = (out.get("parallel") or "Base").strip()
    if par == "Base" and opp.get("parallel"):
        out["parallel"] = str(opp["parallel"]).strip()
    return out


def find_latest_collectors_edge_photo_json(root: Path) -> Path | None:
    """
    Newest **valid** ``collectors_edge_*.json`` (case-insensitive name) from photo_run.

    Skips corrupt files and never returns ``ce_explore_*.json``.
    """
    files = _iter_collectors_edge_json_files(root)
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for p in files:
        if path_is_valid_ce_photo_artifact(p):
            return p
    return None


def resolve_photo_json_from_ce_explore_report(report_path: Path) -> Path | None:
    """Pick the newest existing ``artifact_json`` path inside a ``ce_explore_*.json`` report."""
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    paths: list[Path] = []
    for run in data.get("runs") or []:
        if not isinstance(run, dict):
            continue
        for art in run.get("artifacts") or []:
            if not isinstance(art, dict):
                continue
            pj = art.get("artifact_json")
            if pj:
                paths.append(Path(str(pj)))
    existing = [p for p in paths if p.is_file() and path_is_valid_ce_photo_artifact(p)]
    if not existing:
        return None
    return max(existing, key=lambda p: p.stat().st_mtime)


def find_latest_usable_ce_json(root: Path) -> tuple[Path | None, str]:
    """
    Return ``(path, note)`` for SCP lookup.

    Prefers newest ``collectors_edge_*.json``; if none, uses newest ``ce_explore_*.json``
    and follows its embedded ``artifact_json`` paths.
    """
    direct = find_latest_collectors_edge_photo_json(root)
    if direct is not None:
        return direct, ""
    if not root.is_dir():
        return None, "directory missing"
    explores = sorted(
        _iter_ce_explore_json_files(root),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for rep in explores:
        resolved = resolve_photo_json_from_ce_explore_report(rep)
        if resolved is not None:
            return resolved, f"(from explore report {rep.name})"
    return None, "no valid collectors_edge_*.json and no ce_explore_*.json with usable artifact_json"


def resolve_explicit_ce_json_path(path: Path) -> tuple[Path | None, str]:
    """
    Normalize CLI path: CE photo JSON is used as-is; ``ce_explore_*.json`` (or any JSON with
    ``runs`` and no ``ce_extracted``) is rewritten to the newest valid embedded ``artifact_json``.

    Returns ``(path_to_open, explore_report_name_or_empty)``. On failure returns ``(None, error)``.
    """
    if not path.is_file():
        return None, "not a file"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError) as e:
        return None, str(e)
    if is_ce_photo_run_payload(data):
        return path, ""
    if isinstance(data, dict) and data.get("runs"):
        resolved = resolve_photo_json_from_ce_explore_report(path)
        if resolved is not None:
            return resolved, path.name
        return None, "explore report has no on-disk artifact_json with ce_extracted"
    return None, "not a CE photo artifact (missing ce_extracted) and not an explore report (runs)"


def _iter_ce_explore_json_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    out: list[Path] = []
    for p in root.iterdir():
        if not p.is_file() or p.suffix.lower() != ".json":
            continue
        if p.name.lower().startswith("ce_explore_"):
            out.append(p)
    return out
