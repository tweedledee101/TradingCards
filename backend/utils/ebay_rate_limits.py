"""
eBay API quota visibility for pipelines using the **client-credentials** token.

1) **Response headers** on many REST calls (when eBay sends them):
   ``X-EBAY-C-RATELIMIT-LIMIT``, ``X-EBAY-C-RATELIMIT-REMAINING``, ``X-EBAY-C-RATELIMIT-RESET``.

2) **Analytics API** ``GET /developer/analytics/v1_beta/rate_limit/`` (official app-level
   limits for Buy Browse and other APIs). Uses the same scope as
   ``https://api.ebay.com/oauth/api_scope``. Counts against the Analytics API’s own
   small quota — skip with ``EBAY_SKIP_ANALYTICS_QUOTA=1`` if needed.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import requests


def parse_ratelimit_headers(response: requests.Response) -> Optional[Dict[str, str]]:
    lim = rem = rst = None
    for k, v in response.headers.items():
        lk = k.lower()
        if lk == 'x-ebay-c-ratelimit-limit':
            lim = v
        elif lk == 'x-ebay-c-ratelimit-remaining':
            rem = v
        elif lk == 'x-ebay-c-ratelimit-reset':
            rst = v
    if lim is None and rem is None and rst is None:
        return None
    out: Dict[str, str] = {}
    if lim is not None:
        out['limit'] = lim
    if rem is not None:
        out['remaining'] = rem
    if rst is not None:
        out['reset'] = rst
    out['source'] = 'response_headers'
    return out


def _pick_browse_rate_entry(data: dict) -> Optional[Dict[str, Any]]:
    """Pick the best Browse/Buy resource row that includes numeric limits."""
    blocks = data.get('rateLimits') or []
    candidates: List[Tuple[int, str, Dict[str, Any]]] = []
    for block in blocks:
        ctx = (block.get('apiContext') or '')
        name = (block.get('apiName') or '')
        for res in block.get('resources') or []:
            rname = str(res.get('name') or '')
            for rate in res.get('rates') or []:
                if rate.get('limit') is None and rate.get('remaining') is None:
                    continue
                key = rname.lower()
                score = 0
                if 'item_summary' in key or 'item' in key:
                    score += 4
                if 'search' in key:
                    score += 4
                if 'browse' in key:
                    score += 1
                if ctx.lower() == 'buy' or 'buy' in name.lower():
                    score += 2
                candidates.append((score, rname, rate))
    if not candidates:
        return None
    candidates.sort(key=lambda x: -x[0])
    _sc, rname, rate = candidates[0]
    return {
        'resource': rname,
        'limit': rate.get('limit'),
        'remaining': rate.get('remaining'),
        'count': rate.get('count'),
        'reset': rate.get('reset'),
        'timeWindow': rate.get('timeWindow'),
        'source': 'developer.analytics.v1_beta.rate_limit',
    }


def fetch_buy_browse_app_quota(scraper: Any) -> Optional[Dict[str, Any]]:
    """
    Application-level Buy/Browse limits from Analytics ``getRateLimits``.

    Disable to save Analytics calls: ``EBAY_SKIP_ANALYTICS_QUOTA=1``.
    """
    if os.environ.get('EBAY_SKIP_ANALYTICS_QUOTA', '').lower() in ('1', 'true', 'yes'):
        return None
    token = scraper.token_manager.get_token()
    headers: Dict[str, str] = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    for hk in ('X-EBAY-C-MARKETPLACE-ID', 'X-EBAY-C-ENDUSERCTX'):
        if hk in scraper.headers:
            headers[hk] = scraper.headers[hk]
    url = 'https://api.ebay.com/developer/analytics/v1_beta/rate_limit/'
    try:
        r = requests.get(
            url,
            headers=headers,
            params={'api_name': 'browse', 'api_context': 'buy'},
            timeout=15,
        )
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    try:
        data = r.json()
    except ValueError:
        return None
    return _pick_browse_rate_entry(data)
