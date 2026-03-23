# Trading Card Platform - Current Status
**Last Updated:** 2026-03-23 (Session 14)

## SYSTEM STATUS: TWO PIPELINES LIVE, SNIPE UI COMPLETE, RDS PRIMARY

The SCP-to-eBay opportunity pipeline (`find_opportunities.py`) is running full 40-player scans. Latest scan: 133 opportunities found. Pipeline now includes BIN and auction listings, three-tier pricing (SCP -> 130point sold comps -> eBay BIN comps), volume filtering, price floor, factory set detection, and reprint filtering. Background data worm crawls 130point.com for free eBay sold data. Opportunities stored in database and served via API to the frontend.

Session 14 added: Snipe UI with calculated recommended price (SCP - fees - $10 profit = max bid), Schedule Bid manual entry, My Bids strip on Opportunities page, RDS as primary database, migration runner (`migrate.py`) with schema_migrations tracking for local/RDS sync.

### Quick Start

```bash
cd /home/tweedledee101/TradingCards

# Run opportunity finder (SCP catalog -> eBay active listings)
python3 find_opportunities.py --max-budget 200 --min-profit 10 --min-roi 20 --top-players 40

# Or specify players
python3 find_opportunities.py --max-budget 200 --min-profit 10 --players "Bobby Witt Jr,Mike Trout"

# Start services
nohup /usr/bin/python3 -m backend.api.run > /tmp/api.log 2>&1 &
cd frontend && nohup npm run dev > /tmp/frontend.log 2>&1 &

# Database migrations (keeps local + RDS in sync)
python3 migrate.py --both       # apply pending to both
python3 migrate.py --status --both  # check what's applied
```

---

## WHAT WORKS

### SCP-to-eBay Opportunity Pipeline
File: `find_opportunities.py`

Flow:
1. SCP player search returns full catalog (100 variations per player, 1 Selenium call)
2. Filter to variations within budget ($20-$1000 default)
3. Volume filter: skip cards with "rare", "1 sale per year", "2 sales per year" (dead money)
4. Build precise eBay search queries from SCP data (set name, card number, parallel, print run)
5. Search eBay active listings for each variation (BIN and auctions)
6. Strict title validation: player name + year + card number + variation keyword required
7. Junk filter: excludes "You Pick", "Complete Your Set", "Digital", "Bunt", lots, repacks
8. Factory set filter: excludes "Complete Set", "Montgomery Club", "Walmart Exclusive", "Target Exclusive" (unless SCP card itself is a factory set variant)
9. Reprint filter: excludes "Replica", "Project 2020", "Shoebox Treasures", "Sticker", "ACEO"
10. Wrong set detection: rejects listings containing known set names not in the SCP variation
11. BIN price floor: listings below 30% of SCP are hard-rejected (different product)
12. BIN suspicious flagging: listings between 30-50% of SCP pass but flagged for review
13. Auctions: included with no price floor or flagging (low current bids are normal)
14. Profit calculation: SCP price - buy price - 13% eBay fees
15. Results stored in `opportunities` table with listing_type (buy_it_now or auction)
16. Results served via API with listing_type filter support

### Pipeline Filters (in order)
```
SCP Catalog (100 variations/player)
  -> SCP price range ($20-$1000)
  -> Volume filter (reject "rare", "1 sale/year", "2 sales/year")
  -> eBay search (BIN + Auctions)
  -> Title validation (player + year + card# + parallel)
  -> Junk filter (you pick, mystery, repack, etc.)
  -> Factory set filter (complete set, montgomery, walmart/target exclusive)
  -> Reprint filter (replica, project 2020, shoebox treasures)
  -> Wrong set detection (gold label, gallery, etc. in wrong context)
  -> BIN price floor (< 30% of SCP = different product)
  -> Profit/ROI threshold
  -> BIN suspicious flagging (30-50% of SCP)
  -> Store in DB with listing_type tag
```

### Observability
- Structured logging (`backend/utils/logger.py`) -- WARN+ persists to `error_log` table
- FastAPI request middleware with timing and request_id tracking
- API endpoints: `/api/errors`, `/api/errors/summary`
- Job tracking: `job_runs` table, `/api/status` endpoint
- Data retention: self-managing via `run_retention_cleanup()` PostgreSQL function

### Database State
- 25,434 cards (40 players)
- 42,313 sales (real eBay sold data)
- 44,165 active listings (BIN + Auction)
- 4,400 market rates (SCP prices with Ungraded/Grade 9/PSA 10)
- 334 SCP cache entries (24h TTL)
- 25 sold comps (130point eBay sold data, growing via worm)
- 133 opportunities (latest scan, stored in DB)
- 23 migrations tracked (schema_migrations table on both local + RDS)
- 19 tables in both databases
- Primary DB: RDS (`cardpulse-db.ckvp9bhavaww.us-east-1.rds.amazonaws.com`)
- Local DB: PostgreSQL localhost (structurally synced via migrate.py)
- Sport: Baseball only

### Auction-First Pipeline (Rewritten -- March 22)
File: `find_auction_opportunities.py`

Flips the standard pipeline: eBay auctions first, SCP validation second.
1. Search eBay for auctions ending within 48h using value-focused + player-specific queries (110 queries with pagination)
2. Category filter: eBay category 261328 (Trading Card Singles)
3. Quality filter: card number + player (period-normalized, accent-stripped, eBay aspects fallback) + not junk + within budget
4. SCP validation: DB lookup first, SCP cache (24h TTL), Selenium fallback
5. Multi-pass SCP matching: Pass 1 exact, Pass 2A strict text, Pass 2B fuzzy word-overlap, Pass 3 signals
6. BIN sanity check: hybrid listing BIN < 50% of SCP = reject
7. Profit check: SCP * 0.87 - (current bid + shipping) >= $10
8. Store in opportunities table with listing_type='auction'
9. Diagnostic logging on no_scp cards (first 30)

Latest run: 522 unique auctions found, 198 qualified after quality filter.

### Infrastructure Ready
- GitHub Actions workflows: BIN pipeline + Auction pipeline (both workflow_dispatch)
- RDS CloudFormation template (`aws/cloudformation/rds.yaml`) -- PostgreSQL free tier with self-contained VPC
- RDS deployed and running: `cardpulse-db.ckvp9bhavaww.us-east-1.rds.amazonaws.com:5432` (legacy name, domain is ragnarokgamez.com)
- 23 migrations tracked via `schema_migrations` table (both local + RDS)
- Migration runner: `python3 migrate.py --both` (applies pending, skips already-applied)
- Legacy migration scripts: `aws/apply-rds-migrations.sh`, `aws/migrate-to-rds.sh`
- Code pushed to GitHub (`tweedledee101/TradingCards`, main branch)
- GitHub secrets configured: `DATABASE_URL`, `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`
- Firefox binary auto-detection for local vs GitHub Actions environments

### Other Working Systems
- Volume-based player discovery (45 seed players, ranked by eBay volume)
- Master pipeline (`run_pipeline_full.py`) -- all 5 steps
- Set-specific eBay searches (7 queries/player)
- Precise parallel extraction (80+ patterns)
- Insert set detection (20+ insert names)
- eBay API (production, auto-refreshing OAuth, 5,000 calls/day)
- SCP scraper (Firefox/Selenium) -- search and direct product page scraping
- Card images from eBay thumbnails
- PostgreSQL database with variant-aware schema (migrations 001-010)
- FastAPI REST API with 18+ endpoints
- React frontend with Ragnarok Gaming dark theme
- Opportunities page: scan timestamp, SCP verify link, 3 price tiers, eBay images, "Needs Review" section

### Players (40 total)
Ken Griffey Jr, Shohei Ohtani, Nolan Ryan, Mike Trout, Cal Ripken Jr,
Aaron Judge, Derek Jeter, Ronald Acuna Jr, Juan Soto, Bryce Harper,
Fernando Tatis Jr, Mookie Betts, Julio Rodriguez, Bobby Witt Jr,
Freddie Freeman, Elly De La Cruz, Ichiro Suzuki, Paul Skenes,
Adley Rutschman, Corbin Carroll, James Wood, Corey Seager,
Jackson Chourio, Jasson Dominguez, Gunnar Henderson, Jackson Holliday,
Trea Turner, Dylan Crews, Jackson Merrill, Roki Sasaki,
Yoshinobu Yamamoto, Junior Caminero, Marcelo Mayer, Wyatt Langford,
Evan Carter, Colton Cowser, Jordan Walker, Masyn Winn,
Spencer Strider, Jac Caglianone

---

## WHAT'S BROKEN -- HONEST ASSESSMENT

### 1. Grade Mismatch
Pipeline compares ungraded SCP price to graded eBay listings (and vice versa). Example: Juan Soto Gold Stars #224 -- SCP ungraded is $1.50, PSA 10 is $30. Pipeline matched a $9.99 ungraded BIN against the PSA 10 price and showed $17 profit. Completely wrong.

### 2. Variant Matching Still Too Loose
"Magenta Speckle Refractor" matched to SCP "Magenta Refractor" -- different cards, different print runs (/350 vs /399). Pipeline needs to treat sub-variants as distinct parallels.

### 3. SCP Price Reliability on Low-Volume Cards
SCP prices based on 1-3 sales from 2+ years ago are historical artifacts, not current market value. Example: Jordan Walker Father's Day Blue -- SCP says $220 based on 2023-2024 sales, but the card hasn't sold in 6 months and the trend is clearly down. The pipeline treats stale SCP prices as gospel.

Worse: some low-volume SCP pages have misclassified sales (Juan Soto sales appearing on a Jordan Walker product page). When there are only 2-3 total sales, one misclassified entry corrupts the entire price.

### 4. Volume Filter Not Tight Enough
"3 sales per year" currently passes the volume filter but produces nothing but noise in practice. Every card manually validated at that volume level was a pass -- either dead money, declining trend, or no exit liquidity.

### 5. Factory Set Filter Blind Spot
Factory set filter checks eBay titles but not SCP product names. When the eBay title says "2020 Topps #224 Gold Star" (no "complete set" mention) but the SCP product is "2020 Topps Complete Set", the filter misses it.

### 6. Reprint Detection Gaps
Cal Ripken "R&N China Topps Porcelain" and "2015 Topps Cardboard Icon 5x7" are reprints that don't match current REPRINT_PATTERNS. Need to add "porcelain", "cardboard icon", "5x7" patterns.

### 7. Team Set / Multi-Card Listings
Nolan Ryan 1972 Topps -- eBay listing was "California Angels Team Set w/o #595 Nolan Ryan (27)" -- a team set WITHOUT the Ryan card. Pipeline matched it as a single card.

---

## LESSONS LEARNED (March 20 -- Manual Validation Session)

### Volume Is Everything
Every card manually validated with "3 sales per year" or less was a pass:
- Jordan Walker Father's Day Blue /50: 3 sales/year, declining from $470 to $190, no PSA 9 data
- Jordan Walker Brick by Brick Auto /50: 3 sales/year, last sale July 2023, zero recent eBay solds
- Jordan Walker Leaf Ultimate Auto: 1 sale/year, SCP page has misclassified sales
- Juan Soto Gold Mosaic /10: 1 sale ever (2022), BGS 9 not PSA, no exit

The one card that looked like a real opportunity: Juan Soto Mystical Green /99 -- "1 sale per month" volume, 3 recent comps validating the SCP price, active player, stable trend.

### Real Arbitrage Range
Real opportunities exist in the 50-85% of SCP range. Below 30% is almost certainly a different product. Between 30-50% needs manual review. The efficient market hypothesis holds for popular players on popular cards -- cheap BIN listings are cheap for a reason (factory set, wrong variant, damaged, etc.).

### Auctions Are Where Margins Live
BIN below market rate is inherently suspicious. Auctions ending below market rate is normal -- that's how auctions work. The pipeline was excluding all auctions, which was cutting off the best opportunities.

---

## What Changed (March 22 2026 -- Session 12)

### NEW: Three-Tier Pricing Waterfall
- When SCP fails to match a card, pipeline now tries two fallback sources before giving up
- Tier 1: SCP (DB lookup, SCP cache 24h TTL, Selenium fallback) -- primary, highest confidence
- Tier 2: 130point sold comps (DB cache from background worm, instant, free) -- actual eBay sold prices
- Tier 3: eBay active BIN comps (1 API call per card, median of 3+ listings) -- market asking prices
- All fallback-priced opportunities flagged for review (lower confidence than SCP)

### NEW: 130point.com Scraper (`backend/scrapers/oneThirtyPoint_scraper.py`)
- Plain HTTP POST to `https://back.130point.com/sales/` -- no Selenium needed
- Returns actual completed eBay sale prices, dates, listing types (auction vs fixed)
- Rate limit: 10 requests/minute (we enforce 7s between calls)
- Zero eBay API calls consumed

### NEW: Background Data Worm (`worm_130point.py`)
- Slowly crawls 130point.com building a local cache of eBay sold data in `sold_comps` table
- Prioritizes: cards with SCP rates first (cross-validation), then cards without (discovery)
- 48h TTL on cached data, ~8 queries/min = ~14,000/day capacity, all free
- Run: `nohup python3 worm_130point.py --limit 1000 > /tmp/worm.log 2>&1 &`

### NEW: eBay BIN Comps Fallback
- `search_active_bin_comps()` in ebay_scraper.py -- searches BIN-only listings, 1 API call
- `find_ebay_comps_fallback()` -- median of 3+ ungraded BINs, trims outliers
- Tested: Max Anderson Mojo Auto $24.49 (4 comps), Trey Sweeney Auto $15.00 (15 comps)

### NEW: Database Migration 014 -- sold_comps table
- player_name, card_year, card_set, card_number, parallel, sale_price, sale_type, sale_date
- Indexed: (lower(player_name), card_year, lower(card_number))

### KEY DISCOVERY: 130point returns actual SOLD data (not asking prices)
- eBay Browse API returns active listings (asking prices)
- 130point aggregates actual completed eBay sales (sold prices)
- More conservative and accurate: Max Anderson Mojo -- 130point $14.99 (sold) vs eBay BIN $24.49 (asking)

### KEY DISCOVERY: eBay Browse API `total` field
- Every search returns `total` count even with `limit=1` (1 API call = 1 volume reading)
- Enables cheap volume-based player discovery without fetching items

## What Changed (March 22 2026 -- Session 13)

### NEW: Cross-Validation QA Rule
- `scp_vs_sold_comps` rule in `qa_opportunities.py`: flags when SCP price diverges >50% from 130point sold median
- Requires 3+ sold comps, trims outliers, severity warning at >50%, critical at >75%
- Runs as part of standard QA pass (does not block pipeline)

### NEW: Price Source Tracking
- Migration 015: `price_source` column on opportunities table (values: scp, sold_comps, ebay_comps)
- Wired into both BIN pipeline (always 'scp') and auction pipeline (tracks three-tier fallback)
- Exposed in API responses, displayed as confidence badges in frontend

### NEW: $10 Minimum Profit Floor
- BIN pipeline default changed from $5 to $10 (matches auction pipeline)
- Both pipelines still accept `--min-profit` override

### NEW: Tabbed Card Detail Modal (`CardDetailModal.jsx`)
- Hero section: large card image, key numbers, live countdown, action buttons (always visible)
- Overview tab: player analytics (30d sales, avg sale, velocity, active listings), SCP price tiers, QA flags
- Sell-Through tab: sell-through speed bars by price bucket, capital efficiency callout ("$20.51/day return")
- Price History tab: Recharts sparkline (avg/min/max sale price, SCP reference line), daily volume bars
- Timing tab: day-of-week avg price chart (cheapest day highlighted green), hourly sales volume
- Lazy-loads tab data only when clicked

### NEW: Player Analytics API
- `/api/players/{name}/stats`: cards, sales, velocity, avg sale price, market rates, opportunities, sell-through buckets
- `/api/players/{name}/price-history`: daily avg/min/max sale prices for sparkline chart
- `/api/players/{name}/timing`: day-of-week and hour-of-day sale patterns
- Accent normalization: Acu\u00f1a matches Acuna (fixes zero-data bug for accented player names)

### NEW: Live Countdown Timers
- Every auction card shows seconds ticking: `14h 02m 37s` format
- Client-side 1-second intervals against `end_time` from DB
- `end_time` now exposed in auction API response
- Modal shows live countdown in pricing grid
- Ended auctions show "Ended" label with dimmed opacity

### NEW: Confidence Badges
- Green "SCP" badge: priced from SportsCardsPro (highest confidence)
- Blue "Sold Comps" badge: priced from 130point sold data
- Amber "Market Comps" badge: priced from eBay BIN comps (lowest confidence)
- Shown on every card in list view and in modal hero

### NEW: Scheduled Bids Infrastructure (Snipe Queue)
- Migration 016: `scheduled_bids` table (max_bid, snipe_seconds, ebay_item_id, end_time, status)
- API: POST/GET/DELETE `/api/scheduled-bids`
- Model: `ScheduledBid` in models/__init__.py
- Frontend: Snipe UI complete (Session 14)
- Placeholder for future eBay OAuth auto-bid integration

### NEW: Worm Improvements
- `--opportunities` flag: crawls cards from opportunities table first (cross-validation priority)
- 429 retry logic: 10-minute wait, up to 3 retries (was dying immediately on rate limit)

### FIX: Accent Mismatch in Player Stats
- `Ronald Acu\u00f1a Jr.` (opportunities) vs `Ronald Acuna Jr` (cards) now match
- Uses unicodedata NFD normalization + period stripping
- Affects player stats API and all player-level queries

### NEW: Frontend Features
- QA flags displayed in expanded card view (color-coded by severity)
- "Full Details" button in expanded card view opens modal
- Card thumbnails clickable to open modal
- Filter bar with Max Bid, Min Profit, Min ROI inputs

## What Changed (March 23 2026 -- Session 14)

### NEW: Snipe UI in Card Detail Modal
- "Snipe $XX.XX" button: calculates recommended max bid from SCP (SCP * 0.87 - $10 profit - shipping)
- Expands to snipe panel: big profit headline (updates live as user adjusts bid), math formula summary, bid input pre-filled with recommended price, snipe timing dropdown (3/5/10/15/30s), Queue button
- "Schedule Bid" button: manual entry for users who have their own number, separate panel with bid input + timing + live profit preview
- Panels are mutually exclusive (opening one closes the other)
- After scheduling: both buttons replaced with "Bid Queued" badge
- BIN cards show "Buy $XX.XX" green button linking directly to eBay
- Timer and bid count separated to their own context row (not competing with action buttons)
- eBay/SCP links demoted to small text links (reference, not decisions)

### NEW: My Bids Strip on Opportunities Page
- Horizontal scrollable strip at top of Opportunities page showing all scheduled bids
- Each bid card: thumbnail, player/card info, live countdown (1-second ticks), max bid, snipe timing
- Urgency indicators: normal -> amber (< 1 hour) -> red pulse (within 2x snipe window)
- Cancel button removes bid via API, View link opens eBay listing
- Strip hidden when no scheduled bids exist

### NEW: RDS as Primary Database
- `.env` DATABASE_URL switched from localhost to RDS
- All pipeline runs now write to RDS by default
- Local database kept structurally in sync for fallback

### NEW: Migration Runner (`migrate.py`)
- `schema_migrations` table tracks which migrations have been applied
- `python3 migrate.py --both`: applies pending migrations to local + RDS
- `python3 migrate.py --status --both`: shows applied vs pending
- `python3 migrate.py --local` / `--rds`: target one database
- Handles already-existing objects gracefully (records as applied, doesn't fail)
- 23 migrations tracked on both databases, both up to date

### FIX: Variable Ordering Bug in CardDetailModal
- `recSnipe` was referencing `scpPrice` and `shipping` before they were declared
- Moved recommended snipe calculation below variable declarations

## What Changed (March 22 2026 -- Session 11)

### REWRITE: Auction Search Strategy
- Replaced 101 set-specific queries ("2023 Topps Series 1", etc.) with 110 value-focused + player-specific queries
- 30 value queries: numbered parallels (/25, /50, /99...), autographs, refractors, premium products (Tier One, Tribute, Museum, etc.)
- 80 player queries: top 40 DB players x 2 ("player auto numbered" + "player refractor")
- Added pagination: up to 1000 results per query (was capped at 200)
- Result: searches like a dealer, not like a catalog

### NEW: Fuzzy Parallel Matching (Pass 2B)
- Pass 2A: strict match (all SCP parallel words in eBay title) -- unchanged
- Pass 2B: word-overlap scoring -- extracts meaningful words from both SCP parallel and eBay title, scores by overlap fraction
- Requires 50%+ overlap and at least 1 meaningful word match
- Picks best unambiguous match; refuses to guess on ties
- Fixes: "Aqua" now matches "Aqua Refractor", "Sparkle Refractor" matches "Refractor Chrome Variation"
- Noise words filtered: set names, generic terms (card, baseball, topps, etc.)

### NEW: BIN Sanity Check for Hybrid Listings
- If auction+BIN hybrid listing has BIN price < 50% of SCP price, reject the opportunity
- Seller's own BIN is a market signal -- if they'll sell for $6 and SCP says $27, SCP match is wrong
- Catches the Dylan Crews false positive: $6 BIN vs $27 SCP = 22% ratio = rejected

### FIX: Hybrid Auction+BIN Price Extraction
- eBay's `price` field on hybrids returns the BIN price, not the current bid
- Now uses `currentBidPrice` for the actual bid amount
- BIN price stored separately in `bin_price` field for sanity checking
- Pure auctions unaffected (no `currentBidPrice` field)

### FIX: Player Name Period Matching
- MLB API stores "Vladimir Guerrero Jr." with period; eBay titles use "VLADIMIR GUERRERO JR" without
- Both player names and titles now stripped of periods before matching
- Fixes all Jr./Sr. players: Vlad Jr, Tatis Jr, Witt Jr, Griffey Jr, Acuna Jr, Ripken Jr

### FIX: eBay Scraper Player Aspect Names
- `get_full_item_details()` now accepts Player, Player/Athlete, Athlete, Player Name (was only Player)
- Detail lookup fallback now checks `detail_aspects` dict (was incorrectly checking search-level `aspects`)

### NEW: SCP Match Diagnostic Logging
- First 30 no_scp cards now show: variants found, variant names+prices, Pass 1 tried value, Pass 2 search text, Pass 3 signals, eBay title
- `find_scp_match_via_selenium()` returns 3-tuple: (result, was_cached, diagnostics)
- Diagnostics dict tracks: variants_found, variant_names, pass1_tried, pass2_searched, pass3_signals, fail_reason
- Makes the SCP matching black hole visible for debugging

## What Changed (March 22 2026 -- Session 10)

### NEW: QA Validation System
- `qa_opportunities.py`: background post-pipeline validator
- Rules: extreme_roi (>500%), high_roi (>300%), price_ratio_10x, no_scp_url, card_number_mismatch, low_bid_high_scp
- Stores qa_status (pending/clean/flagged/critical), qa_flags (JSONB), qa_reviewed_at on opportunities
- Migration 012: qa_status, qa_flags, qa_reviewed_at columns
- Does NOT block pipeline -- runs after, in the background

### NEW: MLB Stats API Player Roster
- Replaced 40-player DB lookup with MLB Stats API (`statsapi.mlb.com/api/v1/sports/1/players?season=YEAR`)
- Free, no auth, ~1,400 players per year, 2,104 unique across 2023-2026
- Dramatically reduced "no_player" skip rate in auction pipeline
- Names sorted longest-first to prevent partial matches

### NEW: QA Test Suite (67 tests passing)
- `tests/qa/test_scp_matching.py`: 40 tests for SCP matching logic
- `tests/qa/test_opportunity_analyzer.py`: 19 tests for profit/fee/auction calculations
- `tests/qa/test_api_contract.py`: 8 tests for API response shape
- Fixed JSONB/SQLite incompatibility in conftest.py

### NEW: Unified Pipeline
- `find_opportunities.py` now automatically runs auction pipeline after BIN completes
- One command runs both: `python3 find_opportunities.py --max-budget 200 --min-profit 5 --min-roi 20 --top-players 40`
- BIN pipeline only clears BIN results (was wiping auctions)

### FIX: SCP Selenium Matching (Critical)
- Removed wrong-parallel fallback (was returning first result with any price)
- Added `_scp_url_has_card_number()` -- verifies card number in SCP URL before accepting
- Exact parallel match only, no fallback

### FIX: Lot Detection
- Added `is_lot()` function: detects multiple # signs, X & Y & Z patterns, "N cards" language
- Integrated into `is_junk()` filter

### NEW: Domain -- ragnarokgamez.com
- ACM certificate issued: `arn:aws:acm:us-east-1:635601810497:certificate/8dda492b-b16f-45bf-965e-9268abaabe78`
- Covers ragnarokgamez.com + *.ragnarokgamez.com
- All docs updated from cardpulse.jgaffiliated.com to ragnarokgamez.com
- Logger namespace changed from cardpulse to ragnarok
- AWS resource names (RDS endpoint, stack names) unchanged (deployed infrastructure)

### NEW: Roadmap Additions
- Milestone 4.5: UI Behavior Tracking (user_events table, feedback loop with QA flags)
- Milestone 9: Predict the Spike (standard leading indicators + nuanced signals: social media, artist features, local communities, call-ups, breaker schedules, cross-sport correlation)
- ADR-005 planned: User model, personalization, opportunity scoping

## What Changed (March 21 2026 -- Session 9)

### NEW: Auction-First Pipeline (`find_auction_opportunities.py`)
- Searches eBay for auctions ending soon by year + set name (not generic "baseball card")
- 101 search queries across 4 years x 24+ sets (Topps Chrome, Bowman Chrome, etc.)
- eBay category 261328 filter (Trading Card Singles only)
- Player name extraction: DB match (40 players) -> eBay item aspects fallback
- Card number extraction: title -> aspects -> full item details (3-pass)
- Quality signals: serialed (/XX), auto, rookie, non-base parallel
- SCP validation: database first (4,400 market rates), Selenium fallback
- Profit formula: SCP * 0.87 - (bid + shipping) >= $10
- Resilient Selenium: if Firefox fails, continues with DB-only matches
- Progress output during quality filtering (every 50 auctions, every 25 detail lookups)
- Stores: shipping, bid_count, end_time, scp_volume in opportunities table
- GitHub Actions workflow: `.github/workflows/auction-pipeline.yml`

### NEW: Database Migration 011
- Added columns to opportunities: shipping, bid_count, end_time, scp_volume

### FIX: SportsCardsPro Scraper Firefox Binary
- Auto-detects Firefox binary path (was hardcoded to `/usr/bin/firefox`)
- Now checks `/usr/lib/firefox/firefox`, `/usr/bin/firefox-esr`, `/usr/bin/firefox`

### FIX: API Auction Dict
- `_auction_to_dict()` now uses stored shipping, bid_count, end_time from DB
- Calculates hours_left dynamically from end_time
- Includes scp_volume in response

---

## What Changed (March 20 2026 -- Sessions 7-8)

### NEW: Auction Support
- Removed hard auction filter -- auctions now flow through the pipeline
- Auctions skip price floor check (low current bids are normal)
- Auctions are never flagged as "suspicious price"
- Every opportunity tagged with `listing_type` (buy_it_now or auction)
- Console output shows [BIN] or [AUCTION] tags
- Summary shows breakdown: "113 opportunities found (85 BIN, 28 Auction)"
- Database: `listing_type` column added (migration_010)
- API: `?listing_type=auction` filter, `/api/auctions` endpoint now functional

### NEW: Pipeline Quality Filters (Session 7)
- Auction filtering: discovered pipeline was treating auction bids as BIN prices, fixed
- Factory set filter: 12 patterns (complete set, montgomery club, walmart/target exclusive, etc.)
- Price floor: BIN below 30% of SCP hard-rejected (MIN_PRICE_RATIO = 0.30)
- Suspicious flagging: BIN between 30-50% of SCP flagged for "Needs Review"
- Volume capture: parses SCP volume text ("1 sale per day", "rare", etc.)
- Volume filter: skips "rare", "1 sale per year", "2 sales per year"

### NEW: GitHub Actions + RDS Infrastructure (Session 7)
- `.github/workflows/pipeline.yml`: workflow_dispatch with configurable inputs
- `aws/cloudformation/rds.yaml`: RDS PostgreSQL free tier template
- `aws/migrate-to-rds.sh`: local-to-RDS migration script

### Previous Sessions
- Session 6 (March 19-20): SCP-to-eBay pipeline built and validated
- Session 5 (March 19): SCP card-number-first matching rewrite
- Session 4 (March 19): Graduated SCP search + set validation, insert set detection
- Session 3 (March 18): Parallel precision, volume expansion to 40 players, Ragnarok Gaming UI
- Session 2 (March 18): Card images, Leaf sub-sets, SCP sanity check, buy links
- Session 1 (March 18): Pipeline, discovery, OpportunityAnalyzer core

---

## Known Issues / Next Steps (Priority Order)

### 1. TIGHTEN VOLUME FILTER
Reject "3 sales per year" -- every card at that level was a pass during manual validation. Minimum viable volume is "1 sale per month".

### 2. ADD MINIMUM PROFIT THRESHOLD
$6 profit on an $18 card isn't worth the research time. Need a minimum dollar amount ($15-20).

### 3. FIX GRADE MISMATCH
Pipeline must compare ungraded-to-ungraded, graded-to-graded. Currently uses SCP ungraded price for all listings regardless of grade.

### 4. FIX VARIANT MATCHING
"Magenta Speckle" != "Magenta". Sub-variants need to be treated as distinct parallels.

### 5. EXPAND REPRINT PATTERNS
Add: "porcelain", "cardboard icon", "5x7", "team set", "set w/o", "set without".

### 6. WORKER SEPARATION (Milestone 1)
Data gathering (SCP scraping, eBay API calls) must run in a separate process from the core app. See ADR-004.

### 7. DEMAND-DRIVEN REFRESH (Milestone 2)
No crons. Data refreshes only when needed. See ADR-004.

### 8. CROSS-VALIDATE SCP PRICES
130point sold comps now available for cross-validation. Next: auto-flag when SCP and 130point median diverge by >50%.

### 9. Redesign Remaining Pages
Inventory, Watchlist, CardDetail still have old white theme.

### 10. AWS DEPLOYMENT (Milestone 3)
Core app on ECS, worker on ECS task, database on RDS, frontend on CloudFront + S3.

### 11. EBAY ACCOUNT INTEGRATION (Milestone 3)
OAuth login, auto-import purchases, auto-track sales.

### 12. APPLY FOR EBAY COMPATIBLE APPLICATION STATUS
Upgrade from 5,000 to 50,000-200,000+ API calls/day.

### 13. Basketball/Football Support (Milestone 6)

See `docs/ROADMAP.md` for full feature roadmap with milestones.

---

## Architecture

### Opportunity Pipeline
```
HOT PLAYERS (from eBay sales volume or manual list)
    |
    v
[SCP Selenium] -- 1 search per player --> full catalog (100 variations + prices + volume)
    |
    v
FILTER -- $20-$1000 SCP price range
       -- Volume filter (reject rare, 1/year, 2/year)
    |
    v
[eBay Browse API] -- 1 search per variation --> active listings (BIN + Auctions)
    |
    v
VALIDATE -- player name + year + card# + variation keyword in title
         -- exclude junk, factory sets, reprints, wrong sets
         -- BIN price floor (30% of SCP)
    |
    v
CALCULATE -- SCP price - buy price - 13% fees = profit
    |
    v
STORE -- opportunities table (listing_type: buy_it_now or auction)
    |
    v
API --> Ragnarok Gaming UI (BIN + Auction tabs, Needs Review section)
```

## Key Files

| File | Purpose |
|------|---------|
| `find_opportunities.py` | SCP-to-eBay BIN opportunity pipeline |
| `find_auction_opportunities.py` | eBay-first auction opportunity pipeline (3-tier pricing) |
| `worm_130point.py` | Background 130point sold data crawler |
| `backend/scrapers/oneThirtyPoint_scraper.py` | 130point.com eBay sold data scraper |
| `backend/models/__init__.py` | SQLAlchemy models (Opportunity with listing_type) |
| `backend/api/routes/opportunities.py` | Opportunities + Auctions API endpoints |
| `frontend/src/pages/Opportunities.jsx` | Opportunities page (Ragnarok Gaming theme) |
| `backend/run_pipeline_full.py` | Master data pipeline (7 queries/player) |
| `backend/scrapers/ebay_scraper.py` | eBay import + parallel extraction |
| `backend/utils/logger.py` | Structured logging (WARN+ to DB) |
| `backend/utils/job_tracker.py` | Job tracking (job_runs table) |
| `backend/utils/retention.py` | Self-managing data retention |
| `.github/workflows/pipeline.yml` | GitHub Actions BIN pipeline workflow |
| `.github/workflows/auction-pipeline.yml` | GitHub Actions auction pipeline workflow |
| `aws/cloudformation/rds.yaml` | RDS PostgreSQL CloudFormation template |
| `PIPELINE-OPS.md` | Operations guide |

## Services

```bash
sudo service postgresql start

# API: http://localhost:8000 (Swagger: /docs)
cd /home/tweedledee101/TradingCards
nohup /usr/bin/python3 -m backend.api.run > /tmp/api.log 2>&1 &

# Frontend: http://localhost:3000
cd /home/tweedledee101/TradingCards/frontend
nohup npm run dev > /tmp/frontend.log 2>&1 &
```
