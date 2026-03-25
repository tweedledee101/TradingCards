from backend.scrapers.ebay_scraper import EbayScraper
s = EbayScraper()
tests = [
    '2024 Leaf LEGEND AARON JUDGE L-11 NEW YORK YANKEES',
    '2024 Leaf LEGEND EXCLUSIVE AARON JUDGE LE-15 NEW YORK YANKEES',
    '2024 Leaf OG AARON JUDGE OG-08 NEW YORK YANKEES',
    '2024 Leaf PRIZED LEGEND AARON JUDGE #28 NEW YORK YANKEES',
    '2024 Leaf EXCLUSIVE ROOKIE PAUL SKENES #EX-01',
    '2024 Leaf EXCLUSIVE LEGENDS DE LA CRUZ / HENDERSON #ELE-38',
    '2024 Leaf ROOKIE PAUL SKENES #R-12',
    '2024 Leaf Collective Promo PAUL SKENES Base',
    '2023 Leaf Rookie Achievement Paul Skenes RC #RA-39',
    '2024 Leaf FLAG ROOKIE ROMAN ANTHONY FL-11',
    '2024 Leaf SILVER AARON JUDGE SL-12',
    '1990 Leaf Nolan Ryan #21',
    '2025 Topps Chrome Refractor Aaron Judge',
    '2026 Topps Series 1 #304 Corbin Carroll Green Leaf Foil',
]
for t in tests:
    s_set = s._extract_card_set(t)
    print(f'{s_set:30s} <- {t[:65]}')
