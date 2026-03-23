# Session 14 Prompt - Trading Card Platform

## Conversation Summary

- **Session 13 Overview**: Built cross-validation QA, price_source tracking, $10 profit floor, tabbed card detail modal with analytics, live countdown timers, player stats API, scheduled bids infrastructure. Pipeline was running during session.

- **Cross-Validation QA Rule**: Added `scp_vs_sold_comps` rule to `qa_opportunities.py`. Flags when SCP price diverges >50% from 130point sold median (needs 3+ comps). Trims outliers. Warning at >50%, critical at >75%. 67 QA tests still passing.

- **Price Source Tracking**: Migration 015 added `price_source` column to opportunities table. Values: 'scp', 'sold_comps', 'ebay_comps'. Wired into both BIN pipeline (always 'scp') and auction pipeline (tracks three-tier fallback). Exposed in API, shown as confidence badges in frontend.

- **$10 Minimum Profit Floor**: BIN pipeline default changed from $5 to $10 in `find_opportunities.py` argparse default. Auction pipeline already had $10 default.

- **Tabbed Card Detail Modal**: Complete rewrite of `CardDetailModal.jsx`. Hero section (image, key numbers, live countdown, actions) + 4 tabs:
  - Overview: player analytics grid (30d sales, avg sale, velocity, active listings, cards, SCP rates), SCP price tiers, QA flags
  - Sell-Through: horizontal bar chart by price bucket, capital efficiency callout ("At $71 buy-in, similar cards sell in ~2.8d. That's $20.51/day return on capital.")
  - Price History: Recharts LineChart (avg/min/max daily sale price, SCP reference line), BarChart for daily volume
  - Timing: BarChart for day-of-week avg price (cheapest day green), BarChart for hourly sales volume
  - Lazy-loads tab data only when clicked

- **Player Analytics API**: Three new endpoints in `opportunities.py`:
  - `/api/players/{name}/stats`: cards, sales, velocity, avg sale, sell_through buckets
  - `/api/players/{name}/price-history`: daily avg/min/max + SCP avg reference
  - `/api/players/{name}/timing`: by_day + by_hour patterns
  - All use accent normalization (unicodedata NFD) to match Acuna/Acuna

- **Live Countdown Timers**: `CountdownTimer` component with 1-second intervals. Always shows seconds ticking. `end_time` exposed in auction API. Modal also has live countdown.

- **Confidence Badges**: Green "SCP", Blue "Sold Comps", Amber "Market Comps" on every card.

- **Scheduled Bids (Snipe Queue)**: Migration 016 created `scheduled_bids` table. `ScheduledBid` model. API routes in `scheduled_bids.py` (POST/GET/DELETE). Registered in `main.py`. Client functions added. **Frontend UI patch NOT applied** -- file permission issue.

- **Worm Improvements**: `--opportunities` flag, 429 retry logic (10min wait, 3 retries).

- **Accent Bug Fix**: Player stats returned zeros for "Ronald Acuna Jr." -- fixed with unicodedata NFD normalization.

## INCOMPLETE - Must Finish in Session 14

### 1. Schedule Bid UI in Modal (BLOCKED - file permission issue)
`CardDetailModal.jsx` is owned by root. Fix first:
```bash
sudo chown tweedledee101:tweedledee101 /home/tweedledee101/TradingCards/frontend/src/components/CardDetailModal.jsx
```
Then add to the modal:
- `createScheduledBid` import from client.js (already exported)
- `showSnipe`, `snipeForm`, `snipeStatus` state
- `handleScheduleBid` async function calling createScheduledBid()
- "Schedule Bid" button in hero section (only on live auctions)
- Inline form: max bid input, snipe seconds dropdown (3/5/10/15/30s), Confirm/Cancel
- "Bid Scheduled" green badge after scheduling
- Disclaimer about eBay OAuth requirement

### 2. "My Bids" Strip on Opportunities Page
Not started. Show scheduled bids at top of Opportunities page with:
- Live countdown timers to each auction end
- Max bid, snipe timing, cancel button
- Visual indicator when snipe window approaching

### 3. Run Worm with --opportunities Flag
130point was rate-limited (429) during Session 13. Once unblocked:
```bash
python3 worm_130point.py --limit 500 --opportunities
python3 qa_opportunities.py --recheck
```

### 4. Check Pipeline Results
Full pipeline was running during Session 13:
```bash
sudo -u postgres psql -d trading_cards -c "SELECT COUNT(*), listing_type FROM opportunities GROUP BY listing_type;"
```

## Files Modified in Session 13

- `qa_opportunities.py` -- scp_vs_sold_comps cross-validation rule
- `backend/scrapers/oneThirtyPoint_scraper.py` -- 429 retry logic
- `backend/models/__init__.py` -- price_source on Opportunity, ScheduledBid model
- `backend/models/migration_015_price_source.sql` -- NEW, applied
- `backend/models/migration_016_scheduled_bids.sql` -- NEW, applied
- `find_opportunities.py` -- min-profit $5->$10, price_source='scp'
- `find_auction_opportunities.py` -- price_source wired in
- `backend/api/routes/opportunities.py` -- price_source in responses, end_time in auction, player stats/price-history/timing endpoints, sell-through analysis, accent normalization
- `backend/api/routes/scheduled_bids.py` -- NEW
- `backend/api/main.py` -- registered scheduled_bids router
- `frontend/src/api/client.js` -- 6 new functions (player stats, price history, timing, scheduled bids CRUD)
- `frontend/src/components/CardDetailModal.jsx` -- FULL REWRITE (hero+tabs+charts). OWNED BY ROOT.
- `frontend/src/pages/Opportunities.jsx` -- CountdownTimer, ConfidenceBadge, modal integration, QA flags, Full Details button
- `STATUS.md` -- Session 13 changelog
- `test_130point_live.py` -- throwaway, can delete

## Key Technical Notes

- **File permission**: `CardDetailModal.jsx` owned by root. `sudo chown` before editing.
- **130point rate limit**: 429 on first request. Scraper retries 3x with 10min waits.
- **16 migrations applied** (001-016).
- **67 QA tests passing**.
- **Recharts** already in package.json. Used for Price History and Timing tabs.
- **Sell-through buckets** are player-level, not card-specific. 90-day window.
- **Capital efficiency**: net_profit / avg_days_to_sell = $/day return.

## User Preferences
- No emojis without asking
- No flattery, direct communication
- $10 minimum profit non-negotiable
- QA does NOT block pipeline
- Wants impressive modern UI, not graphs thrown on screen
- Wants snipe/scheduled bid feature
- Prefers running commands in his own terminal when slow
- WSL Ubuntu, watch for root vs tweedledee101 file ownership
