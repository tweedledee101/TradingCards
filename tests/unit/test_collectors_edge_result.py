"""Unit tests for CE result parsing and pipeline-oriented analysis."""

from backend.utils.collectors_edge_result import (
    analyze_ce_for_pipeline,
    extract_ce_from_body_text,
    extract_ce_from_html,
    flat_parsed_for_legacy,
    merge_ce_extractions,
    _extract_card_number_candidates,
)

SAMPLE_BODY = """
Collectors Edge AI VALUATION Home Analysis Nick Solak 2019 Topps Finest Gold Refractor Rookie /50
Nick Solak 2019 Topps Finest Gold Refractor Rookie /50 Sports Super Short Print (/50) Gold Refractor Autograph
HOLD 31 Low Confidence No recent comparable sales found Analyzed Apr 4, 2026
D 20 Edge Score Weak Fair Market Value Raw
MEDIAN MARKET VALUE $65.00 AI estimate based on card attributes & market data
Insert code #FA-NS for matching. Card number is NUMBER and ATTRIBUTES noise here.
LOW $40.00 MEDIAN $65.00 HIGH $100.00 Few comparable sales available.
Market Trend Stable Down 30.0% over 90 days
Price History 2 data points
Recommendation HOLD Given the lack of recent sales data
Sources: eBay Sold Listings
"""

SAMPLE_HTML_FRAGMENT = (
    '<div class="text-gradient-gold-shimmer value-highlight">'
    '<span class="">$65.00</span></div>'
)


def test_extract_body_pricing_and_signals():
    ex = extract_ce_from_body_text(SAMPLE_BODY)
    assert ex["pricing"]["median_usd"] == 65.0
    assert ex["pricing"]["low_usd"] == 40.0
    assert ex["pricing"]["high_usd"] == 100.0
    assert ex["recommendation"]["confidence_pct"] == 31
    assert ex["edge"]["strength"] == "Weak"
    assert ex["comparables"]["no_recent_comparable_sales"] is True
    assert ex["card_signals"]["is_autograph"] is True
    assert ex["card_signals"]["is_rookie"] is True
    assert 2019 in (ex["identity"].get("years_mentioned") or [])
    assert 2026 not in (ex["identity"].get("years_mentioned") or [])
    assert "FA-NS" in (ex.get("card_number_candidates") or [])
    noise = {"NUMBER", "ATTRIBUTES", "IS"}
    assert noise.isdisjoint(set(ex.get("card_number_candidates") or []))


def test_html_median_supplement():
    sup = extract_ce_from_html(SAMPLE_HTML_FRAGMENT)
    assert sup.get("html_median_usd") == 65.0


def test_merge_and_flat_legacy():
    body = extract_ce_from_body_text(SAMPLE_BODY)
    merged = merge_ce_extractions(body, {})
    flat = flat_parsed_for_legacy(merged)
    assert flat["median_usd"] == 65.0
    assert flat["edge_strength"] == "Weak"


def test_analyze_with_pipeline_match():
    body = extract_ce_from_body_text(SAMPLE_BODY)
    merged = merge_ce_extractions(body, {})
    pipe = {
        "player_name": "Nick Solak",
        "card_year": 2019,
        "card_number": "FA-NS",
        "parallel": "Gold Refractor",
        "ebay_title": "2020 TOPPS FINEST NICK SOLAK GOLD",
        "scp_price": 60.0,
    }
    a = analyze_ce_for_pipeline(merged, pipeline=pipe)
    assert any("Player name" in x for x in a["verification_points"])
    assert a["matching_hints"].get("card_number_alignment") == "possible_match"
    assert a["pricing_context"].get("ce_median_over_scp_ungraded") is not None
    assert abs(a["pricing_context"]["ce_median_over_scp_ungraded"] - (65.0 / 60.0)) < 0.01


def test_year_fuzzy_listing_vs_product_year():
    body = extract_ce_from_body_text(SAMPLE_BODY)
    merged = merge_ce_extractions(body, {})
    a = analyze_ce_for_pipeline(
        merged,
        pipeline={"card_year": 2020, "player_name": "Nick Solak"},
    )
    assert a["matching_hints"].get("year_alignment") == "fuzzy_match"
    assert "ce_year_mismatch_risk" not in a["suggested_qa_flags"]


def test_hyphen_prose_not_treated_as_catalog_number():
    s = "MID-SEASON ALL-STAR ON-CARD ALL-SEC CALL-UP Gold #FA-NS variant BA-DG1"
    c = _extract_card_number_candidates(s)
    assert "MID-SEASON" not in c
    assert "ALL-STAR" not in c
    assert "ON-CARD" not in c
    assert "ALL-SEC" not in c
    assert "CALL-UP" not in c
    assert "FA-NS" in c
    assert "BA-DG1" in c


def test_card_number_listing_title_when_ce_has_no_insert():
    body = extract_ce_from_body_text(
        "Analysis Test Player Sports Super Print Gold Analyzed Apr 4, 2026 "
        "MEDIAN MARKET VALUE $10.00 LOW $5.00 MEDIAN $10.00 HIGH $15.00"
    )
    merged = merge_ce_extractions(body, {})
    assert not merged.get("card_number_candidates")
    a = analyze_ce_for_pipeline(
        merged,
        pipeline={
            "player_name": "Test Player",
            "card_number": "FA-NS",
            "ebay_title": "2020 TOPPS #FA-NS GOLD REFRACTOR",
        },
    )
    assert a["matching_hints"].get("card_number_alignment") == "listing_matches_pipeline_ce_silent"


def test_analyze_player_mismatch_flag():
    body = extract_ce_from_body_text(SAMPLE_BODY)
    merged = merge_ce_extractions(body, {})
    a = analyze_ce_for_pipeline(
        merged,
        pipeline={"player_name": "Aaron Judge", "card_year": 2019},
    )
    assert "ce_player_mismatch_risk" in a["suggested_qa_flags"]
