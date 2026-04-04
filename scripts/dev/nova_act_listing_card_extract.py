#!/usr/bin/env python3
"""
Nova Act: read an eBay listing's **images** (main photo + gallery thumbnails) and
extract structured card identity for a **second-pass SCP attempt**.

Use when text/title/aspects failed SCP matching but photos may still identify the card.

  python3.12 scripts/dev/nova_act_listing_card_extract.py \\
    --listing-url "https://www.ebay.com/itm/..."

Output is JSON (stdout). Feed player/year/set/#/parallel guesses into your existing
SCP lookup (not implemented here — this script only extracts).

**Alternative (no eBay HTML):** If you already have **CDN URLs** from the Browse API
(`listing_image_urls` on opportunities or `no_scp_vision_queue_sample` in job results),
a future path is **download bytes + multimodal model** — no Chromium, no Cloudflare
on the listing page. This script still uses the browser for gallery navigation.

Requires: Python 3.10+, nova-act, playwright, NOVA_ACT_API_KEY.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

_PROBE = Path(__file__).resolve().parent / "nova_act_listing_visual_probe.py"
_spec = importlib.util.spec_from_file_location("nova_act_listing_visual_probe", _PROBE)
probe = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(probe)


class CardIdentityFromImages(BaseModel):
    """Fields intentionally loose (strings) — normalize before DB/SCP."""

    player_name: str = Field(default="", description="Best-effort player from card or slab.")
    card_number: str = Field(default="", description="Card # / CN as printed, e.g. 123 or RC-1.")
    card_year: str = Field(
        default="",
        description="Copyright or season year visible on card, else empty.",
    )
    manufacturer_brand: str = Field(default="", description="Topps, Panini, Bowman, etc.")
    set_product_line: str = Field(
        default="",
        description="Chrome, Prizm, Heritage, Update, etc.",
    )
    parallel_insert: str = Field(
        default="",
        description="Refractor color, /199, auto, SP — Base if clearly base.",
    )
    is_rookie_card: bool = Field(default=False, description="True if RC logo or clear 1st year rookie.")
    grading_company: str = Field(default="", description="PSA, BGS, SGC, CGC, or empty if raw.")
    grading_grade: str = Field(default="", description="Numeric grade if slab, else empty.")
    gallery_coverage: str = Field(
        ...,
        description="Which thumbnails you opened (e.g. main + thumb 2 + thumb 3).",
    )
    extraction_confidence: Literal["high", "medium", "low", "unclear"] = Field(
        ...,
        description="How readable and consistent the images were.",
    )
    caveats: str = Field(
        default="",
        description="Stock photo, blurry, lot photo, wrong item, etc.",
    )


def _build_extract_prompt() -> str:
    return """You are extracting trading card identity from an eBay listing for a sports card arbitrage tool.

The browser is on the eBay item page. Rules:
- Do not log in to eBay. Dismiss cookie/consent banners if they block the gallery.
- Inspect the MAIN product image first (largest card photo).
- Then click through **each visible gallery thumbnail** that shows the card (front, back, slab, close-ups). Skip unrelated images (lifestyle, shipping box, graded case only if it shows the label clearly).
- Read text from the card face and slab holder when visible: player, card number, year, brand, set name, parallel, RC, serial number, grading company and grade.
- If images contradict each other, prefer the clearest close-up of the card front; note contradictions in caveats.
- If this is clearly a stock photo or not the actual card, set extraction_confidence to unclear or low and explain in caveats.

Return ONLY JSON matching the provided schema. Use empty strings for unknown text fields."""


def run_card_extraction(
    listing_url: str,
    *,
    headless: bool = False,
    max_steps: int = 40,
) -> CardIdentityFromImages:
    if not listing_url.strip().startswith("http"):
        raise probe.ProbeError("listing_url must be an http(s) URL")
    probe.ensure_live_nova_act_ready()

    from nova_act import ActInvalidModelGenerationError, NovaAct

    schema = CardIdentityFromImages.model_json_schema()
    prompt = _build_extract_prompt()

    try:
        with NovaAct(
            starting_page=listing_url,
            headless=headless,
            screen_width=1280,
            screen_height=720,
        ) as nova:
            try:
                act_result = nova.act_get(prompt, schema=schema, max_steps=max_steps)
            except ActInvalidModelGenerationError as e:
                raise probe.ProbeError(f"Schema validation failed (model output): {e}") from e
        return CardIdentityFromImages.model_validate(act_result.parsed_response)
    except probe.ProbeError:
        raise
    except Exception as e:
        raise probe.ProbeError(f"Nova Act run failed: {e}") from e


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Nova Act: extract card ID from eBay listing images.")
    p.add_argument("--listing-url", default="", help="Full eBay item URL.")
    p.add_argument(
        "--headless",
        action="store_true",
        help="Headless browser (default is headed — you see Chrome).",
    )
    p.add_argument("--max-steps", type=int, default=40)
    args = p.parse_args(argv)

    url = (args.listing_url or "").strip()
    if not url:
        print("Error: pass --listing-url https://www.ebay.com/itm/...", file=sys.stderr)
        return 2

    if not args.headless:
        print(
            "\n>>> Chrome will open — Nova Act will scroll the gallery and read images.\n",
            file=sys.stderr,
        )

    try:
        out = run_card_extraction(url, headless=args.headless, max_steps=args.max_steps)
    except probe.ProbeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 3

    print(json.dumps(out.model_dump(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
