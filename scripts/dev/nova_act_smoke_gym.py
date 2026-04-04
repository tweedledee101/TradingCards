#!/usr/bin/env python3
"""
Watch Nova Act drive a browser — no eBay URL required.

Uses Amazon's public Nova Act *gym* page (same domain family as the product).
Default is **headed** so a Chrome window opens on your machine.

  python3.12 scripts/dev/nova_act_smoke_gym.py          # watch the browser
  python3.12 scripts/dev/nova_act_smoke_gym.py --headless   # CI / no display

Requires: Python 3.10+, nova-act, playwright browsers, NOVA_ACT_API_KEY (backend/.env ok).
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

_PROBE = Path(__file__).resolve().parent / "nova_act_listing_visual_probe.py"
_spec = importlib.util.spec_from_file_location("nova_act_listing_visual_probe", _PROBE)
probe = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(probe)

GYM_URL = "https://nova.amazon.com/act/gym/next-dot/search"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Nova Act smoke: drive browser on official gym page.")
    p.add_argument("--headless", action="store_true", help="No visible window (for servers/CI).")
    p.add_argument("--max-steps", type=int, default=12)
    args = p.parse_args(argv)

    try:
        probe.ensure_live_nova_act_ready()
    except probe.ProbeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    from nova_act import NovaAct

    if not args.headless:
        print(
            "\n>>> Opening Chrome — watch the window. Nova Act will dismiss banners if needed "
            "and interact with the demo page, then stop.\n"
        )
    else:
        print("Running headless (no display).")

    # WSL2 / Wayland / odd window managers can yield 0×0 viewport → screenshot fails.
    # Nova Act docs: use explicit screen dimensions in that case.
    try:
        with NovaAct(
            starting_page=GYM_URL,
            headless=args.headless,
            screen_width=1280,
            screen_height=720,
        ) as nova:
            nova.act(
                "If a cookie or consent banner blocks the page, dismiss it without signing in. "
                "Then briefly scroll the page down a little so it is obvious the agent moved, "
                "and stop."
            )
    except Exception as e:
        print(f"Nova Act run failed: {e}", file=sys.stderr)
        return 3

    print("\nDone. If the browser window moved or scrolled, Nova Act is working.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
