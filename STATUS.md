# Trading Card Platform - Current Status
**Last Updated:** 2026-03-20

## SYSTEM STATUS: PIPELINE RUNNING, QUALITY HARDENING IN PROGRESS

The SCP-to-eBay opportunity pipeline (`find_opportunities.py`) is running full 40-player scans. Latest scan: 1074 variations checked, 113 opportunities found. Pipeline now includes BIN and auction listings, volume filtering, price floor, factory set detection, and reprint filtering. Opportunities stored in database and served via API to the frontend.

### Quick Start

```bash
sudo service postgresql start
cd /home/tweedledee101/TradingCards

# Run opportunity finder (SCP catalog -> eBay active listings)
python3 find_opportunities.py --max-budget 200 --min-profit 5 --min-roi 20 --top-players 40

# Or specify players
python3 find_opportunities.py --max-budget 200 --min-profit 5 --players "Bobby Witt Jr,Mike Trout"

# Start services
nohup /usr/bin/python3 -m backend.api.run > /tmp/api.log 2>&1 &
cd frontend && nohup npm run dev > /tmp/frontend.log 2>&1 &
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
- ~724 market rates (from old collection approach)
- 113 opportunities (latest scan, stored in DB)
- Sport: Baseball only

### Infrastructure Ready
- GitHub Actions workflow (`.github/workflows/pipeline.yml`) -- run pipeline off-laptop
- RDS CloudFormation template (`aws/cloudformation/rds.yaml`) -- PostgreSQL free tier
- Migration script (`aws/migrate-to-rds.sh`) -- dump local DB, load into RDS
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
For high-value opportunities, check eBay sold data to confirm SCP price is realistic.

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
| `find_opportunities.py` | SCP-to-eBay opportunity pipeline (PRIMARY) |
| `backend/models/__init__.py` | SQLAlchemy models (Opportunity with listing_type) |
| `backend/api/routes/opportunities.py` | Opportunities + Auctions API endpoints |
| `frontend/src/pages/Opportunities.jsx` | Opportunities page (Ragnarok Gaming theme) |
| `backend/run_pipeline_full.py` | Master data pipeline (7 queries/player) |
| `backend/scrapers/ebay_scraper.py` | eBay import + parallel extraction |
| `backend/utils/logger.py` | Structured logging (WARN+ to DB) |
| `backend/utils/job_tracker.py` | Job tracking (job_runs table) |
| `backend/utils/retention.py` | Self-managing data retention |
| `.github/workflows/pipeline.yml` | GitHub Actions pipeline workflow |
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
