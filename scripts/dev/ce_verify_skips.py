#!/usr/bin/env python3
"""
CE verification of pipeline economics rejects.

Samples listings from pipeline_listing_skips where buy > Nx SCP (likely wrong match),
fetches their eBay listing image via Browse API, runs Collectors Edge photo identification,
and reports whether CE identifies a different (more valuable) card than our pipeline matched.

Usage:
  # Dry run -- show what would be sampled, no CE or API calls
  python3 scripts/ce_verify_skips.py --dry-run --limit 10

  # Run CE on 5 highest-priority skips (headless)
  python3 scripts/ce_verify_skips.py --limit 5 --headless

  # Run CE on 10, 2 parallel browsers
  python3 scripts/ce_verify_skips.py --limit 10 --headless --max-parallel 2

  # Only skips where buy > 3x SCP and buy >= $50
  python3 scripts/ce_verify_skips.py --min-ratio 3.0 --min-buy 50 --limit 10 --headless
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv
load_dotenv(_REPO_ROOT / "backend" / ".env")

from sqlalchemy import create_engine, text


def _get_engine():
    return create_engine(os.environ["DATABASE_URL"])


def sample_skips(engine, *, min_ratio: float, min_buy: float, limit: int) -> list[dict]:
    """Pull highest-priority economics rejects."""
    with engine.connect() as conn:
        # Sample diverse cards: one per pipeline_card_label, randomized
        rows = conn.execute(text("""
            SELECT DISTINCT ON (pipeline_card_label)
                   id, ebay_item_id, ebay_title, buy_price, scp_price,
                   pipeline_card_label, search_query,
                   ROUND((buy_price / scp_price)::numeric, 2) as ratio
            FROM pipeline_listing_skips
            WHERE skip_reason = 'economics_below_threshold'
              AND scp_price > 0
              AND buy_price >= :min_buy
              AND buy_price / scp_price >= :min_ratio
            ORDER BY pipeline_card_label, random()
            LIMIT :limit
        """), {"min_ratio": min_ratio, "min_buy": min_buy, "limit": limit}).fetchall()

    return [
        {
            "skip_id": r[0],
            "ebay_item_id": r[1],
            "ebay_title": r[2],
            "buy_price": float(r[3]) if r[3] else None,
            "scp_price": float(r[4]) if r[4] else None,
            "pipeline_card_label": r[5],
            "search_query": r[6],
            "ratio": float(r[7]) if r[7] else None,
        }
        for r in rows
    ]


def fetch_ebay_image_url(ebay_item_id: str) -> str | None:
    """Get listing image URL. Tries scraping the listing page OG tag first (free),
    falls back to Browse API if needed."""
    import requests
    import re

    # Method 1: Scrape og:image from listing page (works even on ended listings)
    try:
        resp = requests.get(
            f"https://www.ebay.com/itm/{ebay_item_id}",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=15,
            allow_redirects=True,
        )
        if resp.status_code == 200:
            # og:image meta tag
            m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', resp.text)
            if m:
                url = m.group(1)
                if "ebayimg.com" in url:
                    return url
            # Fallback: any ebayimg URL in the page
            m = re.search(r'(https://i\.ebayimg\.com/images/g/[^"\s]+)', resp.text)
            if m:
                return m.group(1)
    except Exception:
        pass

    # Method 2: Browse API (costs 1 API call)
    try:
        from backend.utils.token_manager import token_manager
        token = token_manager.get_token()
        resp = requests.get(
            f"https://api.ebay.com/buy/browse/v1/item/v1|{ebay_item_id}|0",
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
            },
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            img = data.get("image", {}).get("imageUrl")
            if img:
                return img
    except Exception as e:
        print(f"  Browse API fallback error for {ebay_item_id}: {e}", file=sys.stderr)
    return None


def run_ce_on_skip(
    skip: dict,
    image_url: str,
    *,
    headless: bool,
    out_dir: Path,
    settle_ms: int,
) -> dict:
    """Run CE photo_run on a single skip row. Returns result dict."""
    from scripts.dev.collectors_edge_photo_run import run_flow

    # Download image to temp file
    import requests
    suffix = ".jpg"
    if ".png" in image_url.lower():
        suffix = ".png"
    tf = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tf.close()
    tmp_path = Path(tf.name)

    try:
        r = requests.get(image_url, timeout=60, headers={"User-Agent": "TradingCards-CE/1.0"})
        r.raise_for_status()
        tmp_path.write_bytes(r.content)

        db_meta = {
            "skip_id": skip["skip_id"],
            "ebay_item_id": skip["ebay_item_id"],
            "ebay_title": skip["ebay_title"],
            "buy_price": skip["buy_price"],
            "scp_price": skip["scp_price"],
            "pipeline_card_label": skip["pipeline_card_label"],
            "player_name": (skip.get("pipeline_card_label") or "").split(" ")[0] if skip.get("pipeline_card_label") else None,
        }

        rc = run_flow(
            tmp_path,
            headless=headless,
            timeout_ms=180_000,
            slow_mo_ms=0,
            keep_open_s=0,
            out_dir=out_dir,
            viewport=(1280, 800),
            settle_ms=settle_ms,
            source_image_url=image_url,
            db_meta=db_meta,
        )
        return {"skip_id": skip["skip_id"], "exit_code": rc, "image_url": image_url}
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="CE verification of pipeline economics rejects.")
    ap.add_argument("--limit", type=int, default=5, help="Number of skips to sample (default 5).")
    ap.add_argument("--min-ratio", type=float, default=2.0, help="Min buy/SCP ratio (default 2.0).")
    ap.add_argument("--min-buy", type=float, default=20.0, help="Min buy price (default $20).")
    ap.add_argument("--dry-run", action="store_true", help="Show samples only, no CE or API calls.")
    ap.add_argument("--headless", action="store_true", help="Run CE browser headless.")
    ap.add_argument("--settle-ms", type=int, default=6000, help="CE settle time after result page.")
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=_REPO_ROOT / "scripts" / "dev" / "_collectors_edge_artifacts",
    )
    ap.add_argument("--max-parallel", type=int, default=1, help="Parallel CE browsers (default 1).")
    args = ap.parse_args(argv)

    engine = _get_engine()
    skips = sample_skips(engine, min_ratio=args.min_ratio, min_buy=args.min_buy, limit=args.limit)

    if not skips:
        print("No matching skips found.")
        return 0

    print(f"\nSampled {len(skips)} economics rejects (buy >= ${args.min_buy}, buy/SCP >= {args.min_ratio}x):")
    print("-" * 80)
    for s in skips:
        print(f"  skip_id={s['skip_id']} | ${s['buy_price']:>7} buy | ${s['scp_price']:>7} SCP | {s['ratio']}x")
        print(f"    eBay: {(s['ebay_title'] or '?')[:70]}")
        print(f"    Match: {(s['pipeline_card_label'] or '?')[:70]}")

    if args.dry_run:
        print(f"\n[DRY RUN] Would fetch images for {len(skips)} items via Browse API, then run CE.")
        return 0

    # Fetch images via Browse API
    print(f"\nFetching eBay images via Browse API ({len(skips)} calls)...")
    image_map: dict[int, str] = {}
    for s in skips:
        item_id = s["ebay_item_id"]
        if not item_id:
            print(f"  skip_id={s['skip_id']}: no ebay_item_id, skipping")
            continue
        url = fetch_ebay_image_url(item_id)
        if url:
            image_map[s["skip_id"]] = url
            print(f"  skip_id={s['skip_id']}: got image")
        else:
            print(f"  skip_id={s['skip_id']}: no image (listing may have ended)")
        time.sleep(0.5)

    if not image_map:
        print("No images retrieved. Listings may have ended.")
        return 1

    print(f"\nGot images for {len(image_map)} of {len(skips)} skips. Running CE...")

    # Ensure playwright is available
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        print(
            "Playwright not installed. Run:\n"
            "  python -m pip install -r scripts/dev/extra-requirements-collectors-edge.txt\n"
            "  python -m playwright install chromium",
            file=sys.stderr,
        )
        return 2

    results = []
    for i, s in enumerate(skips):
        if s["skip_id"] not in image_map:
            continue
        print(f"\n[{i+1}/{len(image_map)}] Running CE on skip_id={s['skip_id']}...")
        print(f"  ${s['buy_price']} buy vs ${s['scp_price']} SCP ({s['ratio']}x)")
        print(f"  Pipeline matched: {(s['pipeline_card_label'] or '?')[:60]}")

        result = run_ce_on_skip(
            s,
            image_map[s["skip_id"]],
            headless=args.headless,
            out_dir=args.out_dir,
            settle_ms=args.settle_ms,
        )
        results.append(result)

        if i < len(image_map) - 1:
            time.sleep(3)

    # Summary
    print("\n" + "=" * 80)
    print("CE VERIFICATION RESULTS")
    print("=" * 80)
    succeeded = sum(1 for r in results if r["exit_code"] == 0)
    print(f"  Ran CE on {len(results)} skips, {succeeded} succeeded")
    print(f"  Check artifacts in: {args.out_dir}")
    print(f"  Look for CE median >> pipeline SCP = wrong match = hidden opportunity")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
