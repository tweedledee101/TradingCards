#!/usr/bin/env python3
"""
Single Buy Browse ``item_summary/search`` call using your app token.

Use this to see **right now** whether Browse returns **200** or **429** (throttle).
It does **not** print official “calls remaining today” — eBay exposes daily totals
in the **developer portal** (see below), not via client-credentials + one REST line.

Usage (from repo root, with ``backend/.env`` or env vars set):

  python3 scripts/dev/ebay_browse_ping.py

Daily / quota context:
  - https://developer.ebay.com/develop/get-started/api-call-limits
  - Sign in → https://developer.ebay.com/my/keys → your application → check for
    **Analytics** / **Reports** (UI name varies by account).
  - Per-user rate analytics (``getUserRateLimits``) needs a **user** OAuth token,
    not the client-credentials token this repo uses for pipelines.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import requests  # noqa: E402

from backend.scrapers.ebay_scraper import EbayScraper  # noqa: E402
from backend.utils.token_manager import token_manager  # noqa: E402


def main() -> int:
    scraper = EbayScraper()
    token = token_manager.get_token()
    headers = dict(scraper.headers)
    headers['Authorization'] = f'Bearer {token}'
    url = f'{scraper.base_url}/item_summary/search'
    params = {'q': 'baseball card', 'limit': 1, 'category_ids': '261328'}
    r = requests.get(url, headers=headers, params=params, timeout=30)
    print(f'HTTP {r.status_code}')
    ra = r.headers.get('Retry-After')
    if ra is not None:
        print(f'Retry-After: {ra}')
    snippet = (r.text or '')[:600].replace('\n', ' ')
    if snippet:
        print(snippet)
    return 0 if r.status_code == 200 else 1


if __name__ == '__main__':
    raise SystemExit(main())
