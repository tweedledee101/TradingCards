"""
Free-text card identifiers on eBay (title / shortDescription / HTML description).

Aspects remain authoritative when present; these patterns supplement missing Card Number.
"""
import re
from typing import List

CARD_HASH_RE = re.compile(r'#\s*([A-Za-z0-9][A-Za-z0-9-]*)')

_VERBAL_CARD_NUMBER_RES = [
    re.compile(r'\bcard\s+no\.?\s*#?\s*([A-Za-z0-9][A-Za-z0-9-]*)\b', re.I),
    re.compile(r'\bcn\s*[:#.]?\s*([A-Za-z0-9][A-Za-z0-9-]*)\b', re.I),
    re.compile(r'\bcatalog(?:ue)?\s*#?\s*([A-Za-z0-9][A-Za-z0-9-]*)\b', re.I),
    re.compile(r'\binsert\s*#?\s*([A-Za-z0-9][A-Za-z0-9-]*)\b', re.I),
    re.compile(r'\bref\s*[:#.]\s*([A-Za-z0-9][A-Za-z0-9-]*)\b', re.I),
]


def card_number_tokens_from_free_text(text: str) -> List[str]:
    """
    Ordered unique tokens: all #… matches in text order, then verbal patterns.
    """
    if not text:
        return []
    seen = set()
    out = []

    def add_raw(s):
        if not s:
            return
        t = str(s).strip()
        if not t:
            return
        k = t.lower()
        if k not in seen:
            seen.add(k)
            out.append(t)

    for m in CARD_HASH_RE.finditer(text):
        add_raw(m.group(1))
    for rx in _VERBAL_CARD_NUMBER_RES:
        for m in rx.finditer(text):
            add_raw(m.group(1))
    return out
