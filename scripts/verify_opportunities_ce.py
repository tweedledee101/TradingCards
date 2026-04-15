#!/usr/bin/env python3
"""Post-pipeline CE identity verification for opportunities.

Downloads the first full-size image for each unverified opportunity,
calls Collectors Edge API to identify the card, and updates
verification_status + verification_detail on the opportunity row.

Designed to run after BIN/auction pipeline in CI or manually.

Usage:
    python3 scripts/verify_opportunities_ce.py --limit 50
    python3 scripts/verify_opportunities_ce.py --listing-type buy_it_now --limit 100
    python3 scripts/verify_opportunities_ce.py --min-profit 20  # prioritize high-value
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import requests
from sqlalchemy import text
from backend.utils.database import SessionLocal
from backend.utils.collectors_edge_result import (
    call_ce_identify_api,
    ce_extracted_from_api_json,
    analyze_ce_for_pipeline,
)
from backend.models import Opportunity
from sqlalchemy import and_


def fetch_image(url: str, timeout: int = 15) -> bytes | None:
    try:
        r = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })
        if r.status_code == 200 and len(r.content) > 500:
            return r.content
    except Exception:
        pass
    return None


def _try_year_correction(opp, api_json: dict, ce: dict, db) -> dict | None:
    """When CE confirms player but disagrees on year, look up SCP price for CE year.
    Returns correction dict if profitable, else None."""
    import json as _json

    ce_year = api_json.get("year")
    if not ce_year:
        return None
    try:
        ce_year_int = int(ce_year)
    except (TypeError, ValueError):
        return None

    player = opp.player_name
    card_number = opp.card_number or ""

    # Use a separate session to avoid polluting the ORM session
    lookup_db = SessionLocal()
    try:
        rows = lookup_db.execute(
            text(
                "SELECT variants FROM scp_cache "
                "WHERE player_name ILIKE :player AND card_year = :yr "
                "AND card_number ILIKE :cn LIMIT 5"
            ),
            {"player": player, "yr": ce_year_int, "cn": card_number},
        ).fetchall()
    finally:
        lookup_db.close()

    if not rows:
        return None

    best_price = None
    for row in rows:
        variants = row[0]
        if isinstance(variants, str):
            variants = _json.loads(variants)
        if not isinstance(variants, list):
            continue
        for v in variants:
            price = v.get("ungraded") or 0
            if price and float(price) >= 5:
                if best_price is None or float(price) > best_price:
                    best_price = float(price)

    if best_price is None:
        return None

    buy = float(opp.buy_price)
    profit = best_price - buy - (buy * 0.13)
    if profit < 10:
        return None

    return {
        "year_corrected": True,
        "original_year": opp.card_year,
        "corrected_year": ce_year_int,
        "original_scp_price": float(opp.scp_price),
        "corrected_scp_price": best_price,
        "corrected_profit": round(profit, 2),
    }


def best_image_url(opp: Opportunity) -> str | None:
    urls = opp.listing_image_urls or []
    for u in urls:
        if "s-l1600" in u:
            return u
    for u in urls:
        if "s-l" in u and "s-l225" not in u:
            return u
    return urls[0] if urls else (opp.image_url or None)


def verify_one(opp: Opportunity, db, *, dry_run: bool = False) -> dict:
    result = {"id": opp.id, "player": opp.player_name, "status": "skipped"}

    img_url = best_image_url(opp)
    if not img_url:
        result["status"] = "no_image"
        return result

    img_bytes = fetch_image(img_url)
    if not img_bytes:
        result["status"] = "image_fetch_failed"
        return result

    api_json = call_ce_identify_api(img_bytes, timeout=120)
    if not api_json:
        result["status"] = "ce_api_failed"
        return result

    ce = ce_extracted_from_api_json(api_json)
    pipeline_row = {
        "player_name": opp.player_name,
        "card_year": opp.card_year,
        "card_set": opp.card_set,
        "card_number": opp.card_number,
        "parallel": opp.parallel,
        "ebay_title": opp.ebay_title,
        "scp_price": float(opp.scp_price) if opp.scp_price else None,
    }
    analysis = analyze_ce_for_pipeline(ce, pipeline=pipeline_row)

    # Determine verification outcome
    hints = analysis.get("matching_hints", {})
    flags = analysis.get("suggested_qa_flags", [])

    player_ok = hints.get("player_alignment") in ("likely_match", None)
    year_ok = hints.get("year_alignment") in ("match", "fuzzy_match", None)

    if player_ok and year_ok and not any(f.startswith("ce_player") or f.startswith("ce_year") for f in flags):
        status = "ce_confirmed"
    elif not player_ok:
        status = "ce_player_mismatch"
    elif not year_ok:
        status = "ce_year_mismatch"
    else:
        status = "ce_review"

    ce_pricing = ce.get("pricing", {})
    detail = {
        "schema": 2,
        "ce_status": status,
        "ce_identity": ce.get("identity", {}),
        "ce_pricing": ce_pricing,
        "ce_flags": flags,
        "ce_player_alignment": hints.get("player_alignment"),
        "ce_year_alignment": hints.get("year_alignment"),
        "ce_parallel_alignment": hints.get("parallel_alignment"),
        "ce_card_name": api_json.get("cardName"),
        "ce_year": api_json.get("year"),
        "ce_variant": api_json.get("variant"),
        "ce_print_run": api_json.get("printRun"),
    }

    # Year correction: player is right but year is wrong -- try SCP lookup for CE year
    if status == "ce_year_mismatch" and player_ok and db is not None:
        corrected = _try_year_correction(opp, api_json, ce, db)
        if corrected:
            status = "ce_confirmed"
            detail["ce_status"] = status
            detail.update(corrected)

    # Price triangle: do any two of three (eBay buy, CE median, pipeline SCP) agree?
    # This determines whether the pipeline's card identity match is correct.
    ce_med = ce_pricing.get("median_usd")
    scp = float(opp.scp_price) if opp.scp_price else None
    buy = float(opp.buy_price) if opp.buy_price else None

    if ce_med and scp and buy and scp > 0 and ce_med > 0:
        ebay_ce_gap = abs(buy - ce_med)
        ce_scp_gap = abs(ce_med - scp)
        ebay_scp_gap = abs(buy - scp)

        # "close" = within 30% of the larger value or within $5
        def _close(a, b):
            mx = max(a, b, 1)
            return abs(a - b) < 5.0 or abs(a - b) / mx < 0.30

        ebay_ce_close = _close(buy, ce_med)
        ce_scp_close = _close(ce_med, scp)
        ebay_scp_close = _close(buy, scp)

        detail["ebay_ce_gap"] = round(ebay_ce_gap, 2)
        detail["ce_scp_gap"] = round(ce_scp_gap, 2)
        detail["ebay_scp_gap"] = round(ebay_scp_gap, 2)
        detail["ce_scp_price_ratio"] = round(ce_med / scp, 3)

        if ebay_ce_close and not ce_scp_close and scp > ce_med * 2:
            # eBay and CE agree, SCP is way higher -> pipeline matched wrong SCP entry
            detail["price_triangle"] = "ebay_ce_agree_scp_wrong"
            if status == "ce_confirmed":
                status = "ce_price_divergence"
                detail["ce_status"] = status
        elif ce_scp_close and buy < ce_med * 0.5:
            # CE and SCP agree on value, eBay is much cheaper -> possible real opportunity
            detail["price_triangle"] = "ce_scp_agree_ebay_cheap"
            # This is potentially a real deal -- don't reject
            if status in ("ce_year_mismatch", "ce_review") and player_ok:
                status = "ce_confirmed"
                detail["ce_status"] = status
                detail["price_note"] = "CE and SCP agree on value; eBay price is well below -- possible real opportunity"
        elif ebay_scp_close and not ce_scp_close:
            # eBay and SCP agree, CE is the outlier -> CE might be wrong
            detail["price_triangle"] = "ebay_scp_agree_ce_outlier"
        elif ebay_ce_close and ce_scp_close:
            # All three roughly agree -> strong signal
            detail["price_triangle"] = "all_agree"
        else:
            detail["price_triangle"] = "no_clear_agreement"
    elif ce_med and scp and scp > 0:
        detail["ce_scp_price_ratio"] = round(ce_med / scp, 3)

    result["status"] = status
    result["ce_card_name"] = api_json.get("cardName")
    result["ce_median"] = ce_med

    if not dry_run:
        existing = opp.verification_detail or {}
        if isinstance(existing, str):
            import json
            try:
                existing = json.loads(existing)
            except Exception:
                existing = {}
        merged = {**existing, **detail}
        opp.verification_status = status
        opp.verification_detail = merged  # reassign so SQLAlchemy detects JSONB change
        db.commit()

    return result


def main():
    parser = argparse.ArgumentParser(description="CE identity verification for opportunities")
    parser.add_argument("--limit", type=int, default=50, help="Max opportunities to verify")
    parser.add_argument("--listing-type", type=str, help="Filter: buy_it_now or auction")
    parser.add_argument("--min-profit", type=float, default=0, help="Only verify opps above this profit")
    parser.add_argument("--dry-run", action="store_true", help="Don't update DB")
    parser.add_argument("--cooldown", type=float, default=5, help="Seconds between CE API calls")
    args = parser.parse_args()

    db = SessionLocal()

    filters = [
        Opportunity.verification_status.in_(["pending", None]),
        Opportunity.listing_image_urls.isnot(None),
    ]
    if args.listing_type:
        filters.append(Opportunity.listing_type == args.listing_type)
    if args.min_profit > 0:
        filters.append(Opportunity.profit >= args.min_profit)

    opps = (
        db.query(Opportunity)
        .filter(and_(*filters))
        .order_by(Opportunity.profit.desc())
        .limit(args.limit)
        .all()
    )

    print(f"CE Verification: {len(opps)} opportunities to check")
    if args.dry_run:
        print("(dry run -- no DB updates)")
    print("=" * 60)

    stats = {"confirmed": 0, "mismatch": 0, "review": 0, "failed": 0}

    for i, opp in enumerate(opps, 1):
        label = f"{opp.player_name} {opp.card_year} #{opp.card_number} [{opp.parallel}]"
        print(f"\n[{i}/{len(opps)}] {label}")
        print(f"  SCP: ${opp.scp_price:.2f} | Buy: ${opp.buy_price:.2f} | Profit: ${opp.profit:.2f}")

        result = verify_one(opp, db, dry_run=args.dry_run)
        status = result["status"]

        if status == "ce_confirmed":
            stats["confirmed"] += 1
            print(f"  CE: CONFIRMED -- {result.get('ce_card_name', 'n/a')}")
        elif status in ("ce_player_mismatch", "ce_year_mismatch", "ce_price_divergence"):
            stats["mismatch"] += 1
            print(f"  CE: MISMATCH ({status}) -- {result.get('ce_card_name', 'n/a')}")
            if result.get("ce_median"):
                print(f"  CE median: ${result['ce_median']:.2f} vs SCP: ${opp.scp_price:.2f}")
        elif status == "ce_review":
            stats["review"] += 1
            print(f"  CE: REVIEW -- {result.get('ce_card_name', 'n/a')}")
        else:
            stats["failed"] += 1
            print(f"  CE: {status}")

        if i < len(opps):
            time.sleep(args.cooldown)

    db.close()

    print("\n" + "=" * 60)
    print(f"RESULTS: {len(opps)} verified")
    print(f"  Confirmed: {stats['confirmed']}")
    print(f"  Mismatch:  {stats['mismatch']}")
    print(f"  Review:    {stats['review']}")
    print(f"  Failed:    {stats['failed']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
