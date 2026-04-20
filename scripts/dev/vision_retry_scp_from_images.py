#!/usr/bin/env python3
"""
Vision → SCP DB retry using eBay **CDN images only** (no listing page / Cloudflare).

**Policy:** Vision is **post-pipeline only** during BIN/auction ingest. Pipelines emit a **bounded sample**
in ``job_runs.results_summary``. This script may **append** new ``opportunities`` rows after a HIT
(``--no-persist`` to disable); those rows are **flagged** for review.

- ``vision_post_pipeline_queue_sample`` (preferred): BIN price-floor rejects, BIN “suspicious vs SCP”
  rows that were still stored, **auction Step 2 metadata skips** (``step2_no_year`` / ``step2_no_card_number`` /
  ``step2_no_player``) with gallery URLs, auction no-pricing-after-fallbacks, auction BIN≪SCP sanity rejects.
- ``no_scp_vision_queue_sample`` (legacy auction-only): still read if the unified key is absent.

Pathway:
  1. Load a queue from **latest job**, **``--json``**, or **``--from-recent-opportunities N``** (reads ``opportunities`` with images — works immediately, no new pipeline run).
  2. ``requests.get`` each image URL (eBay i.ebayimg.com, etc.).
  3. Amazon Nova **multimodal** reads pixels → JSON identity.
  4. ``find_scp_match_for_vision`` — DB SCP lookup with Base/RC and multi-parallel fallbacks (stricter ``find_scp_match_in_db`` is for ingest).
  5. **Optional (default on):** insert **new** ``opportunities`` rows on **HIT** when profit/ROI/confidence
     pass filters (``--no-persist`` to only print). Rows are **flagged** + ``qa_flags`` for review.

Requires:
  - ``NOVA_API_KEY`` in ``backend/.env`` (or env)
  - ``pip install openai`` (see ``backend/requirements.txt``)
  - Database URL (same as API / pipelines)

Collectors Edge is **not** invoked here. For photo-truth vs listing/Nova, see ``scripts/scp_lookup_from_ce_json.py`` + ``PIPELINE-OPS.md`` (CE → SCP).

Usage:
  cd /path/to/TradingCards
  python3 scripts/vision_retry_scp_from_images.py --latest-auction-job --limit 5
  python3 scripts/vision_retry_scp_from_images.py --latest-bin-job --limit 5
  python3 scripts/vision_retry_scp_from_images.py --from-recent-opportunities 5 --dry-run
  python3 scripts/vision_retry_scp_from_images.py --json /tmp/queue.json --dry-run
  python3 scripts/vision_retry_scp_from_images.py --latest-bin-job --limit 10 --no-persist   # HIT/MISS only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

# Repo root on sys.path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / "backend" / ".env")

from backend.models import JobRun, Opportunity
from backend.services.scp_db_match import find_scp_match_for_vision, vision_scp_miss_hint
from backend.services.vision_card_extract import download_listing_images, extract_card_identity_nova
from backend.utils.database import SessionLocal

FEE_RATE = 0.13
_CONF_RANK = {"high": 3, "medium": 2, "low": 1, "unclear": 0}


def _confidence_meets_min(conf: str, min_conf: str) -> bool:
    c = (conf or "unclear").strip().lower()
    m = (min_conf or "medium").strip().lower()
    return _CONF_RANK.get(c, 0) >= _CONF_RANK.get(m, 0)


def _norm_ebay_item_id(raw) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if "|" in s:
        s = s.split("|")[-1].strip()
    return s or None


def _listing_type_for_queue_item(job_source: str, item: dict) -> str:
    lt = (item.get("listing_type") or "").strip()
    if lt in ("auction", "buy_it_now"):
        return lt
    if job_source == "auction_finder":
        return "auction"
    return "buy_it_now"


def _buy_price_and_shipping(item: dict) -> tuple[float | None, float]:
    try:
        shipping = float(item.get("shipping")) if item.get("shipping") is not None else 0.0
    except (TypeError, ValueError):
        shipping = 0.0
    for key in ("buy_price", "buy_price_or_bin", "price"):
        v = item.get(key)
        if v is None:
            continue
        try:
            return float(v), shipping
        except (TypeError, ValueError):
            continue
    return None, shipping


def _profit_and_roi(listing_type: str, buy: float, shipping: float, scp: float) -> tuple[float, float]:
    if listing_type == "auction":
        net = scp * (1.0 - FEE_RATE)
        profit = net - buy - shipping
    else:
        profit = scp - buy - (buy * FEE_RATE)
    roi = (profit / buy * 100.0) if buy > 0 else 0.0
    return profit, roi


def _try_insert_vision_opportunity(
    db,
    *,
    item: dict,
    ident: dict,
    scp: dict,
    job_source: str,
    min_profit: float,
    min_roi: float,
    min_confidence: str,
) -> tuple[str, str]:
    if not _confidence_meets_min(ident.get("confidence") or "", min_confidence):
        return "skip_confidence", f"confidence={ident.get('confidence')!r} < min {min_confidence!r}"

    iid = _norm_ebay_item_id(item.get("ebay_item_id"))
    if not iid:
        return "skip_no_item_id", "missing ebay_item_id"

    buy, shipping = _buy_price_and_shipping(item)
    if buy is None:
        return "skip_no_buy_price", "no buy_price on queue row"

    scp_price = float(scp["scp_price"])
    lt = _listing_type_for_queue_item(job_source, item)
    profit, roi = _profit_and_roi(lt, buy, shipping, scp_price)
    if profit < min_profit:
        return "skip_low_profit", f"profit ${profit:.2f} < min ${min_profit:.2f}"
    if min_roi > 0 and roi < min_roi:
        return "skip_low_roi", f"roi {roi:.1f}% < min {min_roi:.1f}%"

    exists = db.query(Opportunity).filter(Opportunity.ebay_item_id == iid).first()
    if exists:
        return "skip_duplicate", f"already opportunity id={exists.id}"

    player = (ident.get("player_name") or "").strip()
    cn = (ident.get("card_number") or "").strip()
    year = ident.get("card_year")
    parallel = scp.get("matched_parallel") or ident.get("parallel") or "Base"
    card_set = scp.get("card_set") or (ident.get("card_set") or "") or ""

    title = (item.get("title") or "")[:500]
    urls = [u for u in (item.get("image_urls") or []) if isinstance(u, str) and u.startswith("http")][:15]
    url = f"https://www.ebay.com/itm/{iid}"

    reason = (item.get("reason") or "")[:120]
    qa = [
        {
            "rule": "vision_retry_persist",
            "severity": "warning",
            "detail": f"vision HIT auto-insert; queue_reason={reason!r}; verify photo vs catalog",
        }
    ]

    cy = None
    if year is not None:
        try:
            cy = int(year)
        except (TypeError, ValueError):
            cy = None

    row = Opportunity(
        player_name=player[:255],
        card_year=cy,
        card_set=(card_set[:255] if card_set else None),
        card_number=cn[:50],
        parallel=(parallel or "Base")[:100],
        scp_title=None,
        scp_price=Decimal(str(round(scp_price, 2))),
        buy_price=Decimal(str(round(buy, 2))),
        shipping=Decimal(str(round(shipping, 2))),
        profit=Decimal(str(round(profit, 2))),
        roi=Decimal(str(round(roi, 2))),
        ebay_title=title,
        ebay_url=url,
        ebay_item_id=iid[:50],
        image_url=urls[0] if urls else None,
        listing_image_urls=urls if urls else None,
        scp_url=scp.get("scp_url"),
        scp_grade_9=(
            Decimal(str(round(float(scp["grade_9"]), 2))) if scp.get("grade_9") is not None else None
        ),
        scp_psa_10=(
            Decimal(str(round(float(scp["psa_10"]), 2))) if scp.get("psa_10") is not None else None
        ),
        listing_type=lt,
        bid_count=0,
        end_time=None,
        scp_volume=None,
        flagged=True,
        qa_status="pending",
        qa_flags=qa,
        verification_status="pending",
        verification_detail={"schema": 1, "pipeline": "vision_retry"},
        sport="Baseball",
        price_source="scp",
        scan_id=None,
    )
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
        return "inserted", f"opportunity id={row.id}"
    except Exception as e:
        db.rollback()
        return "skip_db_error", str(e)


def _parse_results_summary(raw) -> dict:
    """RDS/drivers may return JSON already decoded (dict); local Text column is a str."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
    return {}


def _vision_queue_from_summary(data: dict, *, job_name: str | None = None) -> list:
    """Read unified sample if present (even when []); else legacy auction-only list.

    BIN jobs never had ``no_scp_vision_queue_sample``; do not treat ``[]`` as "missing".
    """
    if not isinstance(data, dict):
        return []
    if "vision_post_pipeline_queue_sample" in data:
        v = data["vision_post_pipeline_queue_sample"]
        if v is None:
            return []
        return list(v) if isinstance(v, list) else []
    if job_name == "opportunity_finder":
        return []
    leg = data.get("no_scp_vision_queue_sample")
    if not isinstance(leg, list) or not leg:
        return []
    out: list = []
    for x in leg:
        if isinstance(x, dict):
            o = dict(x)
            o.setdefault("reason", "auction_no_pricing_after_fallbacks")
            out.append(o)
        else:
            out.append(x)
    return out


def _load_queue_from_latest_job(db, job_name: str = "auction_finder") -> tuple[list, str, dict]:
    """Return ``(queue, empty_reason, diagnosis)``. ``empty_reason`` is non-empty when queue is []."""
    diagnosis: dict = {}
    row = (
        db.query(JobRun)
        .filter(JobRun.job_name == job_name, JobRun.status == "completed")
        .order_by(JobRun.id.desc())
        .first()
    )
    if not row:
        return [], "no_completed_job", diagnosis
    diagnosis["job_run_id"] = row.id
    if not row.results_summary:
        return [], "no_results_summary", diagnosis
    data = _parse_results_summary(row.results_summary)
    if isinstance(data, dict):
        diagnosis["results_summary_keys"] = sorted(data.keys())
    if not data:
        return [], "unparseable_summary", diagnosis
    q = _vision_queue_from_summary(data, job_name=job_name)
    if q:
        return q, "", diagnosis
    if "vision_post_pipeline_queue_sample" in data:
        v = data["vision_post_pipeline_queue_sample"]
        if v is None or (isinstance(v, list) and len(v) == 0):
            return [], "unified_queue_empty", diagnosis
        return [], "unified_queue_bad_type", diagnosis
    if job_name == "auction_finder":
        if "vision_post_pipeline_queue_sample" not in data and (
            "auctions_searched" in data or "step2_skip_reasons" in data or "qualified" in data
        ):
            return [], "auction_predates_vision_summary", diagnosis
    if job_name == "opportunity_finder":
        return [], "missing_vision_key_rerun_bin_pipeline", diagnosis
    leg = data.get("no_scp_vision_queue_sample")
    diagnosis["has_legacy_no_scp_key"] = "no_scp_vision_queue_sample" in data
    diagnosis["legacy_type"] = type(leg).__name__ if leg is not None else None
    diagnosis["legacy_len"] = len(leg) if isinstance(leg, list) else None
    return [], "auction_no_legacy_queue", diagnosis


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Nova vision + DB SCP retry from CDN image URLs.")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--latest-auction-job",
        action="store_true",
        help="Latest completed auction_finder: vision_post_pipeline_queue_sample (or legacy no_scp_vision_queue_sample)",
    )
    src.add_argument(
        "--latest-bin-job",
        action="store_true",
        help="Latest completed opportunity_finder: vision_post_pipeline_queue_sample (price-floor + suspicious BIN)",
    )
    src.add_argument(
        "--from-recent-opportunities",
        type=int,
        metavar="N",
        help="Build queue from N newest opportunities rows that have CDN image URLs (no job_runs required).",
    )
    src.add_argument("--json", type=Path, help="JSON file: array of {ebay_item_id, title, image_urls, reason?}")
    p.add_argument(
        "--listing-type",
        default=None,
        metavar="TYPE",
        help="With --from-recent-opportunities: filter opportunities.listing_type (e.g. buy_it_now, auction).",
    )
    p.add_argument("--limit", type=int, default=8, help="Max listings to process")
    p.add_argument("--max-images", type=int, default=6, help="Max images downloaded per listing")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Only download images; print sizes (no Nova, no DB SCP, no inserts)",
    )
    p.add_argument(
        "--no-persist",
        action="store_true",
        help="On SCP HIT, print only — do not insert opportunities (default: insert when filters pass)",
    )
    p.add_argument(
        "--min-profit",
        type=float,
        default=10.0,
        help="Minimum profit $ required to insert on HIT (default: 10)",
    )
    p.add_argument(
        "--min-roi",
        type=float,
        default=0.0,
        help="Minimum ROI %% to insert on HIT (default: 0 = off)",
    )
    p.add_argument(
        "--min-confidence",
        default="medium",
        choices=["high", "medium", "low", "unclear"],
        help="Minimum Nova confidence to insert (default: medium)",
    )
    args = p.parse_args(argv)

    if args.from_recent_opportunities is not None and args.from_recent_opportunities < 1:
        print("--from-recent-opportunities N requires N >= 1", file=sys.stderr)
        return 2

    queue: list = []
    db = SessionLocal()
    try:
        empty_reason = ""
        diagnosis: dict = {}
        if args.latest_auction_job:
            queue, empty_reason, diagnosis = _load_queue_from_latest_job(db, "auction_finder")
            jn = "auction_finder"
        elif args.latest_bin_job:
            queue, empty_reason, diagnosis = _load_queue_from_latest_job(db, "opportunity_finder")
            jn = "opportunity_finder"
        elif args.from_recent_opportunities is not None:
            from backend.utils.vision_queue_from_opportunities import fetch_vision_queue_from_opportunities

            queue = fetch_vision_queue_from_opportunities(
                db,
                limit=args.from_recent_opportunities,
                listing_type=args.listing_type,
            )
            jn = "opportunities_table"
            if not queue:
                print(
                    "No opportunities with HTTP image_url / listing_image_urls found "
                    "(or --listing-type filter excluded them). Ingest pipeline rows first.",
                    file=sys.stderr,
                )
                return 2
            print(
                f"Loaded {len(queue)} listing(s) from opportunities (reason=from_recent_opportunities).",
                flush=True,
            )
        elif args.json:
            queue = json.loads(args.json.read_text(encoding="utf-8"))
            if not isinstance(queue, list):
                print("--json must contain a JSON array", file=sys.stderr)
                return 2
            jn = "json_file"
        else:
            queue = []
            jn = ""

        if args.latest_auction_job or args.latest_bin_job:
            if not queue:
                hints = {
                    "no_completed_job": f"No completed {jn} row in job_runs.",
                    "no_results_summary": f"Latest completed {jn} job has no results_summary JSON.",
                    "unparseable_summary": "results_summary could not be parsed as JSON.",
                    "unified_queue_empty": (
                        "Latest job has vision_post_pipeline_queue_sample: [] — this run queued no listings "
                        "(no BIN price-floor rejects and no suspicious 30–50% SCP BIN samples, or auction had "
                        "no no-pricing / BIN-sanity rows in the sample buckets). "
                        "Use --from-recent-opportunities N or --json to pass URLs manually."
                    ),
                    "unified_queue_bad_type": "vision_post_pipeline_queue_sample is not a JSON array.",
                    "missing_vision_key_rerun_bin_pipeline": (
                        "Latest opportunity_finder job predates vision_post_pipeline_queue_sample. "
                        "Options: (1) python3 find_opportunities.py … to refresh job_runs, "
                        "(2) python3 scripts/vision_retry_scp_from_images.py --from-recent-opportunities 5 --dry-run, "
                        "(3) --json queue.json."
                    ),
                    "auction_no_legacy_queue": (
                        "Latest auction_finder job has no usable vision queue: "
                        "no `vision_post_pipeline_queue_sample`, no legacy `no_scp_vision_queue_sample` list, "
                        "or legacy value is empty/non-list."
                    ),
                    "auction_predates_vision_summary": (
                        "This `job_runs` row was produced by an **older** `find_auction_opportunities.py` "
                        "that did not write `vision_post_pipeline_queue_sample` (and has no legacy queue). "
                        "Re-run the auction pipeline from current main, **or** use "
                        "`--from-recent-opportunities N --listing-type auction` to feed CDN URLs from `opportunities`."
                    ),
                }
                msg = hints.get(
                    empty_reason,
                    f"No vision queue (reason={empty_reason!r}). Run the pipeline or use --json.",
                )
                keys = diagnosis.get("results_summary_keys") or []
                if (
                    jn == "auction_finder"
                    and empty_reason == "auction_no_legacy_queue"
                    and "vision_post_pipeline_queue_sample" not in keys
                    and ("auctions_searched" in keys or "step2_skip_reasons" in keys)
                ):
                    msg = hints["auction_predates_vision_summary"]
                extra = ""
                if diagnosis.get("job_run_id") is not None:
                    extra = f"\nLatest completed job_run.id={diagnosis['job_run_id']}"
                if keys:
                    extra += f"\nresults_summary keys: {keys}"
                if empty_reason == "auction_no_legacy_queue":
                    if diagnosis.get("has_legacy_no_scp_key"):
                        extra += (
                            f"\n(no_scp_vision_queue_sample present: type={diagnosis.get('legacy_type')!r} "
                            f"len={diagnosis.get('legacy_len')!r})"
                        )
                print(f"{msg}{extra}\n(job={jn!r})", file=sys.stderr)
                return 0 if empty_reason == "unified_queue_empty" else 2

        n = 0
        hits = 0
        inserted = 0
        persist = (not args.dry_run) and (not args.no_persist)
        for item in queue:
            if n >= args.limit:
                break
            urls = item.get("image_urls") if isinstance(item, dict) else None
            if not urls:
                continue
            title = (item.get("title") or "") if isinstance(item, dict) else ""
            iid = item.get("ebay_item_id") if isinstance(item, dict) else None
            reason = (item.get("reason") or "") if isinstance(item, dict) else ""
            pipe = (item.get("pipeline_card") or "") if isinstance(item, dict) else ""

            imgs = download_listing_images(urls, max_images=args.max_images)
            if not imgs:
                print(f"SKIP {iid}: no images downloaded ({len(urls)} URLs tried)")
                n += 1
                continue

            if args.dry_run:
                tag = f"{reason}" + (f" | pipeline={pipe[:48]}…" if len(pipe) > 48 else (f" | pipeline={pipe}" if pipe else ""))
                print(
                    f"DRY {iid}: {len(imgs)} images, bytes={[len(x[0]) for x in imgs]} "
                    f"title={title[:60]!r}" + (f" [{tag}]" if tag.strip() else "")
                )
                n += 1
                continue

            try:
                ident = extract_card_identity_nova(imgs, title_hint=title)
            except Exception as e:
                print(f"VISION_FAIL {iid}: {e}", file=sys.stderr)
                n += 1
                continue

            player = ident.get("player_name") or ""
            cn = ident.get("card_number") or ""
            year = ident.get("card_year")
            parallel = ident.get("parallel") or "Base"
            cset = ident.get("card_set") or ""

            cy: int | None = None
            if year is not None:
                try:
                    cy = int(year)
                except (TypeError, ValueError):
                    cy = None

            if not player or not cn:
                print(
                    f"WEAK {iid}: confidence={ident.get('confidence')} "
                    f"player={player!r} #={cn!r} year={year} — {ident.get('notes', '')[:80]}"
                )
                n += 1
                continue

            scp = find_scp_match_for_vision(db, player, cy, cn, parallel, cset)
            if scp and scp.get("scp_price"):
                hits += 1
                mode = scp.get("db_match_mode") or "?"
                note = scp.get("db_match_note") or ""
                tail = f" db_match={mode!r}"
                if note:
                    tail += f" ({note[:100]}{'…' if len(note) > 100 else ''})"
                print(
                    f"HIT  {iid}: {player} {cy or year or '?'} #{cn} [{parallel}] "
                    f"SCP ${scp['scp_price']:.2f} (vision conf={ident.get('confidence')}){tail}"
                    + (f" [queue={reason}]" if reason else "")
                )
                if persist:
                    st, msg = _try_insert_vision_opportunity(
                        db,
                        item=item if isinstance(item, dict) else {},
                        ident=ident,
                        scp=scp,
                        job_source=jn,
                        min_profit=args.min_profit,
                        min_roi=args.min_roi,
                        min_confidence=args.min_confidence,
                    )
                    if st == "inserted":
                        inserted += 1
                        print(f"  DB_INSERT {iid}: {msg}")
                    else:
                        print(f"  DB_SKIP {iid}: {st} ({msg})")
            else:
                hint = vision_scp_miss_hint(db, player, cy, cn)
                print(
                    f"MISS {iid}: {player} {cy or year or '?'} #{cn} [{parallel}] "
                    f"(vision conf={ident.get('confidence')}; {hint})"
                    + (f" [queue={reason}]" if reason else "")
                )
            if pipe and player and player.lower() not in pipe.lower():
                print(
                    f"  !! Review: vision player {player!r} not found in pipeline_card — "
                    f"wrong SCP match, wrong photo, or model parse error "
                    f"[queue={reason or 'n/a'}]"
                )
            n += 1

        if not args.dry_run:
            tail = f" Inserted={inserted}" if persist else ""
            print(f"\nDone. Processed={n} DB_SCP_hits={hits}{tail}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
