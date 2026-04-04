"""
Parse Collectors Edge AI **result** pages (photo valuation) into structured data and
pipeline-oriented analysis: identity hints, pricing bands, confidence signals, and
cross-checks against our ``opportunities`` / SCP-style identity.

UI strings change over time; this module is defensive and returns partial dicts.
"""

from __future__ import annotations

import re
from typing import Any

from backend.utils.listing_card_identity import card_number_tokens_from_free_text

# Tokens CE's UI copy adds around "card number / attributes" — not catalog numbers.
_CE_CATALOG_STOPWORDS = frozenset(
    """
    number card sports attributes values value details appears allows is on of at to the and
    for with auto raw graded mint near this that from your our has have been were into
    about when what which while also only over such than then them these those very will
    just like into each more most much some time very want better results try adding name
    variant year set market trend stable based data ebay sold listings sources consider
    checking directly unknown past history points investment grade recommendation hold sell
    buy super short print gold refractor rookie autograph PSA BGS SGC CGC ungraded
    professional maximum protection condition liquidity specific available difficult assess
    establish making """.split()
)

# Hyphen phrases CE uses in copy (variant / format), not catalog insert codes like FA-NS.
_CE_HYPHEN_PROSE = frozenset(
    """
    mid-season all-star on-card off-season full-season game-used first-year high-end
    low-number short-print super-short all-sec call-up walk-off pick-up big-league
    """.split()
)

# --- extraction -----------------------------------------------------------------


def _analyzed_year_from_text(s: str) -> int | None:
    m = re.search(r"Analyzed\s+[A-Za-z]{3}\s+\d{1,2},\s+(\d{4})\b", s)
    return int(m.group(1)) if m else None


def _plausible_card_catalog_token(t: str) -> bool:
    """Filter CE boilerplate; keep insert codes (FA-NS) and #123-style fragments."""
    if not t or len(t) > 22:
        return False
    u = t.strip()
    low = u.lower()
    if low in _CE_CATALOG_STOPWORDS:
        return False
    if low in _CE_HYPHEN_PROSE:
        return False
    # Insert / Leaf style: XX-YY, BA-DG1, FA-NS
    if re.match(r"^[A-Za-z]{1,4}-[A-Za-z0-9]{1,10}$", u):
        left, _, right = u.partition("-")
        if left.isalpha() and right.isalpha() and not any(ch.isdigit() for ch in u):
            # Long all-letter chunks (e.g. MID-SEASON, ALL-STAR) are almost never insert codes.
            if len(left) >= 3 and len(right) >= 4:
                return False
        return True
    if any(ch.isdigit() for ch in u) and re.match(r"^[A-Za-z0-9#/.-]+$", u):
        return True
    # Short mixed alphanumeric (e.g. RC3) but not plain English words
    if len(u) <= 5 and not u.isalpha():
        return True
    return False


def _extract_card_number_candidates(s: str) -> list[str]:
    found: list[str] = []
    for pat in (
        r"#\s*([A-Za-z]{1,4}-[A-Za-z0-9]{1,10})\b",
        r"\b#\s*([A-Za-z0-9]{1,6}-[A-Za-z0-9]{1,8})\b",
        r"\b([A-Za-z]{1,4}-[A-Za-z0-9]{1,10})\b",
    ):
        for mm in re.finditer(pat, s):
            t = mm.group(1).strip()
            if _plausible_card_catalog_token(t):
                found.append(t.upper() if t.replace("-", "").isalnum() else t)
    seen: set[str] = set()
    out: list[str] = []
    for t in found:
        k = t.lower()
        if k not in seen:
            seen.add(k)
            out.append(t)
    return out[:12]


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def extract_ce_from_html(html: str | None) -> dict[str, Any]:
    """Supplement text extraction with patterns visible in saved CE HTML (React SSR)."""
    if not html:
        return {}
    out: dict[str, Any] = {}
    # Primary median often in AnimatedCounter / value-highlight block
    m = re.search(
        r'value-highlight[^>]*>.*?>\s*\$([\d,]+\.\d{2})\s*<',
        html,
        re.I | re.DOTALL,
    )
    if m:
        out["html_median_usd"] = float(m.group(1).replace(",", ""))
    # Any labeled grid lows/highs sometimes mirror body text
    prices = re.findall(r">\s*\$([\d,]+\.\d{2})\s*<", html)
    if len(prices) >= 3:
        nums = sorted({float(p.replace(",", "")) for p in prices})
        if nums:
            out["html_price_samples_sorted_usd"] = nums[:12]
    return out


def extract_ce_from_body_text(text: str) -> dict[str, Any]:
    """
    Pull structured fields from ``document.body`` innerText on CE ``/result``.

    Returns a nested dict: pricing, recommendation, confidence, card_signals, narrative, etc.
    """
    s = _collapse_ws(text)
    out: dict[str, Any] = {"raw_text_length": len(text or "")}

    # --- pricing ---
    pricing: dict[str, Any] = {}
    m = re.search(
        r"\bMEDIAN(?:\s+MARKET\s+VALUE)?\s*\$?\s*([\d,]+\.\d{2})\b",
        s,
        re.I,
    )
    if m:
        pricing["median_usd"] = float(m.group(1).replace(",", ""))
    m = re.search(r"\bLOW\s*\$?\s*([\d,]+\.\d{2})", s, re.I)
    if m:
        pricing["low_usd"] = float(m.group(1).replace(",", ""))
    m = re.search(r"\bHIGH\s*\$?\s*([\d,]+\.\d{2})", s, re.I)
    if m:
        pricing["high_usd"] = float(m.group(1).replace(",", ""))
    if (
        pricing.get("low_usd") is not None
        and pricing.get("high_usd") is not None
        and pricing.get("median_usd")
    ):
        lo, hi, med = pricing["low_usd"], pricing["high_usd"], pricing["median_usd"]
        if med > 0:
            pricing["band_width_pct_of_median"] = round((hi - lo) / med * 100.0, 2)
    out["pricing"] = pricing

    # --- recommendation / investment ---
    rec: dict[str, Any] = {}
    m = re.search(r"(\d+)\s*%\s*confidence", s, re.I)
    if m:
        rec["confidence_pct"] = int(m.group(1))
    else:
        m2 = re.search(r"\b(HOLD|BUY|SELL)\s+(\d+)\b", s, re.I)
        if m2 and m2.group(2).isdigit():
            rec["recommendation_lead"] = m2.group(1).upper()
            rec["confidence_pct"] = int(m2.group(2))
    m = re.search(r"Recommendation\s+(HOLD|BUY|SELL)", s, re.I)
    if m:
        rec["recommendation"] = m.group(1).upper()
    m = re.search(r"\b(Low|Medium|Moderate|High)\s+Confidence\b", s, re.I)
    if m:
        rec["confidence_tier"] = m.group(1).title()
    out["recommendation"] = rec

    edge: dict[str, Any] = {}
    m = re.search(r"Edge Score\s+(Weak|Moderate|Strong)", s, re.I)
    if m:
        edge["strength"] = m.group(1)
    m = re.search(r"\bD\s+(\d+)\s+Edge Score\b", s, re.I)
    if m:
        edge["score_0_to_100_guess"] = int(m.group(1))
    out["edge"] = edge

    m = re.search(r"Analyzed\s+([A-Za-z]{3}\s+\d{1,2},\s+\d{4})", s)
    if m:
        out["analyzed_at"] = m.group(1)

    # --- identity / product type ---
    identity: dict[str, Any] = {}
    m = re.search(r"Analysis\s+(.+?)\s+Sports\s", s, re.I)
    headline = m.group(1).strip()[:400] if m else ""
    if headline:
        identity["analysis_headline"] = headline
    analyzed_y = _analyzed_year_from_text(s)
    # Years in full body, excluding "Analyzed Mon DD, YYYY" (stops 2026-style noise).
    all_years = {int(x) for x in re.findall(r"\b(19[89]\d|20[0-3]\d)\b", s)}
    if analyzed_y is not None:
        all_years.discard(analyzed_y)
    years = sorted(all_years)
    if years:
        identity["years_mentioned"] = years
    if headline:
        hy = {int(x) for x in re.findall(r"\b(19[89]\d|20[0-3]\d)\b", headline)}
        if analyzed_y is not None:
            hy.discard(analyzed_y)
        if hy:
            identity["years_in_analysis_headline"] = sorted(hy)
    # Serial / print run
    serials = re.findall(r"/(\d{1,4})\b", s)
    if serials:
        identity["serial_denominators_mentioned"] = sorted(
            {int(x) for x in serials if int(x) <= 10000},
        )[:8]
    m = re.search(r"\((/\d+)\)", s)
    if m:
        identity["serial_slash_notation"] = m.group(1)
    out["identity"] = identity

    card_signals: dict[str, Any] = {
        "is_autograph": bool(re.search(r"\bAuto(graph)?\b", s, re.I)),
        "is_rookie": bool(re.search(r"\bRookie\b|\bRC\b", s, re.I)),
        "is_refractor": bool(re.search(r"Refractor", s, re.I)),
        "is_gold_parallel": bool(re.search(r"\bGold\b", s, re.I)),
        "short_print_mentioned": bool(
            re.search(r"Super Short Print|Short Print|SSP\b", s, re.I)
        ),
        "graded_mentioned": bool(re.search(r"\bPSA\b|\bBGS\b|\bSGC\b|\bCGC\b", s, re.I)),
        "raw_mentioned": bool(re.search(r"\braw\b|\bungraded\b", s, re.I)),
    }
    out["card_signals"] = card_signals

    comps: dict[str, Any] = {}
    comps["no_recent_comparable_sales"] = bool(
        re.search(r"No recent comparable sales", s, re.I)
    )
    comps["few_comparable_sales"] = bool(re.search(r"Few comparable sales", s, re.I))
    m = re.search(r"Sources:\s*([^.]+)", s, re.I)
    if m:
        comps["sources_line"] = m.group(1).strip()[:300]
    out["comparables"] = comps

    trend: dict[str, Any] = {}
    m = re.search(r"Market Trend\s+(\w+)", s, re.I)
    if m:
        trend["label"] = m.group(1)
    m = re.search(
        r"(Down|Up)\s+([\d.]+)%\s+over\s+(\d+)\s*days?",
        s,
        re.I,
    )
    if m:
        trend["direction"] = m.group(1).title()
        trend["pct_change"] = float(m.group(2))
        trend["window_days"] = int(m.group(3))
    out["market_trend"] = trend

    ph = re.search(r"Price History\s+(\d+)\s+data points?", s, re.I)
    if ph:
        out["price_history"] = {"data_points_mentioned": int(ph.group(1))}

    m = re.search(r"Recommendation\s+(HOLD|BUY|SELL)(.{20,800}?)(?=Investment Grade|Price History|Sources:|$)", s, re.I | re.DOTALL)
    if m:
        out["recommendation_narrative"] = _collapse_ws(m.group(2))[:1200]

    cn = _extract_card_number_candidates(s)
    if cn:
        out["card_number_candidates"] = cn

    return out


def merge_ce_extractions(
    body: dict[str, Any],
    html_sup: dict[str, Any],
) -> dict[str, Any]:
    merged = {"from_body_text": body, "from_html": html_sup}
    # Prefer body median; fall back to HTML scrape
    pricing = dict(body.get("pricing") or {})
    if pricing.get("median_usd") is None and html_sup.get("html_median_usd") is not None:
        pricing["median_usd"] = html_sup["html_median_usd"]
        pricing["median_source"] = "html_fallback"
    merged["pricing"] = pricing
    merged["recommendation"] = body.get("recommendation") or {}
    merged["edge"] = body.get("edge") or {}
    merged["identity"] = body.get("identity") or {}
    merged["card_signals"] = body.get("card_signals") or {}
    merged["comparables"] = body.get("comparables") or {}
    merged["market_trend"] = body.get("market_trend") or {}
    if body.get("price_history"):
        merged["price_history"] = body["price_history"]
    if body.get("recommendation_narrative"):
        merged["recommendation_narrative"] = body["recommendation_narrative"]
    if body.get("card_number_candidates"):
        merged["card_number_candidates"] = body["card_number_candidates"]
    if body.get("analyzed_at"):
        merged["analyzed_at"] = body["analyzed_at"]
    merged["raw_text_length"] = body.get("raw_text_length", 0)
    return merged


def flat_parsed_for_legacy(merged: dict[str, Any]) -> dict[str, Any]:
    """Flat dict compatible with earlier CE JSON consumers."""
    p = merged.get("pricing") or {}
    r = merged.get("recommendation") or {}
    e = merged.get("edge") or {}
    ident = merged.get("identity") or {}
    out: dict[str, Any] = {"raw_text_length": merged.get("raw_text_length", 0)}
    for k in ("median_usd", "low_usd", "high_usd"):
        if p.get(k) is not None:
            out[k] = p[k]
    if r.get("confidence_pct") is not None:
        out["confidence_pct"] = r["confidence_pct"]
    if r.get("recommendation_lead"):
        out["recommendation_lead"] = r["recommendation_lead"]
    if r.get("recommendation"):
        out["recommendation"] = r["recommendation"]
    if e.get("strength"):
        out["edge_strength"] = e["strength"]
    if merged.get("analyzed_at"):
        out["analyzed_at"] = merged["analyzed_at"]
    ah = ident.get("analysis_headline")
    if ah:
        out["card_identity_guess"] = ah[:240]
    return out


# --- pipeline analysis ----------------------------------------------------------


def _norm_tokens(s: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", s.lower()) if len(t) >= 3}


def analyze_ce_for_pipeline(
    merged: dict[str, Any],
    *,
    pipeline: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Turn CE extraction into **actionable** signals for matching and QA.

    ``pipeline`` typically includes opportunity fields: player_name, card_year, card_set,
    card_number, parallel, ebay_title, scp_price (optional).
    """
    analysis: dict[str, Any] = {
        "hard_facts": [],
        "verification_points": [],
        "additional_indicators": [],
        "matching_hints": {},
        "pricing_context": {},
        "suggested_qa_flags": [],
    }

    pricing = merged.get("pricing") or {}
    rec = merged.get("recommendation") or {}
    edge = merged.get("edge") or {}
    comps = merged.get("comparables") or {}
    signals = merged.get("card_signals") or {}
    ident = merged.get("identity") or {}
    trend = merged.get("market_trend") or {}

    med = pricing.get("median_usd")
    if med is not None:
        analysis["hard_facts"].append(f"CE median fair-market estimate: ${med:.2f} USD")
    if pricing.get("low_usd") is not None and pricing.get("high_usd") is not None:
        analysis["hard_facts"].append(
            f"CE low/high band: ${pricing['low_usd']:.2f} – ${pricing['high_usd']:.2f}"
        )
        if pricing.get("band_width_pct_of_median") is not None:
            analysis["additional_indicators"].append(
                f"CE band width ≈ {pricing['band_width_pct_of_median']}% of median "
                "(wide band often means thin comps)"
            )

    if rec.get("confidence_pct") is not None:
        analysis["hard_facts"].append(f"CE model confidence: {rec['confidence_pct']}%")
    if rec.get("confidence_tier"):
        analysis["verification_points"].append(
            f"CE labels confidence tier: {rec['confidence_tier']}"
        )
    if edge.get("strength"):
        analysis["verification_points"].append(f"CE edge score bucket: {edge['strength']}")

    if comps.get("no_recent_comparable_sales"):
        analysis["verification_points"].append(
            "CE: no recent comparable sales — treat identity/pricing as unverified vs live market"
        )
        analysis["suggested_qa_flags"].append("ce_no_recent_comps")
    if comps.get("few_comparable_sales"):
        analysis["suggested_qa_flags"].append("ce_few_comps")

    if signals.get("is_autograph"):
        analysis["matching_hints"]["expect_autograph"] = True
    if signals.get("is_rookie"):
        analysis["matching_hints"]["expect_rookie"] = True
    if signals.get("short_print_mentioned") or ident.get("serial_denominators_mentioned"):
        analysis["matching_hints"]["expect_serial_limited"] = True
    if ident.get("years_mentioned"):
        analysis["matching_hints"]["ce_years_mentioned"] = ident["years_mentioned"]

    ah = (ident.get("analysis_headline") or "").strip()
    if ah:
        analysis["matching_hints"]["ce_identity_text"] = ah[:500]

    cn_cands = merged.get("card_number_candidates") or []
    if cn_cands:
        analysis["matching_hints"]["card_number_candidates_from_ce"] = cn_cands

    # Trend as secondary indicator (not ground truth)
    if trend.get("label"):
        analysis["additional_indicators"].append(f"CE market trend label: {trend['label']}")
    if trend.get("pct_change") is not None and trend.get("window_days"):
        analysis["additional_indicators"].append(
            f"CE price history note: {trend.get('direction', '')} {trend['pct_change']}% "
            f"over {trend['window_days']}d (narrative; verify with sold comps)"
        )

    if not pipeline:
        analysis["pricing_context"]["note"] = "No pipeline row supplied — only CE-side signals"
        return analysis

    ebay_title = (pipeline.get("ebay_title") or "").strip()
    player = (pipeline.get("player_name") or "").strip()
    p_year = pipeline.get("card_year")
    p_num = (pipeline.get("card_number") or "").strip()
    p_par = (pipeline.get("parallel") or "").strip()
    scp = pipeline.get("scp_price")

    blob = _collapse_ws(f"{ah} {ebay_title}").lower()
    ce_years = set(ident.get("years_mentioned") or [])
    headline_years = set(ident.get("years_in_analysis_headline") or [])

    if player:
        pl = player.lower()
        if pl in blob or (len(pl) >= 4 and pl.split()[0] in blob):
            analysis["verification_points"].append(
                "Player name from pipeline appears consistent with CE analysis/title text"
            )
            analysis["matching_hints"]["player_alignment"] = "likely_match"
        else:
            analysis["verification_points"].append(
                "Mismatch risk: pipeline player not clearly present in CE identity text — "
                "wrong image, wrong CE parse, or multi-player lot"
            )
            analysis["matching_hints"]["player_alignment"] = "review"
            analysis["suggested_qa_flags"].append("ce_player_mismatch_risk")

    if p_year is not None and (ce_years or headline_years):
        py = int(p_year)
        primary = headline_years if headline_years else ce_years
        if py in ce_years or py in headline_years:
            analysis["verification_points"].append(
                f"Year {p_year} appears in CE identity text — aligns with pipeline card_year"
            )
            analysis["matching_hints"]["year_alignment"] = "match"
        elif any(abs(py - y) <= 1 for y in primary):
            analysis["verification_points"].append(
                f"Year {p_year} is within ±1 of CE headline year(s) {sorted(primary)} — "
                "typical when listing uses release year and CE uses product/copyright year"
            )
            analysis["matching_hints"]["year_alignment"] = "fuzzy_match"
        else:
            analysis["verification_points"].append(
                f"Year check: pipeline {p_year}, CE years in headline {sorted(headline_years) or 'n/a'}, "
                f"body {sorted(ce_years)} — verify product vs listing year"
            )
            analysis["matching_hints"]["year_alignment"] = "review"
            analysis["suggested_qa_flags"].append("ce_year_mismatch_risk")

    if p_num:
        pn = p_num.upper().replace(" ", "")
        listing_tokens = card_number_tokens_from_free_text(ebay_title) if ebay_title else []
        if listing_tokens:
            analysis["matching_hints"]["card_number_tokens_from_listing_title"] = listing_tokens[:10]
        title_norms = {t.upper().replace(" ", "") for t in listing_tokens}
        in_listing_title = pn in title_norms or any(
            pn == t.upper().replace(" ", "") for t in listing_tokens
        )
        ce_hit = False
        if cn_cands:
            ce_hit = any(
                pn == c.upper().replace(" ", "")
                or pn in c.upper().replace(" ", "")
                or c.upper().replace(" ", "") in pn
                for c in cn_cands
            )
        if ce_hit:
            analysis["verification_points"].append(
                "Card # token from pipeline loosely matches CE-extracted candidates"
            )
            analysis["matching_hints"]["card_number_alignment"] = "possible_match"
        elif in_listing_title:
            analysis["verification_points"].append(
                f"Pipeline card # {p_num!r} matches listing title tokens; CE text did not surface "
                "that insert code (CE hyphen tokens are often variant prose, not catalog #)."
            )
            analysis["matching_hints"]["card_number_alignment"] = "listing_matches_pipeline_ce_silent"
        elif cn_cands:
            analysis["verification_points"].append(
                f"Card #: pipeline {p_num!r} vs CE candidates {cn_cands[:5]} — verify parallel/set"
            )
            analysis["matching_hints"]["card_number_alignment"] = "review"
        else:
            analysis["verification_points"].append(
                f"Pipeline card # {p_num!r}; no catalog-style # candidates parsed from CE body."
            )
            analysis["matching_hints"]["card_number_alignment"] = "review"

    if p_par and ah:
        ptoks = _norm_tokens(p_par)
        atoks = _norm_tokens(ah)
        overlap = ptoks & atoks
        if overlap:
            analysis["verification_points"].append(
                f"Parallel keywords overlap CE text: {', '.join(sorted(overlap)[:6])}"
            )
            analysis["matching_hints"]["parallel_alignment"] = "partial_overlap"
        else:
            analysis["matching_hints"]["parallel_alignment"] = "no_obvious_overlap"

    if scp is not None and med is not None:
        try:
            scpf = float(scp)
            if scpf > 0:
                ratio = med / scpf
                analysis["pricing_context"]["ce_median_over_scp_ungraded"] = round(ratio, 3)
                if 0.5 <= ratio <= 2.0:
                    analysis["additional_indicators"].append(
                        f"CE median within ~0.5–2× SCP ungraded (${scpf:.2f}); rough consistency"
                    )
                elif ratio < 0.5:
                    analysis["additional_indicators"].append(
                        f"CE median much below SCP ungraded (${scpf:.2f}) — "
                        "CE thin comps, different condition/parallel, or listing premium"
                    )
                    analysis["suggested_qa_flags"].append("ce_vs_scp_low")
                else:
                    analysis["additional_indicators"].append(
                        f"CE median much above SCP ungraded (${scpf:.2f}) — "
                        "verify parallel/autograph/graded narrative"
                    )
                    analysis["suggested_qa_flags"].append("ce_vs_scp_high")
        except (TypeError, ValueError):
            pass

    # Confidence synthesis for humans / QA
    low_data = bool(
        comps.get("no_recent_comparable_sales")
        or (edge.get("strength") or "").lower() == "weak"
        or (rec.get("confidence_pct") or 100) < 35
    )
    if low_data:
        analysis["additional_indicators"].append(
            "Composite: CE shows weak data / low confidence — downgrade reliance on CE $ for go/no-go"
        )
        analysis["suggested_qa_flags"].append("ce_low_confidence_bundle")

    return analysis
