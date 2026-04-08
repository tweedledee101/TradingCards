"""
Dev-only stricter eBay title gates vs SCP variation (BIN opportunity path).

**Not** a substitute for CE/Nova vision — tightens **text** alignment only.
Next steps (suggested): reconcile ``scp_price`` vs ``sold_comps`` median before eBay;
queue listing photos for multimodal check when strict mode passes economics.
"""
from __future__ import annotations

import re
from typing import Optional


def dev_strict_listing_skip_reason(title: str, variation: dict) -> Optional[str]:
    """
    If the listing should be rejected under dev strict rules, return a short reason key
    (for ``pipeline_listing_skips.skip_reason``); otherwise ``None``.
    """
    title_lower = (title or '').lower()
    parallel = (variation.get('parallel') or 'Base').strip()
    if parallel.lower() != 'base':
        for w in parallel.lower().split():
            if len(w) > 1 and w not in title_lower:
                return 'dev_strict_parallel'

    set_name = (variation.get('set_name') or '').strip()
    tokens = [
        t.lower()
        for t in re.split(r'[^a-zA-Z0-9]+', set_name)
        if len(t) >= 4
    ]
    if len(tokens) >= 2:
        hits = sum(1 for t in tokens if t in title_lower)
        need = max(1, (len(tokens) + 1) // 2)
        if hits < need:
            return 'dev_strict_set_tokens'

    return None
