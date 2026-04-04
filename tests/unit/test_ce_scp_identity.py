"""ce_scp_identity: CE headline → coarse player/year/# hints."""
import json
from pathlib import Path

import pytest

from backend.utils.ce_scp_identity import (
    enrich_identity_guess_from_ce_payload,
    find_latest_collectors_edge_photo_json,
    find_latest_usable_ce_json,
    guess_identity_from_ce_extracted,
    merged_from_ce_artifact,
    resolve_explicit_ce_json_path,
)


@pytest.mark.unit
def test_merged_from_ce_artifact_wraps_ce_extracted():
    inner = {"identity": {"analysis_headline": "X"}}
    assert merged_from_ce_artifact({"ce_extracted": inner}) is inner
    assert merged_from_ce_artifact(inner) is inner


@pytest.mark.unit
def test_guess_player_year_from_headline_and_candidates():
    merged = {
        "identity": {
            "analysis_headline": "Mike Trout 2011 Bowman Chrome Draft",
            "years_mentioned": [2011],
        },
        "card_number_candidates": ["US175"],
    }
    g = guess_identity_from_ce_extracted(merged)
    assert "Mike" in g["player_name"] and "Trout" in g["player_name"]
    assert g["card_year"] == 2011
    assert g["card_number"] == "US175"


@pytest.mark.unit
def test_enrich_fills_card_number_from_database_opportunity(tmp_path: Path):
    payload = {
        "database_opportunity": {
            "player_name": "Nick Solak",
            "card_year": 2020,
            "card_number": "FA-NS",
            "parallel": "Gold Refractor",
        }
    }
    g = {"player_name": "", "card_year": None, "card_number": "", "parallel": "Base", "card_set": ""}
    out = enrich_identity_guess_from_ce_payload(payload, g)
    assert out["player_name"] == "Nick Solak"
    assert out["card_year"] == 2020
    assert out["card_number"] == "FA-NS"
    assert out["parallel"] == "Gold Refractor"


@pytest.mark.unit
def test_find_latest_collectors_edge_skips_invalid_then_uses_older_valid(tmp_path: Path):
    good = {"ce_extracted": {"identity": {"analysis_headline": "x"}}}
    (tmp_path / "collectors_edge_old.json").write_text(json.dumps(good), encoding="utf-8")
    (tmp_path / "collectors_edge_new.json").write_text("{}", encoding="utf-8")
    found = find_latest_collectors_edge_photo_json(tmp_path)
    assert found is not None and found.name == "collectors_edge_old.json"


@pytest.mark.unit
def test_resolve_explicit_path_from_ce_explore_report(tmp_path: Path):
    inner = tmp_path / "inner.json"
    inner.write_text(json.dumps({"ce_extracted": {"identity": {"analysis_headline": "Z"}}}), encoding="utf-8")
    report = {"runs": [{"artifacts": [{"artifact_json": str(inner)}]}]}
    rep_path = tmp_path / "ce_explore_X.json"
    rep_path.write_text(json.dumps(report), encoding="utf-8")
    resolved, name = resolve_explicit_ce_json_path(rep_path)
    assert resolved == inner and name == "ce_explore_X.json"


@pytest.mark.unit
def test_find_latest_usable_follows_explore_when_no_photo_json(tmp_path: Path):
    inner = tmp_path / "inner.json"
    inner.write_text('{"ce_extracted": {"identity": {"analysis_headline": "X"}}}', encoding="utf-8")
    report = {
        "runs": [
            {
                "artifacts": [
                    {"artifact_json": str(inner)},
                ]
            }
        ]
    }
    (tmp_path / "ce_explore_R.json").write_text(json.dumps(report), encoding="utf-8")
    path, note = find_latest_usable_ce_json(tmp_path)
    assert path == inner
    assert "explore" in note
