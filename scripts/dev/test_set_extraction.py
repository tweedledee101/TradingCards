"""Test set + parallel extraction against real eBay titles that caused false positives."""
from backend.scrapers.ebay_scraper import EbayScraper

scraper = EbayScraper.__new__(EbayScraper)  # skip __init__ (no API needed)

cases = [
    # (title, expected_set, expected_parallel)
    # Insert refractors that were misclassified as plain "Topps Chrome / Refractor"
    ("1996 Topps Chrome MG9 Cal Ripken Jr Orioles Master Of The Game Refractor HOF", "Topps Chrome Master Of The Game", "Refractor"),
    ("1998 NOLAN RYAN TOPPS CHROME SILVER REFRACTOR 1986 RETRO VERSION INSERT SP HOF", "Topps Chrome 1986 Retro", "Silver Refractor"),
    ("1998 Topps Chrome Ken Griffey Jr Milestone Refractor - PSA 10", "Topps Chrome Milestone", "Refractor"),
    ("1999 Topps Chrome All Etch Refractor Ken Griffey Jr PSA 9", "Topps Chrome All Etch", "Refractor"),
    ("1999 Topps Chrome Lord Of The Diamonds Ken Griffey Jr Refractor PSA 9", "Topps Chrome Lord Of The Diamonds", "Refractor"),
    ("1999 Topps Chrome Record Numbers Refractor Ken Griffey Jr PSA 10", "Topps Chrome Record Numbers", "Refractor"),
    ("2000 Topps Chrome All-Topps Ken Griffey Jr REFRACTOR PSA 8 HOF Mariners", "Topps Chrome All-Topps", "Refractor"),
    ("2000 Topps Chrome Power Players Ken Griffey Jr Refractor PSA 9", "Topps Chrome Power Players", "Refractor"),
    ("2005 Topps Chrome Opening Day Refractor Derek Jeter ODC9 Yankees-b", "Topps Chrome Opening Day", "Refractor"),
    ("2010 Topps Chrome Ichiro Suzuki National Chicle Refractor /499 Mariners", "Topps Chrome National Chicle", "Refractor"),
    ("2019 Topps Chrome 1984 Topps Juan Soto Refractor. Mets", "Topps Chrome 1984 Topps", "Refractor"),
    ("2020 Topps Chrome Decade's Next Refractor Shohei Ohtani Los Angeles Angels", "Topps Chrome Decade'S Next", "Refractor"),
    # Plain Topps Chrome refractors (should still work)
    ("2013 Topps Chrome Derek Jeter Refractor #10 Yankees", "Topps Chrome", "Refractor"),
    ("2012 Topps Chrome Refractor 84 DEREK JETER Yankees Parallel", "Topps Chrome", "Refractor"),
    # Wave refractors (parallel, not insert)
    ("2024 Topps Chrome Colton Cowser RayWave Refractor Rookie Orioles RC", "Topps Chrome", "Raywave Refractor"),
    ("2025 Topps Chrome Corbin Carroll Green Wave Refractor /99 PSA 8", "Topps Chrome", "Green Wave Refractor"),
    ("2016 Topps Chrome TREA TURNER Blue Wave Refractor Rookie /75 PSA 10", "Topps Chrome", "Blue Wave Refractor"),
]

print("=" * 80)
print("SET + PARALLEL EXTRACTION TEST")
print("=" * 80)

all_pass = True
for title, exp_set, exp_parallel in cases:
    got_set = scraper._extract_card_set(title)
    got_par = scraper._extract_parallel(title)
    set_ok = got_set.lower() == exp_set.lower()
    par_ok = got_par.lower() == exp_parallel.lower()
    status = "PASS" if (set_ok and par_ok) else "FAIL"
    if status == "FAIL":
        all_pass = False
    short_title = title[:65]
    print(f"\n  {status}: {short_title}...")
    if not set_ok:
        print(f"    SET: got '{got_set}' expected '{exp_set}'")
    if not par_ok:
        print(f"    PAR: got '{got_par}' expected '{exp_parallel}'")
    if set_ok and par_ok:
        print(f"    SET: {got_set} | PAR: {got_par}")

print("\n" + "=" * 80)
print("ALL PASSED" if all_pass else "SOME FAILED")
