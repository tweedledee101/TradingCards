# Session 15 Prompt - Trading Card Platform

## Session 14 Summary

- **Snipe UI Complete**: CardDetailModal now has "Snipe $XX.XX" button (calculated: SCP * 0.87 - $10 profit - shipping), expandable panel with big profit headline (updates live), math formula, bid input pre-filled with recommended price, timing dropdown, Queue button. Separate "Schedule Bid" button for manual entry. BIN cards show "Buy $XX.XX" green button. Timer/bids separated to context row, eBay/SCP demoted to text links.

- **My Bids Strip**: Opportunities page fetches scheduled bids on load, renders horizontal scrollable strip above Live Auctions. Each card: thumbnail, player info, live countdown, max bid, snipe timing, urgency indicators (amber < 1hr, red pulse near snipe window), Cancel button, View link. Hidden when empty.

- **RDS Primary Database**: `.env` DATABASE_URL switched from localhost to `cardpulse-db.ckvp9bhavaww.us-east-1.rds.amazonaws.com`. All pipeline runs now write to RDS.

- **Migration Runner** (`migrate.py`): `schema_migrations` table tracks applied migrations. `--both` applies to local + RDS. `--status` shows what's pending. Handles already-existing objects gracefully. 23 migrations tracked on both databases, both up to date. 19 tables.

- **Variable Ordering Bug Fixed**: `recSnipe` was using `scpPrice`/`shipping` before declaration. Moved calculation below variable declarations.

- **Design Iteration**: Went through 3 rounds of snipe UI refinement. Started with busy button row + 4-column math grid. Ended with clean layout: one full-width CTA, profit as headline of snipe panel, math as supporting text, controls on one row.

## TODO for Session 15

### 1. Full Pipeline Run Against RDS
Pipeline hasn't run against RDS yet. Need to verify end-to-end:
```bash
python3 find_opportunities.py --max-budget 200 --min-profit 10 --min-roi 20 --top-players 40
```
Check results:
```bash
PGPASSWORD='FamilyMan33*1' psql -h cardpulse-db.ckvp9bhavaww.us-east-1.rds.amazonaws.com -U cardpulse -d trading_cards -c "SELECT COUNT(*), listing_type FROM opportunities GROUP BY listing_type;"
```

### 2. Push to GitHub
Code hasn't been pushed since Session 13. Need to commit and push:
- Snipe UI (CardDetailModal.jsx, Opportunities.jsx)
- My Bids strip
- Migration runner (migrate.py)
- .env change (DO NOT commit .env -- it has credentials)
- Updated docs (STATUS.md, PIPELINE-OPS.md, memory bank files)

### 3. GitHub Actions Pipeline Update
Existing workflows (`.github/workflows/pipeline.yml`, `auction-pipeline.yml`) may need updating:
- Verify they use the RDS DATABASE_URL from GitHub secrets
- Verify migration runner works in CI environment
- Test a workflow_dispatch run

## Files Modified in Session 14

- `frontend/src/components/CardDetailModal.jsx` -- Snipe UI (calculated price, snipe panel with profit headline, Schedule Bid manual panel, Buy button for BIN, clean layout)
- `frontend/src/pages/Opportunities.jsx` -- My Bids strip (getScheduledBids, cancelScheduledBid, MyBidCard component)
- `frontend/src/api/client.js` -- already had scheduled bid functions from Session 13
- `backend/.env` -- DATABASE_URL switched to RDS
- `migrate.py` -- NEW: migration runner with schema_migrations tracking
- `STATUS.md` -- Session 14 changelog
- `PIPELINE-OPS.md` -- migrations 015-016, migration runner docs
- `.amazonq/rules/memory-bank/structure.md` -- schema_migrations, migration runner section
- `.amazonq/rules/memory-bank/product.md` -- migration count, dual-database setup
- `.amazonq/rules/memory-bank/tech.md` -- migrate.py commands, $10 min profit
- `.amazonq/prompts/session-15.md` -- this file

## Key Technical Notes

- **RDS connection**: `PGPASSWORD='FamilyMan33*1' psql -h cardpulse-db.ckvp9bhavaww.us-east-1.rds.amazonaws.com -U cardpulse -d trading_cards`
- **Local connection**: `sudo -u postgres psql -d trading_cards`
- **23 migrations tracked** on both databases via `schema_migrations` table
- **19 tables** in both databases (identical structure)
- **67 QA tests** should still pass
- **Vite build passes** -- verified after all CardDetailModal changes
- **min-profit default is $10** on both BIN and auction pipelines
- **CardDetailModal.jsx** is ~550 lines. Do NOT attempt full file rewrites -- use targeted fsReplace patches only.

## User Preferences
- No emojis without asking
- No flattery, direct communication
- $10 minimum profit non-negotiable
- QA does NOT block pipeline
- Wants clean, decisive UI -- form serves function
- Prefers running commands in his own terminal when slow
- WSL Ubuntu, watch for root vs tweedledee101 file ownership
- When tools get stuck, give him the commands to run manually
