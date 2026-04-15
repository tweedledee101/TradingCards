"""
Web Search Listing Discovery

Replaces eBay Browse API item_summary/search with free web search via ddgs.
Returns eBay item IDs that can be hydrated via Browse API GET /item/{id}.

Architecture:
  1. ddgs text search with site:ebay.com/itm -> item IDs (free, zero API calls)
  2. Browse API GET /item/{id} per discovered item -> full listing details (targeted API calls)

Savings: a 40-player BIN scan uses ~1,200 Browse search calls today.
With web search discovery, the same scan uses ~0 search calls + N item detail calls
(where N = actual relevant listings found, typically 5-15 per variation).

Usage:
    from backend.services.web_search_discovery import WebSearchDiscovery
    discovery = WebSearchDiscovery()
    items = discovery.search_ebay_listings("bobby witt jr 2024 topps chrome", card_number="120")
    # Returns: [{"item_id": "296840183498", "title": "...", "url": "..."}, ...]
"""
import re
import time
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# ddgs requires Python 3.10+
try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    logger.warning("ddgs not available -- install with: /usr/local/bin/python3.12 -m pip install ddgs")


class WebSearchDiscovery:
    """Find eBay listings via free web search instead of Browse API."""

    EBAY_ITEM_RE = re.compile(r'ebay\.com/itm/(\d+)')
    DEFAULT_DELAY = 5.0  # seconds between queries (DDG rate limit safe)
    MAX_RESULTS_PER_QUERY = 20

    def __init__(self, delay: float = DEFAULT_DELAY):
        if not DDGS_AVAILABLE:
            raise RuntimeError("ddgs not installed. Run: /usr/local/bin/python3.12 -m pip install ddgs")
        self.delay = delay
        self._last_query_time = 0.0

    def _wait(self):
        """Enforce minimum delay between queries."""
        elapsed = time.time() - self._last_query_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_query_time = time.time()

    def _extract_item_ids(self, results: List[Dict]) -> List[Dict]:
        """Extract eBay item IDs from search results, deduped, order preserved."""
        seen = set()
        items = []
        for r in results:
            href = r.get("href", "")
            match = self.EBAY_ITEM_RE.search(href)
            if match and match.group(1) not in seen:
                seen.add(match.group(1))
                items.append({
                    "item_id": match.group(1),
                    "title": r.get("title", ""),
                    "url": href,
                    "snippet": r.get("body", ""),
                })
        return items

    def search_ebay_listings(
        self,
        player: str,
        year: Optional[int] = None,
        card_set: Optional[str] = None,
        card_number: Optional[str] = None,
        parallel: Optional[str] = None,
        max_results: int = MAX_RESULTS_PER_QUERY,
    ) -> List[Dict]:
        """
        Search for eBay listings matching a card identity.

        Uses site:ebay.com/itm prefix to restrict results to actual listing pages.
        Returns list of dicts with item_id, title, url, snippet.
        """
        # Build query: site:ebay.com/itm {player} {year} {set} #{number} {parallel}
        parts = ["site:ebay.com/itm", player]
        if year:
            parts.append(str(year))
        if card_set:
            parts.append(card_set)
        if card_number:
            parts.append(f"#{card_number}")
        if parallel and parallel.lower() not in ("base", ""):
            parts.append(parallel)

        query = " ".join(parts)
        return self._run_query(query, max_results)

    def search_ebay_auctions(
        self,
        query_text: str,
        max_results: int = MAX_RESULTS_PER_QUERY,
    ) -> List[Dict]:
        """
        Search for eBay auction listings with a free-form query.
        Appends site:ebay.com/itm automatically.
        """
        query = f"site:ebay.com/itm {query_text}"
        return self._run_query(query, max_results)

    def search_cross_platform(
        self,
        player: str,
        year: Optional[int] = None,
        card_set: Optional[str] = None,
        platforms: Optional[List[str]] = None,
        max_results: int = 10,
    ) -> Dict[str, List[Dict]]:
        """
        Search multiple platforms for the same card.
        Returns dict keyed by platform name.
        """
        if platforms is None:
            platforms = ["ebay", "mercari", "comc"]

        site_map = {
            "ebay": "ebay.com/itm",
            "mercari": "mercari.com",
            "comc": "comc.com",
        }

        parts = [player]
        if year:
            parts.append(str(year))
        if card_set:
            parts.append(card_set)
        card_text = " ".join(parts)

        results = {}
        for platform in platforms:
            site = site_map.get(platform)
            if not site:
                continue
            query = f"site:{site} {card_text}"
            try:
                raw = self._run_query(query, max_results)
                results[platform] = raw
            except Exception as e:
                logger.warning(f"Web search failed for {platform}: {e}")
                results[platform] = []

        return results

    def _run_query(self, query: str, max_results: int) -> List[Dict]:
        """Execute a single ddgs query with rate limiting."""
        self._wait()
        logger.debug(f"Web search: {query}")
        try:
            with DDGS() as ddgs:
                raw = list(ddgs.text(query, max_results=max_results))
            items = self._extract_item_ids(raw)
            logger.info(f"Web search: {len(raw)} results, {len(items)} eBay items -- {query[:60]}")
            return items
        except Exception as e:
            if "No results found" in str(e):
                logger.debug(f"Web search: 0 results -- {query[:60]}")
                return []
            raise


def _demo():
    """Quick demo of the web search discovery."""
    discovery = WebSearchDiscovery(delay=6.0)

    print("Web Search Discovery Demo")
    print("=" * 60)

    # BIN-style: specific card identity
    print("\n1. BIN-style search (specific card):")
    items = discovery.search_ebay_listings(
        player="mike trout",
        year=2011,
        card_set="topps update",
        card_number="US175",
    )
    print(f"   Found {len(items)} listings")
    for item in items[:5]:
        print(f"   {item['item_id']} -- {item['title'][:60]}")

    # Auction-style: broader value query
    print("\n2. Auction-style search (value query):")
    items = discovery.search_ebay_auctions("2024 topps chrome auto numbered /25 baseball")
    print(f"   Found {len(items)} listings")
    for item in items[:5]:
        print(f"   {item['item_id']} -- {item['title'][:60]}")

    # Cross-platform
    print("\n3. Cross-platform search:")
    results = discovery.search_cross_platform(
        player="bobby witt jr",
        year=2024,
        card_set="topps chrome",
    )
    for platform, items in results.items():
        print(f"   {platform}: {len(items)} results")
        for item in items[:2]:
            print(f"     {item.get('item_id', '?')} -- {item['title'][:55]}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _demo()
