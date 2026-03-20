"""Test what SCP returns for Bryce Harper 2012 Bowman Chrome"""
import logging
logging.basicConfig(level=logging.INFO)

from backend.scrapers.sportscardspro_scraper import SportsCardsProScraper

s = SportsCardsProScraper(headless=True)
try:
    results = s.search("Bryce Harper 2012 Bowman Chrome")
    print(f"\n{'='*80}")
    print(f"Got {len(results)} results")
    print(f"{'='*80}")
    for r in results[:20]:
        p = r.get("parallel", "Base")
        n = r.get("card_number", "?")
        u = r.get("ungraded")
        g9 = r.get("grade_9")
        p10 = r.get("psa_10")
        st = r.get("set_text", "")
        title = r.get("raw_title", "")[:80]
        print(f"  [{p}] #{n}")
        print(f"    U=${u}  G9=${g9}  P10=${p10}")
        print(f"    Set: {st}")
        print(f"    Title: {title}")
        print()
finally:
    s.close()
