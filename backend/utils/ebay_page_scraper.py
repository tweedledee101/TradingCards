"""eBay listing page scraper -- extracts price, title, type, images without Browse API.

Uses primp (TLS impersonation) to fetch eBay listing pages directly.
Zero Browse API calls consumed.

Requires Python 3.10+ and primp: pip install primp

Usage:
    from backend.utils.ebay_page_scraper import scrape_ebay_listing
    data = scrape_ebay_listing("318110495065")
    # Returns: {"item_id": "...", "title": "...", "price": 89.99, "listing_type": "buy_it_now", ...}
"""
from __future__ import annotations

import re
import json
import time
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import primp
    PRIMP_AVAILABLE = True
except ImportError:
    PRIMP_AVAILABLE = False

# Profiles that bypass eBay bot detection (tested April 2026, primp 1.2.2)
# "firefox" and "safari" work; "chrome" and "edge" get blocked
_WORKING_PROFILES = ["firefox", "safari"]
_profile_idx = 0


def _get_client() -> Any:
    global _profile_idx
    profile = _WORKING_PROFILES[_profile_idx % len(_WORKING_PROFILES)]
    _profile_idx += 1
    return primp.Client(impersonate=profile)


def scrape_ebay_listing(item_id: str, timeout: int = 15) -> Optional[Dict[str, Any]]:
    """Fetch an eBay listing page and extract structured data.

    Returns dict with: item_id, title, price, listing_type, image_urls, condition, seller.
    Returns None if blocked or fetch fails.
    """
    if not PRIMP_AVAILABLE:
        return None

    url = f"https://www.ebay.com/itm/{item_id}"
    try:
        client = _get_client()
        resp = client.get(url, headers={"Accept-Language": "en-US,en;q=0.9"})
        if resp.status_code != 200:
            return None
        html = resp.text
        if "Pardon Our Interruption" in html or len(html) < 20000:
            logger.debug(f"eBay blocked item {item_id}")
            return None
    except Exception as e:
        logger.warning(f"Failed to fetch eBay item {item_id}: {e}")
        return None

    return _parse_listing_html(item_id, html)


def scrape_ebay_listings_batch(
    item_ids: List[str],
    delay: float = 1.0,
    max_workers: int = 1,
) -> List[Dict[str, Any]]:
    """Scrape multiple listings sequentially with delay."""
    results = []
    for i, item_id in enumerate(item_ids):
        data = scrape_ebay_listing(item_id)
        if data:
            results.append(data)
        if i < len(item_ids) - 1:
            time.sleep(delay)
    return results


def _parse_listing_html(item_id: str, html: str) -> Optional[Dict[str, Any]]:
    """Extract structured data from eBay listing HTML."""
    result: Dict[str, Any] = {"item_id": item_id}

    # Title from <title> tag
    m = re.search(r"<title>([^<]+)</title>", html)
    if m:
        title = m.group(1).strip()
        # Remove " | eBay" suffix
        title = re.sub(r"\s*\|\s*eBay\s*$", "", title)
        result["title"] = title

    # JSON-LD schema price
    m = re.search(r'"priceCurrency"\s*:\s*"USD"\s*,\s*"price"\s*:\s*"([\d.]+)"', html)
    if m:
        result["price"] = float(m.group(1))

    # Listing type
    if '"AUCTION"' in html or "Place bid" in html:
        result["listing_type"] = "auction"
        # Current bid
        bid_match = re.search(r'"currentBidPrice"\s*:\s*\{\s*"value"\s*:\s*"([\d.]+)"', html)
        if bid_match:
            result["current_bid"] = float(bid_match.group(1))
    elif "Buy It Now" in html or '"FIXED_PRICE"' in html:
        result["listing_type"] = "buy_it_now"
    else:
        result["listing_type"] = "unknown"

    # Images
    images = []
    # Primary image from JSON-LD
    for img_match in re.finditer(r'"image"\s*:\s*"(https://i\.ebayimg\.com/[^"]+)"', html):
        url = img_match.group(1)
        if url not in images:
            images.append(url)
    # Gallery images
    for img_match in re.finditer(r'(https://i\.ebayimg\.com/images/g/[^"\']+s-l\d+\.[a-z]+)', html):
        url = img_match.group(1)
        if url not in images:
            images.append(url)
    # Sort so full-size (s-l1600) comes first
    images.sort(key=lambda u: (0 if "s-l1600" in u else 1, u))
    result["image_urls"] = images[:15]
    result["image_url"] = images[0] if images else None

    # Shipping
    ship_match = re.search(r'"shippingCost"\s*:\s*\{\s*"value"\s*:\s*"([\d.]+)"', html)
    if ship_match:
        result["shipping"] = float(ship_match.group(1))
    elif "Free shipping" in html or "FREE" in html:
        result["shipping"] = 0.0

    # Condition
    cond_match = re.search(r'"conditionDisplayName"\s*:\s*"([^"]+)"', html)
    if cond_match:
        result["condition"] = cond_match.group(1)

    # End time (auctions)
    end_match = re.search(r'"endTime"\s*:\s*"([^"]+)"', html)
    if end_match:
        result["end_time"] = end_match.group(1)

    # Bid count
    bids_match = re.search(r'"bidCount"\s*:\s*(\d+)', html)
    if bids_match:
        result["bid_count"] = int(bids_match.group(1))

    if "price" not in result and "title" not in result:
        return None

    return result


if __name__ == "__main__":
    import sys
    item_id = sys.argv[1] if len(sys.argv) > 1 else "318110495065"
    data = scrape_ebay_listing(item_id)
    if data:
        for k, v in data.items():
            if k == "image_urls":
                print(f"  {k}: {len(v)} images")
            else:
                print(f"  {k}: {v}")
    else:
        print("Failed to scrape")
