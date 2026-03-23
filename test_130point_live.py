#!/usr/bin/env python3
"""Quick test: is 130point unblocked?"""
from backend.scrapers.oneThirtyPoint_scraper import OneThirtyPointScraper
s = OneThirtyPointScraper()
r = s.search("Nolan Ryan 1972 Topps 595")
print(f"Results: {len(r)}")
if r:
    print(f"First: {r[0]}")
else:
    print("No results -- still blocked or no data")
