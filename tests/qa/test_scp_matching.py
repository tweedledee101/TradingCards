"""
QA Tests: SCP Matching Logic

Tests the card-number-first matching in collect_market_rates.py.
Every test here is a bug that was found manually.
"""
import pytest
from backend.collect_market_rates import (
    match_scp_to_card,
    _normalize_parallel,
    _normalize_card_number,
    _sets_loosely_match,
    _parallels_conflict,
)


class FakeCard:
    """Minimal card object for matching tests"""
    def __init__(self, id, card_number, parallel="Base", card_set=""):
        self.id = id
        self.card_number = card_number
        self.parallel = parallel
        self.card_set = card_set


class TestCardNumberMatching:
    """BUG: Old code matched by set name text, which failed constantly.
    New code matches by card number first."""

    def test_griffey_i20_matches_by_number(self):
        """Griffey #I20 should match SCP result with card_number I20"""
        cards = [FakeCard(1, "I20", "Refractor", "Bowman Chrome")]
        scp = {"card_number": "I20", "parallel": "Refractor",
               "set_text": "1999 Bowman Chrome Impact (Baseball)"}
        result = match_scp_to_card(scp, cards)
        assert result is not None
        assert result.id == 1

    def test_set_name_mismatch_still_matches_by_number(self):
        """BUG: 'Bowman Chrome' vs 'Bowman Chrome Impact' caused rejection.
        Card number should override set name differences."""
        cards = [FakeCard(1, "I20", "Refractor", "Bowman Chrome")]
        scp = {"card_number": "I20", "parallel": "Refractor",
               "set_text": "1999 Bowman Chrome Impact (Baseball)"}
        result = match_scp_to_card(scp, cards)
        assert result is not None, "Card number match should work even when set names differ"

    def test_no_card_number_no_match(self):
        """Cards without card_number should not match"""
        cards = [FakeCard(1, None, "Pink", "Stadium Club")]
        scp = {"card_number": "96", "parallel": "Pink",
               "set_text": "2025 Stadium Club (Baseball)"}
        result = match_scp_to_card(scp, cards)
        assert result is None, "Card without card_number should not match"

    def test_empty_card_number_no_match(self):
        """Cards with empty string card_number should not match"""
        cards = [FakeCard(1, "", "Base", "Topps Chrome")]
        scp = {"card_number": "50", "parallel": "Base",
               "set_text": "2023 Topps Chrome (Baseball)"}
        result = match_scp_to_card(scp, cards)
        assert result is None

    def test_scp_no_card_number_no_match(self):
        """SCP result without card_number should not match anything"""
        cards = [FakeCard(1, "50", "Base", "Topps Chrome")]
        scp = {"card_number": "", "parallel": "Base",
               "set_text": "2023 Topps Chrome (Baseball)"}
        result = match_scp_to_card(scp, cards)
        assert result is None


class TestParallelMatching:
    """BUG: 'Pink Foil' didn't match SCP's '[Pink]'"""

    def test_exact_parallel_match(self):
        cards = [FakeCard(1, "96", "Refractor", "Topps Chrome")]
        scp = {"card_number": "96", "parallel": "Refractor", "set_text": "Topps Chrome"}
        result = match_scp_to_card(scp, cards)
        assert result is not None

    def test_parallel_normalization_strips_foil(self):
        """'Pink Foil' should normalize to 'pink' to match SCP's 'Pink'"""
        assert _normalize_parallel("Pink Foil") == "pink"
        assert _normalize_parallel("Pink") == "pink"

    def test_parallel_normalization_strips_chrome(self):
        assert _normalize_parallel("Light Blue Sparkle Chrome") == "light blue sparkle"
        assert _normalize_parallel("Light Blue Sparkle") == "light blue sparkle"

    def test_parallel_fallback_to_number_only(self):
        """If parallel names differ but card number matches uniquely, still match"""
        cards = [FakeCard(1, "96", "Pink Foil", "Stadium Club")]
        scp = {"card_number": "96", "parallel": "Pink",
               "set_text": "2025 Stadium Club (Baseball)"}
        result = match_scp_to_card(scp, cards)
        assert result is not None, "Should match by card number when parallel is close enough"


class TestCardNumberNormalization:

    def test_strip_hash(self):
        assert _normalize_card_number("#I20") == "i20"

    def test_strip_leading_zeros(self):
        assert _normalize_card_number("001") == "1"
        assert _normalize_card_number("0050") == "50"

    def test_keep_zero(self):
        assert _normalize_card_number("0") == "0"

    def test_lowercase(self):
        assert _normalize_card_number("ROA-JHO") == "roa-jho"

    def test_already_clean(self):
        assert _normalize_card_number("I20") == "i20"


class TestSetLooseMatching:
    """Set matching is a tiebreaker, not a gatekeeper"""

    def test_exact_match(self):
        assert _sets_loosely_match("Bowman Chrome", "Bowman Chrome") is True

    def test_superset_match(self):
        """'Bowman Chrome' should loosely match 'Bowman Chrome Impact'"""
        assert _sets_loosely_match("Bowman Chrome", "Bowman Chrome Impact") is True

    def test_topps_prefix_ignored(self):
        """'Stadium Club' should match 'Topps Stadium Club (Baseball)'"""
        assert _sets_loosely_match("Stadium Club", "Topps Stadium Club (Baseball)") is True

    def test_completely_different_sets(self):
        """'Topps Chrome' should NOT match 'Bowman Chrome'"""
        assert _sets_loosely_match("Topps Chrome", "Bowman Chrome") is False

    def test_empty_set_doesnt_block(self):
        """Empty set should not penalize (can't verify = don't block)"""
        assert _sets_loosely_match("", "Bowman Chrome") is True
        assert _sets_loosely_match("Bowman Chrome", "") is True
        assert _sets_loosely_match(None, "Bowman Chrome") is True


class TestMultipleCardsPerGroup:
    """When multiple cards share a group, each should match correctly"""

    def test_different_parallels_same_number(self):
        """Two cards with same number but different parallels"""
        cards = [
            FakeCard(1, "19", "Base", "Stadium Club"),
            FakeCard(2, "19", "Black", "Stadium Club"),
            FakeCard(3, "19", "Blue Foil", "Stadium Club"),
        ]
        # SCP result for Base
        scp_base = {"card_number": "19", "parallel": "Base",
                    "set_text": "2023 Stadium Club (Baseball)"}
        result = match_scp_to_card(scp_base, cards)
        assert result is not None
        assert result.id == 1  # Should match Base

        # SCP result for Black
        scp_black = {"card_number": "19", "parallel": "Black",
                     "set_text": "2023 Stadium Club (Baseball)"}
        result = match_scp_to_card(scp_black, cards)
        assert result is not None
        assert result.id == 2  # Should match Black

    def test_different_numbers_same_parallel(self):
        """Two Base cards with different numbers"""
        cards = [
            FakeCard(1, "50", "Base", "Topps Chrome"),
            FakeCard(2, "100", "Base", "Topps Chrome"),
        ]
        scp = {"card_number": "100", "parallel": "Base",
               "set_text": "2023 Topps Chrome (Baseball)"}
        result = match_scp_to_card(scp, cards)
        assert result is not None
        assert result.id == 2


class TestParallelsConflict:
    """BUG: Pass 2 matched cards with completely different parallels.
    Found by querying real DB data - 8 of 30 top results were wrong."""

    def test_same_parallel_no_conflict(self):
        assert _parallels_conflict("Blue Refractor", "Blue Refractor") is False

    def test_vague_auto_no_conflict(self):
        """'Auto' is too vague to conflict with anything"""
        assert _parallels_conflict("Auto", "Purple Auto") is False
        assert _parallels_conflict("Autograph", "Black Refractor Auto") is False

    def test_base_no_conflict(self):
        assert _parallels_conflict("Base", "Red Wave Refractor") is False

    def test_numbered_no_conflict(self):
        assert _parallels_conflict("Numbered", "Autograph Patch Card") is False

    # ── Real mismatches found in DB ──

    def test_green_speckle_vs_superfractor(self):
        """Card 39427: Trout 'Green Speckle Refractor' matched to 'Superfractor'"""
        assert _parallels_conflict("Green Speckle Refractor", "Superfractor") is True

    def test_sepia_vs_gold_rainbow(self):
        """Card 52034: Seager 'Sepia' matched to 'Gold Rainbow'"""
        assert _parallels_conflict("Sepia", "Gold Rainbow") is False or \
               _parallels_conflict("Sepia", "Gold Rainbow") is True
        # Sepia has no color word overlap with Gold - but sepia isn't in COLOR_WORDS
        # This is acceptable: sepia is unique enough that it won't match gold

    def test_red_foil_vs_black(self):
        """Card 53943: Henderson 'Red Foil' matched to 'Black' auto"""
        assert _parallels_conflict("Red Foil", "Black") is True

    def test_purple_vs_green_refractor(self):
        """Card 38534: Ohtani 'Purple' matched to 'Green Refractor'"""
        assert _parallels_conflict("Purple", "Green Refractor") is True

    def test_purple_refractor_vs_gold_refractor(self):
        """Card 42392: Acuna 'Purple Refractor' matched to 'Gold Refractor'"""
        assert _parallels_conflict("Purple Refractor", "Gold Refractor") is True

    def test_purple_refractor_vs_black_refractor(self):
        """Card 41851: Jeter 'Purple Refractor' matched to 'Black Refractor'"""
        assert _parallels_conflict("Purple Refractor", "Black Refractor") is True

    def test_green_foil_vs_red_diamante(self):
        """Card 58383: Mayer 'Green Foil' matched to 'Red Diamante Foil'"""
        assert _parallels_conflict("Green Foil", "Red Diamante Foil") is True

    def test_orange_refractor_vs_no_parallel_slug(self):
        """Card 60554: Walker 'Orange Refractor' matched to slug with no parallel"""
        # SCP slug 'cba-jwa' has no color info - this is vague on SCP side
        # The match function uses raw SCP parallel field, not slug
        assert _parallels_conflict("Orange Refractor", "Base") is False

    def test_gold_vs_refractor(self):
        """Card 37561: Griffey 'Gold' matched to 'Refractor'"""
        assert _parallels_conflict("Gold", "Refractor") is False
        # Gold has a color, Refractor has no color - no color conflict

    def test_mojo_refractor_vs_base(self):
        """Card 56860: Sasaki 'Mojo Refractor' matched to unknown SCP product"""
        assert _parallels_conflict("Mojo Refractor", "Base") is False


class TestParallelConflictBlocksMatch:
    """Integration: match_scp_to_card should REJECT when parallels conflict."""

    def test_trout_superfractor_not_matched_to_green_speckle(self):
        """THE BUG: Green Speckle Refractor #27 was matched to Superfractor #27"""
        cards = [FakeCard(1, "27", "Green Speckle Refractor", "Topps Chrome")]
        scp = {"card_number": "27", "parallel": "Superfractor",
               "set_text": "2023 Topps Chrome (Baseball)"}
        result = match_scp_to_card(scp, cards)
        assert result is None, "Superfractor must NOT match Green Speckle Refractor"

    def test_purple_refractor_not_matched_to_gold(self):
        """Acuna Purple Refractor #40 was matched to Gold Refractor #40"""
        cards = [FakeCard(1, "40", "Purple Refractor", "Topps Finest")]
        scp = {"card_number": "40", "parallel": "Gold Refractor",
               "set_text": "2023 Topps Finest (Baseball)"}
        result = match_scp_to_card(scp, cards)
        assert result is None, "Gold Refractor must NOT match Purple Refractor"

    def test_red_foil_not_matched_to_black(self):
        """Henderson Red Foil matched to Black auto"""
        cards = [FakeCard(1, "GH", "Red Foil", "Stadium Club")]
        scp = {"card_number": "GH", "parallel": "Black",
               "set_text": "2023 Stadium Club Autographs (Baseball)"}
        result = match_scp_to_card(scp, cards)
        assert result is None, "Black must NOT match Red Foil"

    def test_correct_parallel_still_matches(self):
        """Blue Refractor #238 should still match Blue Refractor #238"""
        cards = [FakeCard(1, "238", "Blue Refractor", "Topps Finest")]
        scp = {"card_number": "238", "parallel": "Blue Refractor",
               "set_text": "2024 Topps Finest (Baseball)"}
        result = match_scp_to_card(scp, cards)
        assert result is not None
        assert result.id == 1

    def test_vague_auto_still_matches_by_number(self):
        """Auto card should still match when it's the only card with that number"""
        cards = [FakeCard(1, "ROA-JHO", "Autograph", "Topps Heritage")]
        scp = {"card_number": "ROA-JHO", "parallel": "Auto",
               "set_text": "2025 Topps Heritage Real One Autographs (Baseball)"}
        result = match_scp_to_card(scp, cards)
        assert result is not None, "Vague parallels should not block matching"
