"""Quick test to see SCP search result structure, especially URLs"""
import json
import logging
from backend.scrapers.sportscardspro_scraper import SportsCardsProScraper

logging.basicConfig(level=logging.INFO)

scraper = SportsCardsProScraper(headless=True)
try:
    results = scraper.search("Ken Griffey Jr 1999 Bowman Chrome I20")
    print(f"\n=== Found {len(results)} results ===\n")
    for r in results[:5]:
        print(json.dumps({
            "raw_title": r.get("raw_title"),
            "url": r.get("url"),
            "set_text": r.get("set_text"),
            "card_number": r.get("card_number"),
            "parallel": r.get("parallel"),
            "ungraded": r.get("ungraded"),
            "grade_9": r.get("grade_9"),
            "psa_10": r.get("psa_10"),
        }, indent=2))
        print("---")
finally:
    scraper.close()
