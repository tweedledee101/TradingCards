"""Free-text card number tokens for eBay listings."""
import pytest

from backend.utils.listing_card_identity import card_number_tokens_from_free_text


@pytest.mark.unit
def test_hash_and_verbal_order():
    t = card_number_tokens_from_free_text("Lot Card No. 150 insert #Z-12")
    assert "Z-12" in t
    assert "150" in t
    assert t.index("Z-12") < t.index("150")  # # before Card No. scan order


@pytest.mark.unit
def test_cn_catalog():
    assert "USC35" in card_number_tokens_from_free_text("CN: USC35 mint")
    assert "M1" in card_number_tokens_from_free_text("catalog # M1 rookie")


@pytest.mark.unit
def test_empty():
    assert card_number_tokens_from_free_text("") == []
    assert card_number_tokens_from_free_text(None) == []
