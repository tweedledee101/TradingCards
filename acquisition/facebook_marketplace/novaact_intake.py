"""NovaAct-driven intake scaffold for Facebook Marketplace.

This script supports a dry-run mode that validates configuration and prints the
steps it would execute. Real NovaAct SDK wiring can replace the placeholders
without changing the command-line interface.

Configure with environment variables:
- NOVAACT_API_KEY (required)
- NOVAACT_BASE_URL (optional)
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import logging
import os
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class NovaActConfig:
    api_key: str
    base_url: str | None = None


class NovaActClient:
    """Client wrapper for NovaAct interactions.

    This keeps a minimal surface area so it can be swapped to the real SDK
    once the SDK wiring is ready.
    """

    def __init__(self, config: NovaActConfig, *, dry_run: bool) -> None:
        self._config = config
        self._dry_run = dry_run
        self._logger = logging.getLogger(__name__)

    def start_session(self) -> None:
        """Start a NovaAct session and authenticate.

        TODO: Implement using NovaAct SDK or API when ready.
        """
        if self._dry_run:
            self._logger.info("Dry run: would start NovaAct session.")
            return
        self._logger.info("NovaAct session start not yet implemented.")

    def login_facebook(self) -> None:
        """Log into Facebook Marketplace.

        TODO: Implement via NovaAct browser automation when ready.
        """
        if self._dry_run:
            self._logger.info("Dry run: would log into Facebook.")
            return
        self._logger.info("Facebook login not yet implemented.")

    def search_marketplace(self, query: str) -> None:
        """Search Marketplace for a query string.

        TODO: Implement search and return normalized listing data when ready.
        """
        if self._dry_run:
            self._logger.info("Dry run: would search Marketplace for %r.", query)
            return
        self._logger.info("Marketplace search not yet implemented for %r.", query)


def ensure_novaact_available() -> None:
    if importlib.util.find_spec("nova_act") is None:
        raise RuntimeError(
            "NovaAct SDK is not installed. Install it with `pip install nova-act`."
        )
    importlib.import_module("nova_act")


def load_config() -> NovaActConfig:
    api_key = os.getenv("NOVAACT_API_KEY")
    if not api_key:
        raise RuntimeError("NOVAACT_API_KEY is required but not set")
    return NovaActConfig(api_key=api_key, base_url=os.getenv("NOVAACT_BASE_URL"))


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the NovaAct Facebook Marketplace intake workflow."
    )
    parser.add_argument(
        "--query",
        default="trading cards",
        help="Marketplace search query to run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and log intended actions without calling NovaAct.",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    config = load_config()
    if not args.dry_run:
        ensure_novaact_available()
    client = NovaActClient(config, dry_run=args.dry_run)
    client.start_session()
    client.login_facebook()
    client.search_marketplace(args.query)


if __name__ == "__main__":
    main()
