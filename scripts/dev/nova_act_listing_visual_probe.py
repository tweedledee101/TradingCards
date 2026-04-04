#!/usr/bin/env python3
"""
Proof-of-concept: use Amazon Nova Act's browser agent to *see* an eBay listing
(vision over screenshots per Nova Act design) and score whether the main
product photo plausibly matches an expected card identity (e.g. SCP lookup result).

Docs (read first):
  https://docs.aws.amazon.com/nova-act/latest/userguide/what-is-nova-act.html
  https://github.com/aws/nova-act (SDK README: act(), act_get(), schemas)

Requires:
  Python 3.10+ (PyPI nova-act requires >=3.10; Ubuntu/WSL default python3 is often 3.8/3.9)
  pip install nova-act pydantic
  playwright install chrome   # recommended by Nova Act
  export NOVA_ACT_API_KEY="..."   # from https://nova.amazon.com/act

This is intentionally separate from scripts that call https://api.nova.amazon.com/v1
chat completions (e.g. scripts/dev/test_nova_act_real_data.py): those are not
guaranteed to run a real browser; this script uses the Playwright-backed SDK.

Usage:
  python scripts/dev/nova_act_listing_visual_probe.py --dry-run
  python scripts/dev/nova_act_listing_visual_probe.py \\
    --listing-url "https://www.ebay.com/itm/..." \\
    --expected "2023 Topps Chrome Julio Rodriguez base rookie"
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_ENV = _REPO_ROOT / "backend" / ".env"
# PyPI package ``nova-act`` declares requires-python >= 3.10; older ``python3`` gets "No matching distribution".
_NOVA_ACT_MIN_PY = (3, 10)


def _nova_act_python_ok() -> bool:
    return sys.version_info[:2] >= _NOVA_ACT_MIN_PY


def _load_nova_env() -> None:
    """Load backend/.env if present; map NOVA_API_KEY → NOVA_ACT_API_KEY when needed."""
    if _BACKEND_ENV.is_file():
        try:
            from dotenv import load_dotenv

            load_dotenv(_BACKEND_ENV)
        except ImportError:
            pass
    if not os.getenv("NOVA_ACT_API_KEY") and os.getenv("NOVA_API_KEY"):
        os.environ["NOVA_ACT_API_KEY"] = os.environ["NOVA_API_KEY"]


class ProbeError(RuntimeError):
    """Live probe preflight or Nova Act run failure."""


class ListingVisualAssessment(BaseModel):
    """Structured output from act_get; keep fields simple for schema reliability."""

    main_image_summary: str = Field(
        ...,
        description="What the primary listing photo shows: player, year, set hints, parallel color, raw vs slab.",
    )
    visible_grading: str = Field(
        default="",
        description="Grading company and grade if visible on slab or label, else empty string.",
    )
    match_confidence: Literal["high", "medium", "low", "unclear"] = Field(
        ...,
        description="How well the visible card matches the expected identity.",
    )
    reasoning: str = Field(
        ...,
        description="Short justification referencing visible cues vs expected card.",
    )


def _nova_act_available() -> bool:
    return importlib.util.find_spec("nova_act") is not None


def ensure_live_nova_act_ready() -> None:
    """Load backend/.env, then validate API key, Python version, and nova_act import."""
    _load_nova_env()
    if not os.getenv("NOVA_ACT_API_KEY"):
        raise ProbeError(
            "NOVA_ACT_API_KEY is not set (and NOVA_API_KEY missing). "
            "Use backend/.env or export; keys from https://nova.amazon.com/act"
        )
    if not _nova_act_python_ok():
        raise ProbeError("Python 3.10+ required for nova-act (see script docstring)")
    if not _nova_act_available():
        raise ProbeError(
            "nova_act is not installed for this interpreter "
            f"({sys.executable}). Try: {sys.executable} -m pip install --user nova-act"
        )


def run_listing_visual_assessment(
    listing_url: str,
    expected_identity: str,
    *,
    headless: bool = False,
    max_steps: int = 28,
) -> ListingVisualAssessment:
    """
    Run one act_get session. Calls ensure_live_nova_act_ready() internally.
    Raises ProbeError on preflight or model failures.
    """
    if not listing_url.strip().startswith("http"):
        raise ProbeError("listing_url must be an http(s) URL")
    if not (expected_identity or "").strip():
        raise ProbeError("expected_identity is required")

    ensure_live_nova_act_ready()

    from nova_act import ActInvalidModelGenerationError, NovaAct

    prompt = _build_prompt(expected_identity)
    schema = ListingVisualAssessment.model_json_schema()

    try:
        with NovaAct(
            starting_page=listing_url,
            headless=headless,
            screen_width=1280,
            screen_height=720,
        ) as nova:
            try:
                act_result = nova.act_get(
                    prompt,
                    schema=schema,
                    max_steps=max_steps,
                )
            except ActInvalidModelGenerationError as e:
                raise ProbeError(f"Schema validation failed (model output): {e}") from e

        return ListingVisualAssessment.model_validate(act_result.parsed_response)
    except ProbeError:
        raise
    except Exception as e:
        raise ProbeError(f"Nova Act run failed: {e}") from e


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Nova Act visual probe: eBay listing photo vs expected card identity."
    )
    p.add_argument(
        "--listing-url",
        default=os.getenv("EBAY_LISTING_URL", ""),
        help="Full https URL to an eBay item page (or set EBAY_LISTING_URL).",
    )
    p.add_argument(
        "--expected",
        required=False,
        default="",
        help='Expected card identity, e.g. "2022 Bowman Chrome Elly De La Cruz 1st refractor".',
    )
    p.add_argument(
        "--headless",
        action="store_true",
        help="Run Chromium headless (see Nova Act docs for debugging headless).",
    )
    p.add_argument(
        "--max-steps",
        type=int,
        default=28,
        help="Max agent steps per act_get (default 28; eBay can be noisy).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print prompt + JSON schema and exit (no browser, no API).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    _load_nova_env()

    if args.dry_run:
        schema = ListingVisualAssessment.model_json_schema()
        prompt = _build_prompt(args.expected or "(not set — pass --expected)")
        print("=== Dry run: Nova Act listing visual probe ===\n")
        print("Listing URL:", args.listing_url or "(set --listing-url or EBAY_LISTING_URL)")
        print("\n--- Prompt (excerpt) ---\n")
        print(prompt[:2000] + ("..." if len(prompt) > 2000 else ""))
        print("\n--- Pydantic JSON schema ---\n")
        print(json.dumps(schema, indent=2))
        py_hint = ""
        if not _nova_act_python_ok():
            py_hint = (
                f"\nNOTE: This interpreter is Python {sys.version_info.major}.{sys.version_info.minor}; "
                "nova-act needs 3.10+. Use python3.12 (or a venv) for a live run — see stderr message "
                "from a non-dry-run on this interpreter.\n"
            )
        print(
            "\nInstall (use Python 3.10+ and the SAME interpreter you run this script with):\n"
            f"  {sys.executable} -m pip install --user nova-act\n"
            f"  {sys.executable} -m playwright install chrome\n"
            "API key: NOVA_ACT_API_KEY (or NOVA_API_KEY in backend/.env — auto-loaded from repo root)"
            + py_hint
        )
        return 0

    if not args.listing_url:
        print("Error: --listing-url or EBAY_LISTING_URL is required.", file=sys.stderr)
        return 2
    if not args.expected:
        print("Error: --expected is required for a meaningful comparison.", file=sys.stderr)
        return 2

    print("Starting Nova Act session (first run may take 1–2 minutes for Playwright)...")
    try:
        assessment = run_listing_visual_assessment(
            args.listing_url,
            args.expected,
            headless=args.headless,
            max_steps=args.max_steps,
        )
    except ProbeError as e:
        msg = str(e)
        if "NOVA_ACT_API_KEY" in msg or "NOVA_API_KEY" in msg:
            print(f"Error: {msg}", file=sys.stderr)
            return 2
        if "Python 3.10+" in msg:
            exe = sys.executable
            ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            print(
                "Error: nova-act requires Python 3.10 or newer (PyPI: requires-python >=3.10).\n"
                f"  Interpreter: {exe}\n"
                f"  Version:     {ver}\n"
                "\n"
                "On Ubuntu/WSL, default python3 is often 3.8/3.9, so "
                "python3 -m pip install nova-act fails with \"No matching distribution\".\n"
                "\n"
                "Fix (pick one):\n"
                "  sudo apt update && sudo apt install -y python3.12 python3.12-venv\n"
                "  python3.12 -m venv ~/.venv-novaact && source ~/.venv-novaact/bin/activate\n"
                "  python -m pip install -U pip nova-act && python -m playwright install chrome\n"
                "  python scripts/dev/nova_act_listing_visual_probe.py --listing-url '...' --expected '...'\n"
                "\n"
                "Or without venv (user install):\n"
                "  python3.12 -m pip install --user nova-act\n"
                "  python3.12 -m playwright install chrome\n"
                "  python3.12 scripts/dev/nova_act_listing_visual_probe.py ...\n",
                file=sys.stderr,
            )
            return 2
        if "nova_act is not installed" in msg:
            exe = sys.executable
            ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            print(
                f"Error: {msg}\n"
                f"  Interpreter: {exe}\n"
                f"  Version:     {ver}\n"
                "\n"
                "Install with:\n"
                f"  {exe} -m pip install --user nova-act\n"
                "Then install browsers (once):\n"
                f"  {exe} -m playwright install chrome\n"
                "\n"
                "If pip says \"No matching distribution\", your Python is below 3.10 — see error above.\n"
                "\n"
                "Verify:\n"
                f"  {exe} -c \"import nova_act; print('ok', nova_act.__file__)\"",
                file=sys.stderr,
            )
            return 2
        print(f"Error: {msg}", file=sys.stderr)
        return 3

    print(json.dumps(assessment.model_dump(), indent=2))
    return 0


def _build_prompt(expected_identity: str) -> str:
    return f"""You are verifying a sports trading card eBay listing for purchase safety.

The browser is already on the eBay item page. Rules:
- If a cookie or privacy consent banner blocks the listing, dismiss it if you can without signing in.
- Do not log in to eBay.
- Focus on the MAIN product image (largest photo of the card). If the gallery requires clicking the first thumbnail to see the card clearly, do that.
- Read visible text on the card or slab when possible (player, year, brand, "RC", refractor color, grade).

Expected card identity (from our catalog / SCP search): {expected_identity}

Task: Decide how well the visible listing photo matches that expected identity based on what you SEE, not only the listing title (titles can be wrong).

Return ONLY fields that satisfy the provided JSON schema.
Be honest: use "unclear" if the photo is blurry, stock image, or ambiguous."""


if __name__ == "__main__":
    raise SystemExit(main())
