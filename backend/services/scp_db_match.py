"""Database-only SCP market rate lookup (no Selenium). Shared by auction pipeline and vision retry."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func

from backend.models import Card, MarketRate


def _normalize_card_number(card_number: str) -> str:
    s = (card_number or "").strip()
    if s.startswith("#"):
        s = s[1:].strip()
    return s


def _scp_dict_from_card_rate(card: Card, rate: MarketRate) -> Optional[Dict[str, Any]]:
    if not rate.ungraded_price:
        return None
    card_parallel = (card.parallel or "Base").lower()
    url = rate.scp_product_url or ""
    if url and card_parallel != "base":
        url_lower = url.lower()
        parallel_slug = card_parallel.replace(" ", "-")
        if parallel_slug not in url_lower:
            return None
    return {
        "scp_price": float(rate.ungraded_price) if rate.ungraded_price else None,
        "grade_9": float(rate.grade_9_price) if rate.grade_9_price else None,
        "psa_10": float(rate.psa_10_price) if rate.psa_10_price else None,
        "scp_url": rate.scp_product_url,
        "card_set": card.card_set,
        "source": "database",
        "match_type": "exact",
        "matched_parallel": card.parallel or "Base",
    }


def find_scp_match_in_db(
    db,
    player_name: str,
    card_year: Optional[int],
    card_number: str,
    parallel: str,
    card_set: str,
) -> Optional[Dict[str, Any]]:
    """Look up SCP market rate from database. Returns dict with prices or None."""
    _ = card_set  # reserved for future set-scoped matching
    cn = _normalize_card_number(card_number)
    if not player_name or not cn:
        return None

    query = (
        db.query(Card, MarketRate)
        .join(MarketRate, Card.id == MarketRate.card_id)
        .filter(func.lower(Card.player_name) == player_name.lower())
    )

    if card_year is not None and card_year > 0:
        query = query.filter(Card.card_year == card_year)

    query = query.filter(func.lower(Card.card_number) == cn.lower())

    results = query.order_by(MarketRate.date_recorded.desc()).all()

    if not results:
        return None

    parallel_lower = (parallel or "base").lower()
    for card, rate in results:
        card_parallel = (card.parallel or "Base").lower()
        if card_parallel == parallel_lower:
            return _scp_dict_from_card_rate(card, rate)

    return None


def _collect_priced_variants(
    db,
    player_name: str,
    card_year: Optional[int],
    cn: str,
) -> List[Tuple[Card, MarketRate, Dict[str, Any]]]:
    q = (
        db.query(Card, MarketRate)
        .join(MarketRate, Card.id == MarketRate.card_id)
        .filter(func.lower(Card.player_name) == player_name.lower())
        .filter(func.lower(Card.card_number) == cn.lower())
    )
    if card_year is not None and card_year > 0:
        q = q.filter(Card.card_year == card_year)
    rows = q.order_by(MarketRate.date_recorded.desc()).all()
    by_card_id: dict[int, Tuple[Card, MarketRate, Dict[str, Any]]] = {}
    for card, rate in rows:
        if card.id in by_card_id:
            continue
        d = _scp_dict_from_card_rate(card, rate)
        if d:
            by_card_id[card.id] = (card, rate, d)
    return list(by_card_id.values())


def find_scp_match_for_vision(
    db,
    player_name: str,
    card_year: Optional[int],
    card_number: str,
    parallel: str,
    card_set: str,
) -> Optional[Dict[str, Any]]:
    """
    Like ``find_scp_match_in_db`` but tolerates common vision/catalog mismatches:

    - Normalizes ``#US175`` → ``US175``
    - If vision says ``Base`` but the catalog uses ``RC`` / rookie-style parallels, tries those
    - If multiple priced variants exist, picks one with a small heuristic (keyword overlap, then
      lowest ungraded as a conservative comp)
    """
    _ = card_set
    cn = _normalize_card_number(card_number)
    if not player_name or not cn:
        return None

    hit = find_scp_match_in_db(db, player_name, card_year, cn, parallel, card_set)
    if hit:
        out = dict(hit)
        out["db_match_mode"] = "exact_parallel"
        return out

    vision_par = (parallel or "base").strip().lower()
    if vision_par == "base":
        for alt in ("RC", "Sp", "SP", "Rookie", "Rookie Card"):
            hit = find_scp_match_in_db(db, player_name, card_year, cn, alt, card_set)
            if hit:
                out = dict(hit)
                out["db_match_mode"] = "catalog_rookie_parallel"
                out["db_match_note"] = (
                    f"vision said Base; catalog match uses parallel {out['matched_parallel']!r}"
                )
                return out

    variants = _collect_priced_variants(db, player_name, card_year, cn)
    year_relaxed = False
    if not variants and card_year is not None and card_year > 0:
        variants = _collect_priced_variants(db, player_name, None, cn)
        year_relaxed = True
    if not variants:
        return None

    if len(variants) == 1:
        card, _r, d = variants[0]
        out = dict(d)
        if year_relaxed:
            out["db_match_mode"] = "single_priced_variant_year_relaxed"
            out["db_match_note"] = (
                f"No priced row for year {card_year}; using catalog year {card.card_year} "
                f"for the same # (confirm listing vs slab before trading)."
            )
        else:
            out["db_match_mode"] = "single_priced_variant"
        return out

    vis_blob = f"{parallel} {card_set}".lower()
    scored: List[Tuple[int, float, Dict[str, Any], str]] = []
    for card, _rate, d in variants:
        cpar = (card.parallel or "base").lower()
        score = 0
        if cpar in vis_blob:
            score += 3
        for tok in cpar.replace("/", " ").split():
            if len(tok) > 2 and tok in vis_blob:
                score += 1
        scored.append((score, float(d["scp_price"]), d, cpar))

    scored.sort(key=lambda x: (-x[0], x[1]))
    _sc, _pr, best, cpar = scored[0]
    out = dict(best)
    out["db_match_mode"] = "multi_variant_heuristic_year_relaxed" if year_relaxed else "multi_variant_heuristic"
    ys = sorted({v[0].card_year for v in variants if v[0].card_year is not None})
    prefix = (
        f"Dropped year filter (requested {card_year}); this # exists in catalog years {ys[:10]}. "
        if year_relaxed
        else ""
    )
    out["db_match_note"] = (
        prefix
        + f"{len(variants)} priced variants in DB; picked [{out['matched_parallel']!r}] "
        f"(title/parallel overlap + conservative price tie-break)"
    )
    out["db_match_other_parallels"] = sorted(
        {v[0].parallel or "Base" for v in variants}
    )[:12]
    return out


def catalog_card_number_hints_for_player(
    db,
    player_name: str,
    card_number_hint: str,
    *,
    limit: int = 55,
    max_rows_to_scan_all_numbers: int = 600,
) -> Tuple[List[str], str]:
    """
    Distinct ``cards.card_number`` values for a player: prefer #s matching tokens from
    ``card_number_hint`` (e.g. FA from FA-NS), then fill alphabetically if the player is small
    enough in ``cards``.
    """
    pn = (player_name or "").strip()
    if not pn:
        return [], ""
    base = (
        db.query(Card.card_number)
        .filter(func.lower(Card.player_name) == pn.lower())
        .filter(Card.card_number.isnot(None))
        .filter(Card.card_number != "")
    )
    hint = _normalize_card_number(card_number_hint)
    toks = sorted(
        {t for t in re.split(r"[^A-Za-z0-9]+", hint) if len(t) >= 2},
        key=len,
        reverse=True,
    )[:6]

    n_rows = (
        db.query(Card).filter(func.lower(Card.player_name) == pn.lower()).count()
    )

    picked: List[str] = []
    seen: set[str] = set()
    note = ""

    for tok in toks:
        for (cn,) in base.filter(Card.card_number.ilike(f"%{tok}%")).distinct().limit(40):
            s = (cn or "").strip()
            if s and s not in seen:
                seen.add(s)
                picked.append(s)
        if len(picked) >= limit:
            return picked[:limit], f"(#s matching tokens from {hint!r})"

    if n_rows <= max_rows_to_scan_all_numbers:
        all_n: set[str] = set()
        for (cn,) in base.distinct().all():
            s = (cn or "").strip()
            if s:
                all_n.add(s)
        rest = sorted(all_n - seen, key=str.lower)
        for s in rest:
            picked.append(s)
            if len(picked) >= limit:
                break
        note = f"({len(all_n)} distinct #s in DB for this player; showing {min(len(picked), limit)})"
    else:
        note = (
            f"({n_rows} `cards` rows for player — not listing every #; "
            f"used token search on {hint!r} only)"
        )

    return picked[:limit], note


def vision_scp_miss_hint(
    db,
    player_name: str,
    card_year: Optional[int],
    card_number: str,
    *,
    hint_context: str = "vision_retry",
) -> str:
    """One-line explanation when ``find_scp_match_for_vision`` returns no row."""
    cn = _normalize_card_number(card_number)
    if not player_name or not cn:
        return "incomplete identity"

    q = (
        db.query(Card)
        .filter(func.lower(Card.player_name) == player_name.lower())
        .filter(func.lower(Card.card_number) == cn.lower())
    )
    n_any = q.count()

    if n_any == 0:
        if hint_context == "ce_lookup":
            n_player = (
                db.query(Card)
                .filter(func.lower(Card.player_name) == player_name.lower())
                .count()
            )
            # n_any is already "this player + this # across all years" — do not blame a single year.
            msg = (
                f"No PostgreSQL `cards` row for {player_name!r} #{cn!r} (any year). "
                "That exact # is not in your local catalog — ingest never pulled it, or SCP labels "
                "the card differently than the listing."
            )
            if n_player:
                msg += f" You do have {n_player} `cards` row(s) for this player under other #s — see follow-up sample."
            else:
                msg += " No `cards` rows at all for this player name — check spelling vs catalog."
            return msg
        return (
            f"Nova read player+# {player_name!r} #{cn!r} — no matching `cards` row "
            "(Collectors Edge not used in vision_retry; ingest gap or wrong #)"
        )

    if card_year is not None and card_year > 0:
        n_year = q.filter(Card.card_year == card_year).count()
        if n_year == 0:
            ys_rows = (
                db.query(Card.card_year)
                .filter(func.lower(Card.player_name) == player_name.lower())
                .filter(func.lower(Card.card_number) == cn.lower())
                .distinct()
                .limit(12)
                .all()
            )
            ys = sorted({r[0] for r in ys_rows if r[0] is not None})
            ys_txt = f" same # exists in catalog years {ys}" if ys else ""
            if hint_context == "ce_lookup":
                return (
                    f"{player_name!r} #{cn!r}: no `cards` row for year {card_year}; "
                    f"{n_any} row(s) for this # in other years{ys_txt}. "
                    f"Adjust `--year` / `--prefer-db-year` or confirm listing year vs slab."
                )
            return (
                f"Nova year {card_year} + #{cn}: no `cards` row for that year; "
                f"{n_any} row(s) for this # in other years{ys_txt}. "
                f"If the listing year is wrong, use CE photo → `scripts/scp_lookup_from_ce_json.py`."
            )

    with_rate = (
        db.query(Card)
        .join(MarketRate, Card.id == MarketRate.card_id)
        .filter(func.lower(Card.player_name) == player_name.lower())
        .filter(func.lower(Card.card_number) == cn.lower())
    )
    if card_year is not None and card_year > 0:
        with_rate = with_rate.filter(Card.card_year == card_year)
    n_rate = with_rate.count()

    if n_rate == 0:
        who = "this identity" if hint_context == "ce_lookup" else "Nova identity"
        return f"{n_any} `cards` row(s) for {who} but no priced `market_rates` for this #/year"

    pars = (
        db.query(Card.parallel)
        .join(MarketRate, Card.id == MarketRate.card_id)
        .filter(func.lower(Card.player_name) == player_name.lower())
        .filter(func.lower(Card.card_number) == cn.lower())
    )
    if card_year is not None and card_year > 0:
        pars = pars.filter(Card.card_year == card_year)
    plist = sorted({(row[0] or "Base") for row in pars.distinct().limit(40).all()})
    return (
        f"{n_rate} priced row(s); parallels {plist[:10]!s}"
        f"{' …' if len(plist) > 10 else ''} — matcher still missed (URL slug vs parallel text?)"
    )
