#!/usr/bin/env python3
"""
Full Collectors Edge AI **photo** flow (dev / manual research).

Opens https://collectorsedgeai.com, switches to **Photo**, uploads an image, then
clicks through common CTAs (Get Instant Valuation, Continue, Next, graded/raw prompts)
until a result page stabilizes or timeout. Writes **HTML + screenshot + JSON** (default under
`scripts/dev/_collectors_edge_artifacts/`, or `$TMPDIR/tradingcards_collectors_edge` if not writable).
JSON includes **`ce_extracted`** (structured CE fields), **`ce_pipeline_analysis`** (verification vs our DB row when using ``--from-db``), and flat **`parsed`** for backward compatibility.

**Not** a supported production integration: respect https://collectorsedgeai.com terms,
use your own account if the site requires login, and do not hammer the service.

Requires:
  pip install -r scripts/dev/extra-requirements-collectors-edge.txt
  playwright install chromium

Examples:
  python scripts/dev/collectors_edge_photo_run.py --image-url "https://i.ebayimg.com/..."
  python scripts/dev/collectors_edge_photo_run.py --from-db --headless
  python scripts/dev/collectors_edge_photo_run.py --from-db --db-limit 3 --pause-between-cards 12 --keep-open 20
  python scripts/dev/collectors_edge_photo_run.py --from-db --opportunity-ids 2687,2685 --headless --settle-ms 8000
  python scripts/dev/collectors_edge_photo_run.py --image /tmp/card.jpg --keep-open 30
  python scripts/dev/collectors_edge_photo_run.py --image-url "..." --headless --out-dir /tmp/ce-run
  python scripts/dev/collectors_edge_photo_run.py --image-url "..." --settle-ms 8000 --keep-open 30
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

CE_HOME = "https://collectorsedgeai.com/"
# Avoid overly broad labels (e.g. "View") that match on the final page and stall the loop.
CE_CTA_ROUND = [
    r"Identify\s*&\s*Value",
    r"Identify\s+and\s+Value",
    "Get Instant Valuation",
    "Continue",
    "Next",
    "Submit",
    "Analyze",
    "Valuate",
    "See results",
]
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.utils.collectors_edge_result import (
    analyze_ce_for_pipeline,
    call_ce_identify_api,
    ce_extracted_from_api_json,
    extract_ce_from_body_text,
    extract_ce_from_html,
    flat_parsed_for_legacy,
    merge_ce_extractions,
)


def _ensure_playwright() -> None:
    """Import Playwright; print the *real* error (wrong interpreter is common)."""
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except Exception as e:
        print(
            f"Cannot load Playwright ({type(e).__name__}: {e})\n"
            f"Interpreter in use: {sys.executable}\n"
            "Install into this exact interpreter:\n"
            "  python -m pip install -r scripts/dev/extra-requirements-collectors-edge.txt\n"
            "  python -m playwright install chromium\n"
            "If `python` is not your venv, use the same binary you used for `pip` (e.g. python3.12).",
            file=sys.stderr,
        )
        raise SystemExit(2) from e


def _validate_image_url(url: str) -> None:
    """Fail fast with a clear message when people paste doc placeholders."""
    u = (url or "").strip()
    parsed = urlparse(u)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        print(
            "Invalid --image-url: must start with https:// (you pasted a placeholder, not a real link).\n"
            "  On eBay: open a listing → right‑click the main photo → Copy image address.\n"
            "  Example host: i.ebayimg.com",
            file=sys.stderr,
        )
        raise SystemExit(2)
    low = u.lower()
    if "..." in u or "paste_" in low or "real_full_url" in low or "your_" in low:
        print(
            "Invalid --image-url: still looks like placeholder text, not a real image URL.",
            file=sys.stderr,
        )
        raise SystemExit(2)


def _download_image(url: str, dest: Path) -> None:
    r = requests.get(url, timeout=60, headers={"User-Agent": "TradingCards-CE-probe/1.0"})
    r.raise_for_status()
    ct = (r.headers.get("content-type") or "").lower()
    if "image" not in ct and not url.lower().split("?", 1)[0].endswith((".jpg", ".jpeg", ".png", ".webp")):
        print(
            f"Warning: response Content-Type is {ct!r} — expected an image. Continuing anyway.",
            file=sys.stderr,
        )
    dest.write_bytes(r.content)


def _dismiss_common_banners(page) -> None:
    for label in ("Accept", "Accept all", "Got it", "I agree", "Close"):
        try:
            page.get_by_role("button", name=re.compile(f"^{re.escape(label)}$", re.I)).click(
                timeout=800
            )
            page.wait_for_timeout(300)
        except Exception:
            pass


def _click_photo_tab(page) -> None:
    # Prefer exact tab name from their UI strings.
    for name in ("Photo",):
        try:
            page.get_by_role("tab", name=name).click(timeout=5000)
            return
        except Exception:
            pass
    try:
        page.get_by_text("Photo", exact=True).first.click(timeout=5000)
    except Exception as e:
        raise RuntimeError("Could not switch to Photo mode — UI may have changed.") from e


def _upload_image(page, path: Path) -> None:
    inp = page.locator('input[type="file"]')
    if inp.count() == 0:
        raise RuntimeError("No file input found after Photo tab.")
    inp.first.set_input_files(str(path))


def _try_click_named_buttons(page, names: list[str]) -> bool:
    for raw in names:
        try:
            page.get_by_role("button", name=re.compile(raw, re.I)).first.click(timeout=1500)
            return True
        except Exception:
            pass
    return False


def _try_click_identify_value(page) -> bool:
    """Primary CTA after photo upload on Collectors Edge (often missed if only 'Get Instant Valuation' is listed)."""
    patterns = (
        r"^\s*Identify\s*&\s*Value\s*$",
        r"^\s*Identify\s+and\s+Value\s*$",
        r"Identify\s*&\s*Value",
        r"Identify\s+and\s+Value",
    )
    for pat in patterns:
        rx = re.compile(pat, re.I)
        try:
            page.get_by_role("button", name=rx).first.click(timeout=3000)
            return True
        except Exception:
            pass
        try:
            page.get_by_role("link", name=rx).first.click(timeout=3000)
            return True
        except Exception:
            pass
    try:
        page.get_by_text(re.compile(r"Identify\s*&\s*Value", re.I)).first.click(timeout=3000)
        return True
    except Exception:
        pass
    try:
        page.locator('[role="button"]:has-text("Identify")').filter(has_text=re.compile(r"Value", re.I)).first.click(
            timeout=3000
        )
        return True
    except Exception:
        pass
    return False


def _try_answer_card_state_raw(page) -> bool:
    """If they ask graded vs raw, prefer raw to reduce friction."""
    for pat in (r"Raw\s*/\s*Ungraded", r"^Raw$", r"Ungraded"):
        try:
            page.get_by_role("button", name=re.compile(pat, re.I)).first.click(timeout=1500)
            return True
        except Exception:
            pass
    return False


def _ce_final_page_reached(page_url: str) -> bool:
    """Collectors Edge uses ``/result`` for the valuation view; some flows use ``/cards/...``."""
    path = urlparse(page_url).path.rstrip("/")
    if path == "/result":
        return True
    if "/cards/" in page_url or path.startswith("/cards"):
        return True
    return False


def _result_ready(page) -> bool:
    return _ce_final_page_reached(page.url)


def _pipeline_context_from_db_meta(db_meta: dict[str, Any] | None) -> dict[str, Any] | None:
    if not db_meta:
        return None
    keys = (
        "player_name",
        "card_year",
        "card_set",
        "card_number",
        "parallel",
        "ebay_title",
        "scp_price",
    )
    out = {k: db_meta[k] for k in keys if db_meta.get(k) is not None}
    return out or None


def _failure_message(page) -> str | None:
    try:
        t = page.locator("body").inner_text(timeout=3000)
    except Exception:
        return None
    if "Card analysis failed" in t:
        return "Card analysis failed (site message)"
    if "Card Not Found" in t:
        return "Card Not Found (site message)"
    return None


def _resolve_out_dir(preferred: Path) -> Path:
    """Use repo dir when writable; otherwise /tmp (WSL / root-owned trees often block repo writes)."""
    preferred = preferred.expanduser().resolve()
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        probe = preferred / ".tradingcards_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return preferred
    except OSError as e:
        alt = Path(tempfile.gettempdir()) / "tradingcards_collectors_edge"
        try:
            alt.mkdir(parents=True, exist_ok=True)
        except OSError as e2:
            print(
                f"Cannot write artifacts to {preferred} or {alt}:\n  {e}\n  {e2}",
                file=sys.stderr,
            )
            raise SystemExit(2) from e2
        print(
            f"Note: {preferred} is not writable ({e}); using {alt} for artifacts.",
            file=sys.stderr,
        )
        return alt.resolve()


CE_EXIT_BROWSER_CLOSED = 4
CE_EXIT_INTERRUPTED = 130


def _playwright_target_gone(exc: BaseException) -> bool:
    if type(exc).__name__ == "TargetClosedError":
        return True
    msg = str(exc).lower()
    return "has been closed" in msg or "target closed" in msg


def _safe_page_wait(page, ms: int) -> bool:
    """Sleep on the page unless the user closed the window. Returns False if the page is dead."""
    try:
        if page.is_closed():
            return False
    except Exception:
        return False
    try:
        page.wait_for_timeout(ms)
        return True
    except Exception as e:
        if _playwright_target_gone(e):
            return False
        raise


def _browser_closed_user_hint() -> None:
    print(
        "\nThe browser window was closed while the script was still running "
        "(often during the ~30–60s analysis wait after ‘Identify & Value’).\n"
        "Leave the window open until you see ‘Done.’ and the JSON block, or use --headless.\n",
        file=sys.stderr,
        flush=True,
    )


def _sleep_keep_open(seconds: float) -> bool:
    """Sleep for --keep-open / pause; returns True if user hit Ctrl+C."""
    try:
        time.sleep(seconds)
        return False
    except KeyboardInterrupt:
        print("\nInterrupted (Ctrl+C) during wait — closing browser.", flush=True)
        return True


def _browser_close_quietly(browser) -> None:
    try:
        browser.close()
    except Exception:
        pass


def _try_api_direct(
    image_path: Path,
    *,
    json_out: Path,
    source_image_url: str | None,
    db_meta: dict[str, Any] | None,
    run_label: str,
    merge_payload_out: list[dict[str, Any]] | None = None,
) -> int | None:
    """Try CE tRPC API directly. Returns 0 on success, None to fall back to Playwright."""
    print(f"  Trying CE API direct (no browser)...", flush=True)
    image_bytes = image_path.read_bytes()
    api_json = call_ce_identify_api(image_bytes, timeout=120)
    if api_json is None:
        print(f"  CE API returned nothing -- falling back to Playwright.", flush=True)
        return None

    ce_extracted = ce_extracted_from_api_json(api_json)
    parsed = flat_parsed_for_legacy(ce_extracted)
    pipeline_ctx = _pipeline_context_from_db_meta(db_meta)
    ce_pipeline_analysis = analyze_ce_for_pipeline(ce_extracted, pipeline=pipeline_ctx)

    identity = (parsed.get("card_identity_guess") or "").strip()
    med = parsed.get("median_usd")
    who = ""
    if db_meta:
        oid = db_meta.get("opportunity_id") or db_meta.get("skip_id")
        title = (db_meta.get("ebay_title") or "")[:60]
        who = f" id={oid}" + (f" | {title!r}..." if title else "")
    print(
        f"\n>>> CE API identified{who}\n"
        f"    card: {api_json.get('cardName', '?')}\n"
        f"    median=${med}  player={api_json.get('player', '?')}  "
        f"year={api_json.get('year', '?')}  variant={api_json.get('variant', '?')}\n",
        flush=True,
    )
    vps = ce_pipeline_analysis.get("verification_points") or []
    flags = ce_pipeline_analysis.get("suggested_qa_flags") or []
    if vps:
        print("--- CE vs pipeline (verification) ---", flush=True)
        for line in vps[:6]:
            print(f"  * {line}", flush=True)
    if flags:
        print(f"  suggested_qa_flags: {', '.join(flags)}", flush=True)

    payload: dict[str, Any] = {
        "final_url": "api://collectorsedgeai.com/api/trpc/cards.identifyByImage",
        "source_image_url": source_image_url,
        "database_opportunity": db_meta,
        "parsed": parsed,
        "ce_extracted": ce_extracted,
        "ce_pipeline_analysis": ce_pipeline_analysis,
        "method": "api_direct",
    }
    json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"JSON: {json_out}", flush=True)

    print("\n=== CE_RESULT_JSON ===", flush=True)
    print(json.dumps(payload, indent=2)[:4000], flush=True)
    if len(json.dumps(payload)) > 4000:
        print(f"... (truncated)", flush=True)
    print("=== END CE_RESULT_JSON ===\n", flush=True)

    if merge_payload_out is not None:
        merge_payload_out[:] = [
            {"ce_pipeline_analysis": ce_pipeline_analysis, "db_meta": db_meta},
        ]
    return 0


def _run_one_collectors_edge_card(
    page,
    image_path: Path,
    *,
    png: Path,
    html_out: Path,
    json_out: Path,
    settle_ms: int,
    timeout_ms: int,
    source_image_url: str | None,
    db_meta: dict[str, Any] | None,
    run_label: str,
    merge_payload_out: list[dict[str, Any]] | None = None,
) -> int:
    """One upload → result on an existing Playwright page. Returns 0, 3 (site failure), or 4 (browser closed).

    If ``merge_payload_out`` is a list, on success it is replaced with one dict:
    ``{"ce_pipeline_analysis": ..., "db_meta": ...}`` for DB QA merge.
    """
    print(f"\n{'=' * 72}\n{run_label}\n{'=' * 72}\n", flush=True)

    try:
        page.goto(CE_HOME, wait_until="domcontentloaded")
    except Exception as e:
        if _playwright_target_gone(e):
            _browser_closed_user_hint()
            return CE_EXIT_BROWSER_CLOSED
        raise
    if not _safe_page_wait(page, 1500):
        _browser_closed_user_hint()
        return CE_EXIT_BROWSER_CLOSED
    _dismiss_common_banners(page)

    _click_photo_tab(page)
    if not _safe_page_wait(page, 500):
        _browser_closed_user_hint()
        return CE_EXIT_BROWSER_CLOSED
    _upload_image(page, image_path)
    if not _safe_page_wait(page, 2500):
        _browser_closed_user_hint()
        return CE_EXIT_BROWSER_CLOSED

    clicked_identify = False
    for _ in range(15):
        if _try_click_identify_value(page):
            print("Clicked ‘Identify & Value’ — analysis often takes ~30–60s…", flush=True)
            clicked_identify = True
            if not _safe_page_wait(page, 1500):
                _browser_closed_user_hint()
                return CE_EXIT_BROWSER_CLOSED
            break
        if not _safe_page_wait(page, 1000):
            _browser_closed_user_hint()
            return CE_EXIT_BROWSER_CLOSED
    if not clicked_identify:
        print(
            "Warning: did not find ‘Identify & Value’ after upload — trying other CTAs in the main loop.",
            file=sys.stderr,
        )

    deadline = time.monotonic() + max(timeout_ms / 1000, 90)

    while time.monotonic() < deadline:
        try:
            if page.is_closed():
                _browser_closed_user_hint()
                return CE_EXIT_BROWSER_CLOSED
            fail = _failure_message(page)
        except Exception as e:
            if _playwright_target_gone(e):
                _browser_closed_user_hint()
                return CE_EXIT_BROWSER_CLOSED
            raise
        if fail:
            page.screenshot(path=str(png), full_page=True)
            html_out.write_text(page.content(), encoding="utf-8")
            print(f"FAIL: {fail}\n  screenshot: {png}\n  html: {html_out}", file=sys.stderr)
            return 3

        try:
            ready = _result_ready(page)
        except Exception as e:
            if _playwright_target_gone(e):
                _browser_closed_user_hint()
                return CE_EXIT_BROWSER_CLOSED
            raise
        if ready:
            print(
                f"Result page ({page.url}) — waiting {settle_ms}ms for render, then saving…",
                flush=True,
            )
            if not _safe_page_wait(page, settle_ms):
                _browser_closed_user_hint()
                return CE_EXIT_BROWSER_CLOSED
            break

        progressed = False
        progressed |= _try_answer_card_state_raw(page)
        progressed |= _try_click_identify_value(page)
        progressed |= _try_click_named_buttons(page, CE_CTA_ROUND)
        if progressed:
            if not _safe_page_wait(page, 1200):
                _browser_closed_user_hint()
                return CE_EXIT_BROWSER_CLOSED
            continue

        if not _safe_page_wait(page, 2000):
            _browser_closed_user_hint()
            return CE_EXIT_BROWSER_CLOSED

    if page.is_closed():
        _browser_closed_user_hint()
        return CE_EXIT_BROWSER_CLOSED

    if not _ce_final_page_reached(page.url):
        print(
            "\nNote: URL is not /result or /cards/… — check screenshot/HTML (login, limits, UI change).",
            file=sys.stderr,
        )

    print("Writing screenshot + HTML + JSON summary…", flush=True)
    if not _safe_page_wait(page, 800):
        _browser_closed_user_hint()
        return CE_EXIT_BROWSER_CLOSED
    html_raw = ""
    try:
        page.screenshot(path=str(png), full_page=True)
        html_raw = page.content()
        html_out.write_text(html_raw, encoding="utf-8")
    except Exception as e:
        if _playwright_target_gone(e):
            _browser_closed_user_hint()
            return CE_EXIT_BROWSER_CLOSED
        raise

    full_text = ""
    try:
        full_text = page.locator("body").inner_text(timeout=8000)
    except Exception as e:
        if _playwright_target_gone(e):
            _browser_closed_user_hint()
            return CE_EXIT_BROWSER_CLOSED
        pass

    body_ex = extract_ce_from_body_text(full_text) if full_text else {}
    html_ex = extract_ce_from_html(html_raw)
    ce_extracted = merge_ce_extractions(body_ex, html_ex)
    parsed = flat_parsed_for_legacy(ce_extracted)
    pipeline_ctx = _pipeline_context_from_db_meta(db_meta)
    ce_pipeline_analysis = analyze_ce_for_pipeline(ce_extracted, pipeline=pipeline_ctx)

    identity = (parsed.get("card_identity_guess") or "").strip()
    med = parsed.get("median_usd")
    who = ""
    if db_meta:
        oid = db_meta.get("opportunity_id")
        title = (db_meta.get("ebay_title") or "")[:60]
        who = f" opp_id={oid}" + (f" | {title!r}…" if title else "")
    print(
        f"\n>>> Identified{who}\n"
        f"    parsed median_usd={med!r}  identity_snippet={identity[:120]!r}\n",
        flush=True,
    )
    vps = ce_pipeline_analysis.get("verification_points") or []
    flags = ce_pipeline_analysis.get("suggested_qa_flags") or []
    if vps:
        print("--- CE vs pipeline (verification) ---", flush=True)
        for line in vps[:6]:
            print(f"  • {line}", flush=True)
    if flags:
        print(f"  suggested_qa_flags: {', '.join(flags)}", flush=True)

    payload: dict[str, Any] = {
        "final_url": page.url,
        "source_image_url": source_image_url,
        "database_opportunity": db_meta,
        "parsed": parsed,
        "ce_extracted": ce_extracted,
        "ce_pipeline_analysis": ce_pipeline_analysis,
        "artifacts": {
            "png": str(png),
            "html": str(html_out),
            "json": str(json_out),
        },
    }
    json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"URL: {page.url}")
    print(f"Screenshot: {png}")
    print(f"HTML: {html_out}")
    print(f"JSON: {json_out}")
    print("\n=== CE_RESULT_JSON ===", flush=True)
    print(json.dumps(payload, indent=2), flush=True)
    print("=== END CE_RESULT_JSON ===\n", flush=True)

    if full_text:
        snippet = re.sub(r"\s+", " ", full_text).strip()[:900]
        print("--- text preview (truncated) ---\n", snippet, "\n---\n", sep="", flush=True)

    if merge_payload_out is not None:
        merge_payload_out[:] = [
            {"ce_pipeline_analysis": ce_pipeline_analysis, "db_meta": db_meta},
        ]
    return 0


def _persist_ce_qa_to_db(payload: dict[str, Any]) -> None:
    """Merge CE ``suggested_qa_flags`` into ``opportunities.qa_flags`` when ``--merge-qa-to-db`` is set."""
    db_meta = payload.get("db_meta") or {}
    oid = db_meta.get("opportunity_id")
    if oid is None:
        print(
            "CE merge skipped: no opportunity_id on database_opportunity payload.",
            file=sys.stderr,
            flush=True,
        )
        return
    analysis = payload.get("ce_pipeline_analysis")
    try:
        from backend.utils.collectors_edge_qa_merge import opportunity_updates_from_ce_analysis
        from backend.utils.database import SessionLocal
        from backend.models import Opportunity
    except ImportError as e:
        print(f"CE merge skipped: cannot import DB ({e}).", file=sys.stderr, flush=True)
        return

    db = SessionLocal()
    try:
        opp = db.query(Opportunity).filter(Opportunity.id == int(oid)).first()
        if not opp:
            print(f"CE merge skipped: opportunities.id={oid} not found.", file=sys.stderr, flush=True)
            return
        updates = opportunity_updates_from_ce_analysis(
            existing_qa_flags=opp.qa_flags,
            qa_status=opp.qa_status,
            flagged=opp.flagged,
            ce_pipeline_analysis=analysis,
        )
        opp.qa_flags = updates["qa_flags"]
        if "qa_status" in updates:
            opp.qa_status = updates["qa_status"]
        if "flagged" in updates:
            opp.flagged = updates["flagged"]
        db.commit()
        nce = sum(
            1
            for f in (updates["qa_flags"] or [])
            if isinstance(f, dict) and str(f.get("rule", "")).startswith("ce_")
        )
        print(
            f"CE QA merge: opportunities.id={oid} — {nce} ce_* flag(s), qa_status={opp.qa_status!r}.",
            flush=True,
        )
    except Exception as e:
        db.rollback()
        print(f"CE merge failed for opportunities.id={oid}: {e}", file=sys.stderr, flush=True)
    finally:
        db.close()


def run_flow(
    image_path: Path,
    *,
    headless: bool,
    timeout_ms: int,
    slow_mo_ms: int,
    keep_open_s: float,
    out_dir: Path,
    viewport: tuple[int, int],
    settle_ms: int,
    source_image_url: str | None = None,
    db_meta: dict[str, Any] | None = None,
    merge_qa_to_db: bool = False,
    no_api: bool = False,
) -> int:
    from playwright.sync_api import sync_playwright

    out_dir = _resolve_out_dir(out_dir)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    stem = f"collectors_edge_{stamp}"
    png = out_dir / f"{stem}.png"
    html_out = out_dir / f"{stem}.html"
    json_out = out_dir / f"{stem}.json"

    # Try API direct first (no browser needed)
    if not no_api:
        merge_holder: list[dict[str, Any]] = []
        rc = _try_api_direct(
            image_path,
            json_out=json_out,
            source_image_url=source_image_url,
            db_meta=db_meta,
            run_label="Collectors Edge — API direct",
            merge_payload_out=merge_holder if merge_qa_to_db else None,
        )
        if rc is not None:
            if merge_qa_to_db and rc == 0 and merge_holder:
                _persist_ce_qa_to_db(merge_holder[0])
            return rc

    # Fallback to Playwright browser
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=slow_mo_ms)
        context = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
        page = context.new_page()
        page.set_default_timeout(timeout_ms)

        merge_holder_pw: list[dict[str, Any]] = []
        rc = _run_one_collectors_edge_card(
            page,
            image_path,
            png=png,
            html_out=html_out,
            json_out=json_out,
            settle_ms=settle_ms,
            timeout_ms=timeout_ms,
            source_image_url=source_image_url,
            db_meta=db_meta,
            run_label="Collectors Edge — single run (Playwright fallback)",
            merge_payload_out=merge_holder_pw if merge_qa_to_db else None,
        )
        if merge_qa_to_db and rc == 0 and merge_holder_pw:
            _persist_ce_qa_to_db(merge_holder_pw[0])

        interrupted = False
        if keep_open_s > 0 and not headless:
            print(f"\nDone. Keeping browser open {keep_open_s:.0f}s — close the window or Ctrl+C.", flush=True)
            interrupted = _sleep_keep_open(keep_open_s)
        else:
            print("\nDone. Closing browser.", flush=True)

        _browser_close_quietly(browser)

    if interrupted:
        return CE_EXIT_INTERRUPTED
    return rc


def run_flow_db_sequence(
    jobs: list[tuple[Path, str | None, dict[str, Any] | None]],
    *,
    headless: bool,
    timeout_ms: int,
    slow_mo_ms: int,
    keep_open_s: float,
    pause_between_cards_s: float,
    out_dir: Path,
    viewport: tuple[int, int],
    settle_ms: int,
    merge_qa_to_db: bool = False,
    no_api: bool = False,
) -> int:
    """Process multiple cards. Tries API direct per card; falls back to shared Playwright session."""
    if not jobs:
        return 0

    out_dir = _resolve_out_dir(out_dir)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    n = len(jobs)
    exit_rc = 0

    # Try API direct for each card first (no browser needed)
    if not no_api:
        remaining_jobs: list[tuple[int, Path, str | None, dict[str, Any] | None]] = []
        for i, (image_path, source_image_url, db_meta) in enumerate(jobs):
            json_out = out_dir / f"collectors_edge_{stamp}_{i + 1:02d}_of_{n:02d}.json"
            label = f"Card {i + 1} of {n}"
            if db_meta and db_meta.get("opportunity_id") is not None:
                label += f" (opportunity_id={db_meta['opportunity_id']})"

            merge_holder: list[dict[str, Any]] = []
            rc = _try_api_direct(
                image_path,
                json_out=json_out,
                source_image_url=source_image_url,
                db_meta=db_meta,
                run_label=label,
                merge_payload_out=merge_holder if merge_qa_to_db else None,
            )
            if rc is not None:
                if merge_qa_to_db and rc == 0 and merge_holder:
                    _persist_ce_qa_to_db(merge_holder[0])
                if rc != 0:
                    exit_rc = rc
            else:
                remaining_jobs.append((i, image_path, source_image_url, db_meta))

            if i < n - 1 and pause_between_cards_s > 0:
                time.sleep(pause_between_cards_s)

        if not remaining_jobs:
            print(f"\nDone. All {n} card(s) processed via API direct.", flush=True)
            return exit_rc
        print(f"\n{len(remaining_jobs)} card(s) need Playwright fallback...", flush=True)
    else:
        remaining_jobs = [(i, p, u, m) for i, (p, u, m) in enumerate(jobs)]

    # Playwright fallback for cards that failed API
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=slow_mo_ms)
        context = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
        page = context.new_page()
        page.set_default_timeout(timeout_ms)

        interrupted = False
        stop_sequence = False
        for idx, (orig_i, image_path, source_image_url, db_meta) in enumerate(remaining_jobs):
            stem = f"collectors_edge_{stamp}_{orig_i + 1:02d}_of_{n:02d}"
            png = out_dir / f"{stem}.png"
            html_out = out_dir / f"{stem}.html"
            json_out = out_dir / f"{stem}.json"
            label = f"Card {orig_i + 1} of {n} -- Playwright fallback"
            if db_meta and db_meta.get("opportunity_id") is not None:
                label += f" (opportunity_id={db_meta['opportunity_id']})"

            merge_holder_pw: list[dict[str, Any]] = []
            rc = _run_one_collectors_edge_card(
                page, image_path,
                png=png, html_out=html_out, json_out=json_out,
                settle_ms=settle_ms, timeout_ms=timeout_ms,
                source_image_url=source_image_url, db_meta=db_meta,
                run_label=label,
                merge_payload_out=merge_holder_pw if merge_qa_to_db else None,
            )
            if merge_qa_to_db and rc == 0 and merge_holder_pw:
                _persist_ce_qa_to_db(merge_holder_pw[0])
            if rc != 0:
                exit_rc = rc
            if rc == CE_EXIT_BROWSER_CLOSED:
                stop_sequence = True
                break

            is_last = idx == len(remaining_jobs) - 1
            if not is_last and pause_between_cards_s > 0:
                if _sleep_keep_open(pause_between_cards_s):
                    interrupted = True
                    break

        if not interrupted and not stop_sequence and keep_open_s > 0 and not headless:
            interrupted = _sleep_keep_open(keep_open_s)

        _browser_close_quietly(browser)

    return CE_EXIT_INTERRUPTED if interrupted else exit_rc


def main(argv: list[str] | None = None) -> int:
    _ensure_playwright()

    p = argparse.ArgumentParser(description="Run Collectors Edge AI photo valuation (dev probe).")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--image-url", help="HTTP(S) URL to download (e.g. eBay CDN image).")
    g.add_argument("--image", type=Path, help="Local image path (jpg/png/webp).")
    g.add_argument(
        "--from-db",
        action="store_true",
        help="Use first opportunity image from DB (needs backend/.env + pip install -r backend/requirements.txt).",
    )

    p.add_argument("--headless", action="store_true", help="Run without visible window.")
    p.add_argument(
        "--timeout-ms",
        type=int,
        default=180_000,
        help="Playwright default timeout (photo analysis + navigation can exceed 60s).",
    )
    p.add_argument("--slow-mo-ms", type=int, default=0, help="Slow motion for debugging.")
    p.add_argument("--keep-open", type=float, default=0, help="Seconds to keep headed browser open at end.")
    p.add_argument(
        "--out-dir",
        type=Path,
        default=_REPO_ROOT / "scripts" / "dev" / "_collectors_edge_artifacts",
        help="Where to write screenshot, HTML, and JSON.",
    )
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=800)
    p.add_argument(
        "--settle-ms",
        type=int,
        default=5000,
        help="After /result or /cards/ URL, wait this long (ms) before capture so lazy content can render.",
    )
    p.add_argument(
        "--db-skip",
        type=int,
        default=0,
        metavar="N",
        help="With --from-db: skip the first N opportunities that have an image URL (default 0).",
    )
    p.add_argument(
        "--db-listing-type",
        default="all",
        metavar="TYPE",
        help="With --from-db: filter opportunities.listing_type (default all).",
    )
    p.add_argument(
        "--db-limit",
        type=int,
        default=1,
        metavar="N",
        help="With --from-db: process N opportunities in one browser session (default 1).",
    )
    p.add_argument(
        "--pause-between-cards",
        type=float,
        default=8.0,
        metavar="SEC",
        help="With --from-db and N>1: pause between cards so you can read the result (default 8; 0 to go immediately).",
    )
    p.add_argument(
        "--opportunity-ids",
        default=None,
        metavar="IDS",
        help="With --from-db: comma-separated opportunity ids (order preserved). Skips ids with no image URL.",
    )
    p.add_argument(
        "--merge-qa-to-db",
        action="store_true",
        help="With --from-db: after each successful run, merge CE suggested_qa_flags into opportunities.qa_flags.",
    )
    p.add_argument(
        "--no-api",
        action="store_true",
        help="Skip direct API call, always use Playwright browser (slower but captures screenshots).",
    )

    args = p.parse_args(argv)

    if args.merge_qa_to_db and not args.from_db:
        print("--merge-qa-to-db only applies with --from-db.", file=sys.stderr)
        return 2

    tmp_download_paths: list[Path] = []
    try:
        if args.from_db:
            try:
                from dotenv import load_dotenv
            except ImportError as e:
                print(
                    "Missing python-dotenv. Install backend deps:\n"
                    "  python -m pip install -r backend/requirements.txt",
                    file=sys.stderr,
                )
                raise SystemExit(2) from e
            load_dotenv(_REPO_ROOT / "backend" / ".env")
            try:
                from backend.utils.database import SessionLocal
                from backend.utils.opportunity_image_urls import (
                    iter_opportunity_image_rows,
                    iter_opportunity_rows_by_ids,
                )
            except ImportError as e:
                print(
                    "Cannot import backend DB helpers. Install:\n"
                    "  python -m pip install -r backend/requirements.txt",
                    file=sys.stderr,
                )
                raise SystemExit(2) from e
            db = SessionLocal()
            try:
                if args.opportunity_ids:
                    raw_ids = [x.strip() for x in args.opportunity_ids.split(",") if x.strip()]
                    want: list[int] = []
                    for x in raw_ids:
                        try:
                            want.append(int(x, 10))
                        except ValueError:
                            print(f"Ignoring non-integer opportunity id: {x!r}", file=sys.stderr)
                    if not want:
                        print("No valid integers in --opportunity-ids.", file=sys.stderr)
                        return 2
                    rows = list(iter_opportunity_rows_by_ids(db, want))
                    found_ids = {m.get("opportunity_id") for _, m, _ in rows}
                    missing = [i for i in want if i not in found_ids]
                    if missing:
                        print(
                            f"Note: skipped opportunity ids (not found or no HTTP image URL): {missing}",
                            file=sys.stderr,
                        )
                else:
                    rows = list(
                        iter_opportunity_image_rows(
                            db,
                            listing_type=args.db_listing_type,
                            skip=max(0, args.db_skip),
                            limit=max(1, args.db_limit),
                        )
                    )
            finally:
                db.close()
            if not rows:
                print(
                    "No opportunity with image URLs found (check DB, --db-skip, --db-listing-type, --opportunity-ids).",
                    file=sys.stderr,
                )
                return 2

            jobs: list[tuple[Path, str, dict[str, Any]]] = []
            for first_url, db_meta, _all_urls in rows:
                _validate_image_url(first_url)
                suffix = ".jpg"
                low = first_url.lower()
                if ".png" in low:
                    suffix = ".png"
                elif ".webp" in low:
                    suffix = ".webp"
                tfp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
                tfp.close()
                path = Path(tfp.name)
                tmp_download_paths.append(path)
                print(f"Downloading DB listing image ({first_url[:80]}...)")
                _download_image(first_url, path)
                jobs.append((path, first_url, db_meta))

            if len(jobs) == 1:
                p0, u0, m0 = jobs[0]
                return run_flow(
                    p0,
                    headless=args.headless,
                    timeout_ms=args.timeout_ms,
                    slow_mo_ms=args.slow_mo_ms,
                    keep_open_s=args.keep_open,
                    out_dir=args.out_dir,
                    viewport=(args.width, args.height),
                    settle_ms=max(0, args.settle_ms),
                    source_image_url=u0,
                    db_meta=m0,
                    merge_qa_to_db=args.merge_qa_to_db,
                    no_api=args.no_api,
                )

            return run_flow_db_sequence(
                jobs,
                headless=args.headless,
                timeout_ms=args.timeout_ms,
                slow_mo_ms=args.slow_mo_ms,
                keep_open_s=args.keep_open,
                pause_between_cards_s=max(0.0, args.pause_between_cards),
                out_dir=args.out_dir,
                viewport=(args.width, args.height),
                settle_ms=max(0, args.settle_ms),
                merge_qa_to_db=args.merge_qa_to_db,
                no_api=args.no_api,
            )

        if args.image_url:
            source_image_url = args.image_url
            _validate_image_url(args.image_url)
            suffix = ".jpg"
            low = args.image_url.lower()
            if ".png" in low:
                suffix = ".png"
            elif ".webp" in low:
                suffix = ".webp"
            tfp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
            tfp.close()
            path = Path(tfp.name)
            tmp_download_paths.append(path)
            print(f"Downloading {args.image_url[:80]}...")
            _download_image(args.image_url, path)
            return run_flow(
                path,
                headless=args.headless,
                timeout_ms=args.timeout_ms,
                slow_mo_ms=args.slow_mo_ms,
                keep_open_s=args.keep_open,
                out_dir=args.out_dir,
                viewport=(args.width, args.height),
                settle_ms=max(0, args.settle_ms),
                source_image_url=source_image_url,
                db_meta=None,
                no_api=args.no_api,
            )

        path = args.image.expanduser().resolve()
        if not path.is_file():
            print(f"Not a file: {path}", file=sys.stderr)
            return 2

        return run_flow(
            path,
            headless=args.headless,
            timeout_ms=args.timeout_ms,
            slow_mo_ms=args.slow_mo_ms,
            keep_open_s=args.keep_open,
            out_dir=args.out_dir,
            viewport=(args.width, args.height),
            settle_ms=max(0, args.settle_ms),
            source_image_url=None,
            db_meta=None,
            no_api=args.no_api,
        )
    finally:
        for pth in tmp_download_paths:
            try:
                pth.unlink(missing_ok=True)
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
