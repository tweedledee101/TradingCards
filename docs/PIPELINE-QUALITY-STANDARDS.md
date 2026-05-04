# Auction Pipeline V2 - Quality Standards

## Hard Requirements (non-negotiable)

### Accuracy: 95% minimum
Every opportunity shown to the user must be a correctly matched card.
- Correct player
- Correct year
- Correct set/product line
- Correct parallel/variant
- Correct SCP price for that exact product

**Measurement**: After every pipeline run, sample 20 random opportunities.
Manually verify eBay listing vs SCP match. Count correct / total.
If accuracy < 95%, the run is a failure. Do not ship results to production.

### Volume: 10+ biddable auctions daily
The pipeline must surface at least 10 actionable auction opportunities per day
that the user can bid on. "Actionable" means:
- Auction is still active (not ended)
- Profit >= $10 after fees
- Card has proven sales volume (daily/weekly/monthly)

**Measurement**: Count opportunities with end_time > now and profit >= $10.

## Quality Gates

### Gate 1: Card Identity (5-field match)
Every match must verify ALL five identity fields:
1. Player name (last name in eBay title)
2. Year (in eBay title or getItem)
3. Set/product line (set keywords must align between eBay and SCP)
4. Card number (must match)
5. Parallel/variant (exact match from getItem or Nova)

### Gate 2: Product Type Validation
Premium products (Relic, Autograph, Sapphire, etc.) in SCP must also
appear in the eBay listing. A base card must never match a relic price.

### Gate 3: Lot Detection
Multi-card listings must be filtered before matching. Patterns:
"lot", "N cards", "card lot", "Nx", "pick your"

### Gate 4: Recovery
When a match fails validation, attempt recovery using eBay's real identity
(from getItem structured data) to find the correct SCP entry. Recovery
matches must also pass all validation gates.

## Post-Run Audit Script

After every run, execute:
```bash
/usr/local/bin/python3.12 _audit_stored_opps.py
```

Review the top 20 results. For each:
- Open the eBay URL
- Open the SCP URL
- Confirm they are the same card
- Record correct/incorrect

If < 19/20 correct (95%), the run failed.

## History

| Date | Run | Accuracy | Opportunities | Status |
|------|-----|----------|---------------|--------|
| 2026-05-02 | V2 first run | ~10% | 273 (mostly wrong) | FAILED |
| 2026-05-02 | After cleanup | ~50% est | 218 | FAILED |
| 2026-05-03 | With validation + recovery | TBD | TBD | PENDING |
