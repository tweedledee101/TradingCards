"""
Download eBay CDN listing images and extract card identity via Amazon Nova (OpenAI-compatible).

Uses NOVA_API_KEY + https://api.nova.amazon.com/v1 — no Playwright, no ebay.com HTML.
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

import requests

DEFAULT_NOVA_BASE = "https://api.nova.amazon.com/v1"
DEFAULT_VISION_MODEL = os.getenv("NOVA_VISION_MODEL", "nova-2-lite-v1")

USER_AGENT = (
    "Mozilla/5.0 (compatible; RagnarokGaming/1.0; +https://ragnarokgamez.com) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def download_listing_images(
    urls: List[str],
    *,
    max_images: int = 6,
    max_bytes_per_image: int = 3_500_000,
    timeout: float = 25.0,
) -> List[Tuple[bytes, str]]:
    """Fetch images from eBay CDN URLs. Returns (bytes, mime_type) per image."""
    out: List[Tuple[bytes, str]] = []
    seen: set = set()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    for raw in urls:
        if len(out) >= max_images:
            break
        u = (raw or "").strip()
        if not u.startswith("http") or u in seen:
            continue
        seen.add(u)
        try:
            r = session.get(u, timeout=timeout, stream=True)
            r.raise_for_status()
            ct = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if ct and not ct.startswith("image/"):
                continue
            buf = bytearray()
            for chunk in r.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                buf.extend(chunk)
                if len(buf) > max_bytes_per_image:
                    buf = bytearray()
                    break
            if not buf:
                continue
            mime = ct if ct.startswith("image/") else "image/jpeg"
            if "png" in u.lower():
                mime = "image/png"
            elif "webp" in u.lower():
                mime = "image/webp"
            out.append((bytes(buf), mime))
        except OSError:
            continue
        except requests.RequestException:
            continue

    return out


def _data_url(data: bytes, mime: str) -> str:
    b64 = base64.standard_b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def parse_model_json_response(text: str) -> Dict[str, Any]:
    """Extract a single JSON object from a chat model reply (handles ``` fences)."""
    return _parse_json_object(text)


def _parse_json_object(text: str) -> Dict[str, Any]:
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```\w*\n?", "", t)
        t = re.sub(r"\n?```\s*$", "", t).strip()
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object in model response")
    return json.loads(t[start : end + 1])


def _coerce_identity(raw: Dict[str, Any]) -> Dict[str, Any]:
    y = raw.get("card_year")
    year: Optional[int] = None
    if y is not None and y != "":
        try:
            year = int(y)
        except (TypeError, ValueError):
            pass

    cn = raw.get("card_number")
    card_number = str(cn).strip() if cn is not None else ""

    parallel = (raw.get("parallel_or_insert") or "Base").strip() or "Base"
    player = (raw.get("player_name") or "").strip()
    card_set = (raw.get("set_product_line") or "").strip()

    return {
        "player_name": player,
        "card_number": card_number,
        "card_year": year,
        "parallel": parallel,
        "card_set": card_set,
        "manufacturer_brand": (raw.get("manufacturer_brand") or "").strip(),
        "grading_company": (raw.get("grading_company") or "").strip(),
        "grading_grade": (raw.get("grading_grade") or "").strip(),
        "confidence": (raw.get("confidence") or "unclear").strip().lower(),
        "notes": (raw.get("notes") or "").strip(),
        "_raw": raw,
    }


VISION_PROMPT = """You are an expert at reading sports trading cards from photos.

The images are from an eBay listing (front/back/slab). Extract what you can READ from the card or holder.

Return ONLY a JSON object (no markdown) with exactly these keys:
- player_name (string, empty if unknown)
- card_number (string, the printed card # e.g. "87" or "BCA-AB" — empty if unknown)
- card_year (integer copyright year or season year, or null if unknown)
- manufacturer_brand (string: Topps, Panini, Bowman, etc.)
- set_product_line (string: e.g. "Topps Chrome", "Prizm")
- parallel_or_insert (string: "Base" if clearly base; otherwise color/serial/auto)
- grading_company (string: PSA, BGS, SGC, or empty if raw)
- grading_grade (string: e.g. "10" or "9.5", empty if raw)
- confidence: one of high, medium, low, unclear
- notes (string: blur, stock photo, lot, etc.)

Be conservative: if unsure, use unclear confidence and empty strings."""


def extract_card_identity_nova(
    images: List[Tuple[bytes, str]],
    *,
    title_hint: str = "",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call Nova multimodal chat. Requires ``openai`` package and ``NOVA_API_KEY``.
    """
    key = api_key or os.getenv("NOVA_API_KEY")
    if not key:
        raise RuntimeError("NOVA_API_KEY is not set (backend/.env or environment)")

    try:
        from openai import OpenAI
    except ImportError as e:
        ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        raise RuntimeError(
            "Cannot import `openai`.\n"
            f"  Interpreter: {sys.executable}\n"
            f"  Version:     Python {ver}\n\n"
            "Common causes:\n"
            "  • Broken .venv: `pip` installed into lib/python3.12 but `python` is 3.8 (or the reverse). "
            "Check: `python3 -c \"import sys; print(sys.version)\"` and `ls .venv/lib` — only one version should exist.\n"
            "  • Python 3.8 + openai 2.x: resolver error on `jiter` (needs newer Python). Use Python 3.10+ for the venv.\n\n"
            "Fix (recommended — matches CI Python 3.11):\n"
            "  deactivate 2>/dev/null; rm -rf .venv\n"
            "  python3.12 -m venv .venv   # or python3.11\n"
            "  source .venv/bin/activate\n"
            "  python3 -m pip install -U pip\n"
            "  python3 -m pip install -r backend/requirements.txt\n"
            "  python3 -c \"import openai; print(openai.__file__)\""
        ) from e

    client = OpenAI(api_key=key, base_url=base_url or os.getenv("NOVA_API_BASE", DEFAULT_NOVA_BASE))

    use_model = model or os.getenv("NOVA_VISION_MODEL", DEFAULT_VISION_MODEL)

    parts: List[Dict[str, Any]] = [
        {
            "type": "text",
            "text": VISION_PROMPT
            + (f"\n\nListing title hint (may be wrong): {title_hint[:500]}" if title_hint else ""),
        }
    ]
    for data, mime in images:
        parts.append(
            {"type": "image_url", "image_url": {"url": _data_url(data, mime)}}
        )

    resp = client.chat.completions.create(
        model=use_model,
        messages=[{"role": "user", "content": parts}],
        max_tokens=1200,
        temperature=0.2,
    )
    content = resp.choices[0].message.content
    if not content:
        raise RuntimeError("Empty response from Nova vision model")
    raw = parse_model_json_response(content)
    return _coerce_identity(raw)
