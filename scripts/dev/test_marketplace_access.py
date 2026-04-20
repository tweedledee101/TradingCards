#!/usr/bin/env python3
"""Test marketplace scrapers against real endpoints."""
import requests, json, re, sys

print("=" * 60)
print("MARKETPLACE SCRAPER VERIFICATION")
print("=" * 60)

# --- Mercari ---
print("\n1. Mercari mobile API...")
try:
    resp = requests.post(
        "https://api.mercari.com/v2/entities:search",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mercari/1 CFNetwork/1568.200.51 Darwin/24.1.0",
            "X-Platform": "web",
        },
        json={
            "keyword": "aaron judge 2024 topps chrome",
            "limit": 3,
            "defaultDatasets": ["DATASET_TYPE_MERCARI"],
            "searchCondition": {
                "sort": "SORT_SCORE",
                "order": "ORDER_DESC",
                "status": ["STATUS_ON_SALE"],
                "categoryId": [2536],
            },
        },
        timeout=10,
    )
    print(f"   HTTP {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"   Keys: {list(data.keys())[:5]}")
        items = data.get("items", data.get("data", data.get("searchResults", [])))
        print(f"   Items: {len(items)}")
        if items and isinstance(items, list):
            print(f"   First item keys: {list(items[0].keys())[:8]}")
            print(f"   MERCARI API: WORKING")
        else:
            print(f"   Response snippet: {json.dumps(data)[:300]}")
            print(f"   MERCARI API: NEEDS INVESTIGATION")
    elif resp.status_code == 403:
        print(f"   MERCARI API: BLOCKED (403) -- need different approach")
    else:
        print(f"   Body: {resp.text[:200]}")
        print(f"   MERCARI API: FAILED")
except requests.exceptions.ConnectionError as e:
    print(f"   DNS/Connection error: {str(e)[:100]}")
    print(f"   MERCARI API: DNS FAIL (WSL issue, not Mercari)")
except Exception as e:
    print(f"   Error: {e}")
    print(f"   MERCARI API: ERROR")

# --- Mercari web fallback ---
print("\n2. Mercari web (HTML scrape)...")
try:
    resp = requests.get(
        "https://www.mercari.com/search/?keyword=aaron+judge+topps+chrome&categoryId=2536",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        timeout=10,
    )
    print(f"   HTTP {resp.status_code}")
    if resp.status_code == 200:
        # Check for Next.js data
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text)
        if match:
            print(f"   __NEXT_DATA__ found ({len(match.group(1))} chars)")
            print(f"   MERCARI WEB: WORKING (Next.js data available)")
        elif 'challenge' in resp.text.lower() or 'cloudflare' in resp.text.lower():
            print(f"   MERCARI WEB: CLOUDFLARE CHALLENGE")
        else:
            print(f"   Page title: {re.search(r'<title>(.*?)</title>', resp.text[:2000], re.I)}")
            print(f"   MERCARI WEB: NEEDS INVESTIGATION")
    else:
        print(f"   MERCARI WEB: HTTP {resp.status_code}")
except requests.exceptions.ConnectionError:
    print(f"   MERCARI WEB: DNS FAIL")
except Exception as e:
    print(f"   MERCARI WEB: ERROR - {e}")

# --- COMC ---
print("\n3. COMC (plain HTTP)...")
try:
    resp = requests.get(
        "https://www.comc.com/Cards/Baseball",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        timeout=10,
    )
    print(f"   HTTP {resp.status_code}")
    if 'challenge' in resp.text[:500].lower() or 'cloudflare' in resp.text[:500].lower():
        print(f"   COMC: CLOUDFLARE CHALLENGE (needs Playwright)")
    elif resp.status_code == 200:
        print(f"   COMC: ACCESSIBLE (no Cloudflare)")
    else:
        print(f"   COMC: HTTP {resp.status_code}")
except requests.exceptions.ConnectionError:
    print(f"   COMC: DNS FAIL")
except Exception as e:
    print(f"   COMC: ERROR - {e}")

# --- Sportlots (bonus -- simple site, no Cloudflare) ---
print("\n4. Sportlots (bonus check)...")
try:
    resp = requests.get(
        "https://www.sportlots.com/inven/dealbin/dealbin.tpl?sport=B&cat=1&name=aaron+judge",
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    )
    print(f"   HTTP {resp.status_code}")
    if resp.status_code == 200 and '<table' in resp.text.lower():
        # Count result rows
        rows = re.findall(r'<tr[^>]*class="[^"]*data[^"]*"', resp.text, re.I)
        print(f"   Results: ~{len(rows)} rows")
        print(f"   SPORTLOTS: WORKING (plain HTML, no Cloudflare)")
    elif resp.status_code == 200:
        print(f"   SPORTLOTS: ACCESSIBLE but format unclear")
    else:
        print(f"   SPORTLOTS: HTTP {resp.status_code}")
except requests.exceptions.ConnectionError:
    print(f"   SPORTLOTS: DNS FAIL")
except Exception as e:
    print(f"   SPORTLOTS: ERROR - {e}")

print("\n" + "=" * 60)
print("SUMMARY: Which platforms can we scrape right now?")
print("=" * 60)
