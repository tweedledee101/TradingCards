"""
Noise Listing Filter

Detects "You Pick" / "Complete Your Set" / lot listings that pollute
active_listings and create fake arbitrage opportunities.

Used at import time (collect_active_listings) and query time (opportunity_analyzer).
"""

import re

# Phrases that indicate a multi-card / pick-your-card listing, not a single card for sale
_NOISE_PATTERNS = [
    r'you pick',
    r'u-pick',
    r'u pick',
    r'pick your',
    r'choose your',
    r'complete your set',
    r'finish your set',
    r'build your set',
    r'card minimum',
    r'buy more.{0,10}save',
    r'\blot of \d+',
]

_NOISE_RE = re.compile('|'.join(_NOISE_PATTERNS), re.IGNORECASE)


def is_noise_listing(title: str) -> bool:
    """Return True if the listing title matches a known noise pattern."""
    if not title:
        return False
    return bool(_NOISE_RE.search(title))
