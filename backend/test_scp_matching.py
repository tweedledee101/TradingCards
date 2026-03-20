"""Test SCP matching logic against the Bryce Harper false positive case.

Tests _sets_match and match_scp_to_card without needing Selenium/Firefox.
"""
from backend.collect_market_rates import _sets_match, _normalize_parallel, _normalize_set

print("=" * 60)
print("TEST 1: _sets_match")
print("=" * 60)

cases = [
    ("Bowman Chrome", "Bowman Chrome", True),
    ("Bowman Chrome", "Bowman Chrome Prospects", False),
    ("Bowman Chrome Prospects", "Bowman Chrome", False),
    ("Bowman Chrome Prospects", "Bowman Chrome Prospects", True),
    ("Topps Chrome", "Topps Chrome", True),
    ("Topps Chrome", "Topps Chrome Update", False),
    ("Heritage", "Topps Heritage", True),
    ("Stadium Club", "Topps Stadium Club", True),
    ("Stadium Club", "Topps Stadium Club (Baseball)", True),
    ("Bowman", "Bowman Chrome", False),
    ("Bowman Chrome", "Bowman", False),
    # Empty/None sets should NOT match (don't trust unverifiable data)
    ("", "Bowman Chrome", False),
    ("Bowman Chrome", "", False),
    (None, "Bowman Chrome", False),
]

all_pass = True
for card_set, scp_set, expected in cases:
    result = _sets_match(card_set, scp_set)
    status = "PASS" if result == expected else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  {status}: '{card_set}' vs '{scp_set}' -> {result} (expected {expected})")

print()
print("=" * 60)
print("TEST 2: _normalize_parallel")
print("=" * 60)

parallel_cases = [
    ("Refractor", "refractor", True),
    ("Blue Foil Pattern II", "Blue Pattern II", True),
    ("Lime Green", "Green", False),
    ("Light Blue Sparkle", "Light Blue Sparkle Chrome", True),
    ("Base", "Base", True),
    ("Gold", "Gold Foil", True),
]

for ebay, scp, expected in parallel_cases:
    e_norm = _normalize_parallel(ebay)
    s_norm = _normalize_parallel(scp)
    result = e_norm == s_norm
    status = "PASS" if result == expected else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  {status}: '{ebay}' ({e_norm}) vs '{scp}' ({s_norm}) -> {result} (expected {expected})")

print()
if all_pass:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
