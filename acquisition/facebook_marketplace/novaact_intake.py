"""NovaAct-driven intake scaffold for Facebook Marketplace.

This module intentionally avoids embedding secrets. Configure with environment variables:
- NOVAACT_API_KEY (required)
- NOVAACT_BASE_URL (optional)
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class NovaActConfig:
    api_key: str
    base_url: str | None = None


class NovaActClient:
    """Placeholder client for NovaAct interactions.

    Replace the methods below with actual NovaAct SDK or HTTP calls.
    """

    def __init__(self, config: NovaActConfig) -> None:
        self._config = config

    def start_session(self) -> None:
        """Start a NovaAct session and authenticate.

        TODO: Implement using NovaAct SDK or API.
        """
        raise NotImplementedError("NovaAct session start not yet implemented")

    def login_facebook(self) -> None:
        """Log into Facebook Marketplace.

        TODO: Implement via NovaAct browser automation.
        """
        raise NotImplementedError("Facebook login not yet implemented")

    def search_marketplace(self, query: str) -> None:
        """Search Marketplace for a query string.

        TODO: Implement search and return normalized listing data.
        """
        raise NotImplementedError("Marketplace search not yet implemented")


def load_config() -> NovaActConfig:
    api_key = os.getenv("NOVAACT_API_KEY")
    if not api_key:
        raise RuntimeError("NOVAACT_API_KEY is required but not set")
    return NovaActConfig(api_key=api_key, base_url=os.getenv("NOVAACT_BASE_URL"))


def main() -> None:
    config = load_config()
    client = NovaActClient(config)
    client.start_session()
    client.login_facebook()
    client.search_marketplace("trading cards")


if __name__ == "__main__":
    main()
