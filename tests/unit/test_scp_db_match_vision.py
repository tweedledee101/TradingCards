"""scp_db_match vision-oriented helpers (no DB)."""
import pytest

from backend.services.scp_db_match import _normalize_card_number


@pytest.mark.unit
def test_normalize_card_number_strips_hash_and_space():
    assert _normalize_card_number("#US175") == "US175"
    assert _normalize_card_number("  #399 ") == "399"
    assert _normalize_card_number("") == ""
