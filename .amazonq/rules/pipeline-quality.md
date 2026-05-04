# Pipeline Quality Standards

## Every auction pipeline run MUST meet these targets:

### Accuracy: 95% minimum
- Every opportunity must be a correctly matched card (player, year, set, card number, parallel)
- After every run, audit 20 random opportunities against eBay + SCP URLs
- If < 19/20 correct, the run FAILED. Do not ship to production.

### Volume: 10+ biddable auctions daily
- At least 10 actionable opportunities per day (active auctions, $10+ profit, proven volume)

### Card Identity: 5-field match required
1. Player name
2. Year
3. Set/product line
4. Card number
5. Parallel/variant

All 5 must be verified before storing an opportunity. No exceptions.

### Post-Run Audit
Run `_audit_stored_opps.py` after every pipeline run. Review results manually.
Record accuracy in `docs/PIPELINE-QUALITY-STANDARDS.md`.

See `docs/PIPELINE-QUALITY-STANDARDS.md` for full details and history.
