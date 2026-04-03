# Pipeline Operations Guide

## One Command To Rule Them All

```bash
cd /home/tweedledee101/TradingCards
/usr/bin/python3 -m backend.run_pipeline_full --fresh --sport Baseball --top 40
```

## What The Pipeline Does (In Order)

| Step | What | API Calls (40 players) | Time |
|------|------|------------------------|------|
| 1. Discover | Search 45 seed players, rank by eBay volume | 45 eBay | ~30s |
| 2. Import Sales | Fetch sold listings (7 queries/player) | 280 eBay | ~15min |
| 3. Active Listings | Fetch current listings (7 queries/player) | 280 eBay | ~15min |
| 4. Trends | Calculate price trends from sales data | 0 | ~5s |
| 5. SCP Rates | Scrape SportsCardsPro (graduated search + set validation) | 0 eBay | 2-8 hrs |

**Total eBay API calls: ~605/day (of 5,000 limit)**

### Set-Specific Searches (Step 2 & 3)

Each player gets 7 eBay queries instead of 1:
1. `{player} card` (generic)
2. `{player} Topps Chrome`
3. `{player} Bowman Chrome`
4. `{player} Topps Heritage`
5. `{player} Stadium Club`
6. `{player} Topps Finest`
7. `{player} Topps Inception`

Results are deduped by ebay_item_id across queries. This surfaces high-value parallels ($10-$100+) that get buried in generic searches (eBay returns max 200 per query).

Sets are configured in `backend/config/sets.py` (also has Basketball/Football sets).

## Pipeline Flags

```bash
--fresh              # Wipe all data first
--sport Baseball     # Sport filter (default: Baseball)
--top 40             # Number of top players (default: 20)
--skip-scp           # Skip slow SCP step
--skip-discovery     # Reuse existing players in DB
--scp-timeout 7200   # SCP timeout in seconds (default: 1800)
--days 7             # Discovery lookback days (default: 7)
```

## Running Auction Finder (eBay-First)

Searches eBay for auctions ending soon, validates against SCP.

### Basic Usage
```bash
# Default: 48h window, $10 min profit, $200 max budget, baseball
python3 find_auction_opportunities.py

# Tighter window, higher profit threshold
python3 find_auction_opportunities.py --hours 24 --min-profit 15

# Specific years only
python3 find_auction_opportunities.py --years 2025,2026

# Dry run (no DB storage)
python3 find_auction_opportunities.py --dry-run
```

### Auction Finder Flags
```bash
--hours 48           # Auctions ending within X hours (default: 48)
--min-profit 10      # Min profit after bid + shipping + fees (default: $10)
--max-budget 200     # Max bid + shipping (default: $200)
--years 2023,2024,2025,2026  # Years to search (default: all four)
--sport baseball     # Sport (default: baseball)
--dry-run            # Show results without storing in DB
```

### Audit auction funnel (data, not guesses)

After any `auction_finder` run, `job_runs.results_summary` stores JSON including **`auctions_searched`**, **`qualified`**, **`step2_skip_reasons`** (why listings dropped before SCP), **`step3_*`** counters (no pricing, bin sanity, low volume, below min profit), and **`opportunities_found`**.

**Step 3 pricing funnel:** **`step3_no_pricing`** counts listings with **no price after all sources**. **`step3_no_pricing_after_primary`** = entered fallback (no DB/SCP price). **`step3_no_pricing_after_sold_comps`** = still no price after 130point (so eBay BIN comps were tried or skipped). Compare the three to see whether the gap is **SCP**, **sold comps**, or **eBay comps**.

```bash
export DATABASE_URL='postgresql://...'   # RDS or local
python3 scripts/audit_auction_pipeline.py
# Re-measure vs previous run (newest vs second-newest job with JSON summary):
python3 scripts/audit_auction_pipeline.py --compare
```

**Stale ended auction rows** (audit prints `ended_still_stored`):

```bash
python3 scripts/cleanup_stale_auction_opportunities.py --dry-run
python3 scripts/cleanup_stale_auction_opportunities.py
```

Interpretation:

- **`qualified` ≪ `auctions_searched`** → Step 2 (card #, player, year, junk, budget) is the bottleneck; fix identity extraction / queries before SCP.
- **`step3_below_min_profit` dominates** → economic threshold or bid+ship too high vs comps; experiment `--min-profit` / `--max-budget` in **dry-run** and compare counts.
- **`step3_no_pricing` dominates** → use **`after_primary`** vs **`after_sold_comps`** vs final: primary SCP miss vs thin 130point vs weak eBay BIN comp set.

### Auction improvement hypotheses (test in order)

| Hypothesis | How to test | If true, lever |
|------------|-------------|----------------|
| H1: Most raw auctions die in Step 2 (`no_card_number`, `no_player`) | Run audit script; read `step2_skip_reasons` on latest run | Description/`shortDescription` `#` parse; more `get_full_item_details` coverage; broader aspects |
| H2: Many qualify but fail `step3_no_pricing` | `step3_no_pricing` large vs `qualified` | SCP cache fill rate, Selenium health, `sold_comps` worm volume, parallel matching fixes |
| H3: Pricing works but `step3_below_min_profit` dominates | Counters in `results_summary` | Soften `--min-profit` for a “scout” tier in UI; or raise `--max-budget` for high-end flips |
| H4: UI shows 3 because most rows **ended** | `ended_still_stored` vs `active_ui` in audit | Shorter `--hours` refresh cadence or filter/cleanup ended rows; run pipeline more often |
| H5: Query set misses liquid segments | `auctions_searched` high, `qualified` flat | Pipeline adds **`get_set_queries`** for top 15 DB players (see `HIGH_VALUE_SETS`); tune player cap or sets in `backend/config/sets.py` |

**SCP Selenium slow loads:** Firefox may log `Navigation timed out after … ms`; the scraper catches that and still parses partial HTML when possible. Raise **`SCP_PAGE_LOAD_TIMEOUT`** in `backend/.env` (default **60**s, max **180**) if timeouts are frequent.

**Services in play today (auctions):** eBay **Browse API** (`item_summary/search` ending soon, `item/{id}` details, BIN comp search), **MLB Stats API** (player names), **SportsCardsPro** (Selenium when DB/cache miss), **`sold_comps` / 130point worm**, **PostgreSQL** (`opportunities`, `job_runs`, `error_log`, `scp_cache`, `market_rates`).

**Can leverage more (experiments):** extra Browse queries (same API, watch daily cap), second sport flag, duplicate **set-specific** auction queries (proven in BIN pipeline’s 7-queries-per-player pattern), Trading API only if Browse lacks a field (extra app/credentials).

### What The Auction Finder Does

1. Searches eBay using **value queries + per-player queries** (top 40 DB players: auto/refractor + **set-specific** queries for the top 15 via `backend/config/sets.py`)
2. Paginates up to 1000 results per query (5 pages x 200)
3. Filters to eBay category 261328 (Trading Card Singles)
4. Deduplicates across all queries by eBay item ID
5. Quality filter: card number required (title -> aspects -> full item details)
6. Player identification: MLB Stats API roster (2,269 players) + period/accent normalization + eBay aspects fallback (Player/Athlete/Player Name)
7. SCP validation: database lookup first (4,400 market rates), SCP cache (24h TTL), Selenium fallback
8. Multi-pass SCP matching: Pass 1 exact parallel, Pass 2A strict text, Pass 2B fuzzy word-overlap (50%+), Pass 3 signal match (RC/Auto/Relic/print_run)
9. BIN sanity check: hybrid listing BIN < 50% of SCP = reject (seller disagrees)
10. Profit check: SCP * 0.87 - (current bid + shipping) >= $10
11. Fallback pricing: 130point sold comps (DB cache) -> eBay active BIN comps (1 API call)
12. Diagnostic logging: first 30 no_scp cards show variants found, pass attempts, failure reason
13. Stores opportunities with listing_type='auction', shipping, bid_count, end_time

---

## Running 130point Data Worm (Background)

Crawls 130point.com for eBay sold data. Zero eBay API calls. Builds `sold_comps` cache.

### Basic Usage
```bash
# Default: 100 cards
python3 worm_130point.py

# Longer run (background)
nohup python3 worm_130point.py --limit 1000 > /tmp/worm.log 2>&1 &

# Focus on one player
python3 worm_130point.py --player "Juan Soto"
```

### Worm Flags
```bash
--limit 100          # Max cards to crawl (default: 100)
--player "Name"      # Focus on a specific player
```

### What The Worm Does
1. Queries DB for cards lacking recent sold comps (48h TTL)
2. Prioritizes cards with SCP market rates (cross-validation value)
3. Then cards without SCP rates (discovery value)
4. Hits 130point backend API (plain HTTP POST, no Selenium)
5. Parses sold prices, dates, listing types from HTML response
6. Stores in `sold_comps` table
7. Rate: ~8 queries/min (under 130point's 10/min limit)

### Rate Limits
- 130point: 10 requests/minute, 429 = blocked 1 hour
- We enforce 7s between calls (safe margin)
- Capacity: ~14,000 queries/day

---

## Running Opportunity Finder (SCP-First / BIN)

### Basic Usage
```bash
# All 40 players, default filters (BIN + Auctions)
python3 find_opportunities.py --max-budget 200 --min-profit 5 --min-roi 20

# Specific players
python3 find_opportunities.py --max-budget 200 --min-profit 5 --players "Bobby Witt Jr,Mike Trout"

# Adjust SCP price range
python3 find_opportunities.py --max-budget 500 --min-scp-price 50 --max-scp-price 500

# Higher budget scan
python3 find_opportunities.py --max-budget 1000 --min-profit 20 --min-roi 15 --top-players 40
```

### Opportunity Finder Flags
```bash
--max-budget 200     # Max buy price (default: $200)
--min-profit 5       # Min profit after fees (default: $5)
--min-roi 20         # Min ROI % (default: 20)
--min-scp-price 20   # Min SCP price to consider (default: $20)
--max-scp-price 1000 # Max SCP price (default: $1000)
--players "A,B"      # Comma-separated player names (overrides --top-players)
--top-players 40     # Number of hot players by volume (default: 40)
```

### What The Opportunity Finder Does

1. Gets player list (from DB volume ranking or --players flag)
2. Scrapes SCP for each player's full catalog (Selenium/Firefox)
3. Filters by SCP price range and volume (rejects "rare", "1 sale/year", "2 sales/year")
4. Searches eBay for each variation (BIN + Auctions)
5. Validates: player + year + card# + parallel in title
6. Filters: junk listings, factory sets, reprints, wrong sets
7. BIN price floor: below 30% of SCP = hard reject (different product)
8. BIN suspicious flag: 30-50% of SCP = passes but flagged for review
9. Auctions: no price floor, no flagging (low bids are normal)
10. Calculates profit: SCP - buy price - 13% fees
11. Stores all opportunities in `opportunities` table with `listing_type`
12. Prints summary with [BIN] and [AUCTION] tags

### Output Format
```
[eBay 409/1074] Juan Soto 2025 Topps Update Mystical #MYS-14 [Green]
  SCP: $34.99
  Query: Juan Soto 2025 Topps Update Mystical #MYS-14 Green /99
  2 opportunities found!
    [BIN] $24.99 -> $34.99 = $6.75 profit (27% ROI)
    [AUCTION] $15.00 -> $34.99 = $18.04 profit (120% ROI)

RESULTS: 113 opportunities found (85 BIN, 28 Auction)
```

### Querying Results via API
```bash
# All opportunities
curl http://localhost:8000/api/opportunities

# BIN only
curl "http://localhost:8000/api/opportunities?listing_type=buy_it_now"

# Auctions only
curl http://localhost:8000/api/auctions

# With filters
curl "http://localhost:8000/api/opportunities?min_profit=20&min_roi=50&hide_flagged=true"

# Stats
curl http://localhost:8000/api/opportunities-stats
```

## Running on GitHub Actions (Off-Laptop)

Both pipelines can run on GitHub Actions. Requires RDS database.

### Setup
1. RDS is deployed: `cardpulse-db.ckvp9bhavaww.us-east-1.rds.amazonaws.com:5432` (legacy name, domain is ragnarokgamez.com)
2. Schema + migrations applied (001-023, tracked via `schema_migrations`)
3. GitHub secrets configured: `DATABASE_URL`, `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`
4. Trigger: Actions tab -> choose workflow -> Run workflow

### Scheduled Runs (Cron)
- **BIN Pipeline**: 2AM + 2PM ET daily (`0 6,18 * * *` UTC)
- **Auction Pipeline**: 5AM + 5PM ET daily (`0 9,21 * * *` UTC)
- **Card Data Pipeline** (sales / Trending): daily `0 11 * * *` UTC (~6–7 AM ET), `--skip-scp` on schedule
- **Daily Report**: 7PM ET daily (`0 23 * * *` UTC)
- **QA Pipeline**: on push/PR to main (CI)

**Card Data Pipeline** (`card-data-pipeline.yml`): **daily cron** `0 11 * * *` UTC (~6–7 AM ET) with **`--skip-scp`**. Still supports **Run workflow** manually.

All workflows also support manual `workflow_dispatch` triggers from the Actions UI.

### SPA “Market Movers” / Trending (`GET /api/trending`)

Backend: `backend/api/routes/trending.py`. A card appears only if **all** of the following hold:

| Rule | Detail |
|------|--------|
| Auth | JWT required (`require_auth`). |
| Data | At least one row in **`sales`** joined to **`cards`**. |
| Recency | `sales.sale_date >= now() - 30 days` (rolling window). |
| Price floor | Default query param `min_price=5.0`: **average** sale price in that window must be **≥ $5** (cards cheaper than that are dropped). |
| Limit | Up to `limit` groups (default 100; UI requests 200), ordered by sale count. |

**What does *not* feed Trending:** **`find_opportunities.py`** and the scheduled **Opportunity Pipeline** write **`opportunities`** (and related flow); they do **not** populate **`sales`** for this endpoint. **`sales`** are imported by **`python3 -m backend.run_pipeline_full`** (sold listings step — eBay Browse API, see table at top of this doc). On GitHub, that is the **Card Data Pipeline** workflow only. If RDS has old **`sales.sale_date`** values (all older than 30 days), Trending correctly returns **zero rows** even when **Opportunities** is full.

**Operational fix:** Merge the workflow with **daily cron**, or **Run workflow** once on **Card Data Pipeline** for immediate `sales`. Local: `python3 -m backend.run_pipeline_full --sport Baseball --top 20 --skip-scp`.

### Available Workflows
- **Opportunity Pipeline** (`.github/workflows/pipeline.yml`) -- BIN pipeline (`find_opportunities.py`); **scheduled**
- **Auction Pipeline** (`.github/workflows/auction-pipeline.yml`) -- Auction-first pipeline; **scheduled**
- **Card Data Pipeline** (`.github/workflows/card-data-pipeline.yml`) -- `backend.run_pipeline_full` (imports **`sales`**, active listings, trends); **daily cron + manual**
- **Daily Report** (`.github/workflows/daily-report.yml`) -- Operations report
- **QA Pipeline** (`.github/workflows/qa.yml`) -- 167 tests (unit + integration + QA + frontend build)

### Workflow Inputs
- `players`: comma-separated (default: top 40 by volume)
- `max_budget`: default 200
- `min_profit`: default 5
- `min_roi`: default 20
- `min_scp_price`: default 20
- `max_scp_price`: default 1000

### Inspect recent Actions runs (no UI scraping)

Read-only summary of conclusions + failed job steps via the GitHub API:

```bash
cd /path/to/TradingCards
# Option A: GitHub CLI (after: gh auth login)
python3 scripts/summarize_github_actions.py

# Option B: PAT with repo + Actions read
export GITHUB_TOKEN=ghp_...   # or fine-grained: Actions: Read
python3 scripts/summarize_github_actions.py --limit 20

# Only opportunity + auction workflows
python3 scripts/summarize_github_actions.py --workflow pipeline.yml auction-pipeline.yml
```

Default workflows scanned: `pipeline.yml`, `auction-pipeline.yml`, `card-data-pipeline.yml`, `daily-report.yml`. Failures list each job step that ended `failure` so you can open the run URL and expand the right step.

## Common Scenarios

### Resume After Interruption (DNS failure, etc.)
```bash
/usr/bin/python3 -m backend.run_pipeline_full --skip-discovery --sport Baseball --top 40
```
Skips discovery, deduplicates by ebay_item_id so already-imported players are fast.

### Daily Refresh (add new data, keep existing)
```bash
/usr/bin/python3 -m backend.run_pipeline_full --sport Baseball --top 40
```

### Quick Refresh (skip SCP, ~30 min)
```bash
/usr/bin/python3 -m backend.run_pipeline_full --sport Baseball --top 40 --skip-scp
```

### Full Reset (wipe everything, start clean)
```bash
/usr/bin/python3 -m backend.run_pipeline_full --fresh --sport Baseball --top 40
```

## Job Status

```bash
# Check all job statuses via API
curl http://localhost:8000/api/status

# Check specific job
curl http://localhost:8000/api/status/opportunity_finder

# Check via database
sudo -u postgres psql -d trading_cards -c "SELECT job_name, status, started_at, completed_at, items_processed, items_total FROM job_runs ORDER BY started_at DESC LIMIT 10;"
```

## Running Individual Steps

```bash
# 1. Discovery only
/usr/bin/python3 -m backend.discover_players --sport Baseball --limit 40

# 2. Import sold listings only
/usr/bin/python3 -m backend.scrapers.ebay_scraper

# 3. Active listings only
/usr/bin/python3 -m backend.collect_active_listings

# 4. Trends only
/usr/bin/python3 -m backend.calc_trends

# 5. SCP rates only
/usr/bin/python3 -m backend.collect_market_rates --skip-existing
```

## Starting Services

```bash
# PostgreSQL (after WSL restart)
sudo service postgresql start

# API server (port 8000)
cd /home/tweedledee101/TradingCards
nohup /usr/bin/python3 -m backend.api.run > /tmp/api.log 2>&1 &

# Frontend (port 3000)
cd /home/tweedledee101/TradingCards/frontend
nohup npm run dev > /tmp/frontend.log 2>&1 &
```

## Troubleshooting

### DNS failure in WSL (api.ebay.com won't resolve)
- Restart WSL: close all terminals, run `wsl --shutdown` from PowerShell, reopen
- Then restart services (PostgreSQL, API, frontend)
- Resume pipeline with `--skip-discovery`

### eBay API returns 0 results or errors
- Check daily limit: 5,000 calls/day resets at midnight Pacific
- Token expires every 2 hours (auto-refreshes)
- If 401 errors persist: check backend/.env credentials

### SCP scraper fails
- Firefox must run as user `tweedledee101` (not root)
- Auto-detects binary: `/usr/lib/firefox/firefox`, `/usr/bin/firefox-esr`, `/usr/bin/firefox`
- geckodriver at `/usr/local/bin/geckodriver` (v0.36.0)
- Page load timeout (30s) is EXPECTED - data still loads

### Database locked / queries hang
- Kill any running collection scripts first
- `sudo service postgresql restart`

### API server won't start
- `lsof -i :8000` to check, `kill $(pgrep -f 'backend.api.run')` to clear
- Check log: `cat /tmp/api.log`

## Data Flow

### Opportunity Pipeline (PRIMARY)
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
API --> Ragnarok Gaming UI
```

All jobs tracked via `job_runs` table. Check status:
```bash
curl http://localhost:8000/api/status
```

## Database Quick Reference

```bash
# Check counts
sudo -u postgres psql -d trading_cards -c "SELECT
  (SELECT COUNT(*) FROM cards) as cards,
  (SELECT COUNT(*) FROM sales) as sales,
  (SELECT COUNT(*) FROM active_listings) as active,
  (SELECT COUNT(*) FROM market_rates) as rates,
  (SELECT COUNT(*) FROM opportunities) as opportunities,
  (SELECT COUNT(DISTINCT player_name) FROM cards) as players;"

# Check opportunities by type
sudo -u postgres psql -d trading_cards -c "SELECT listing_type, COUNT(*), ROUND(AVG(profit)::numeric, 2) as avg_profit FROM opportunities GROUP BY listing_type;"

# Check flagged opportunities
sudo -u postgres psql -d trading_cards -c "SELECT COUNT(*) as flagged FROM opportunities WHERE flagged = true;"
```

## Running Daily Operations Report

Generates a comprehensive health check covering pipeline status, data freshness, data quality, and action items.

```bash
# Run locally
python3 daily_report.py

# Output goes to stdout + /tmp/daily-report.json
```

The report covers:
- **Pipeline health**: last run times, success/failure status from `job_runs` table
- **Database health**: row counts for all key tables
- **Data freshness**: latest timestamps, stale SCP cache entries, expired auctions
- **Data quality**: null SCP prices, negative profits, duplicate eBay IDs
- **QA flags**: summary of flagged opportunities by rule
- **Opportunity summary**: counts and avg profit by listing type
- **Trends**: 7-day opportunity history
- **Action items**: prioritized as critical/warning/info

Runs automatically at 7PM ET via GitHub Actions (`daily-report.yml`). JSON artifact uploaded for 7 days.

---

## Migrations Applied

| Migration | What |
|-----------|------|
| 001 | Base schema (cards, sales, active_listings, etc.) |
| 002 | PSA grading population |
| 003 | Variant columns + price benchmarks |
| 004 | Accuracy tracking + image_url |
| 005 | Sell-through metrics |
| 006 | Job runs (job tracking) |
| 007 | Error log (observability) |
| 008 | Retention cleanup function |
| 009 | Opportunities table |
| 009b | SCP URL, grade_9, psa_10, image_url on opportunities |
| 010 | listing_type on opportunities (BIN vs auction) |
| 011 | Auction fields (shipping, bid_count, end_time, scp_volume) |
| 012 | QA fields (qa_status, qa_flags, qa_reviewed_at) |
| 013 | SCP cache table (scp_cache with JSONB variants, 24h TTL) |
| 014 | Sold comps table (130point eBay sold data cache) |
| 015 | Price source tracking (scp, sold_comps, ebay_comps) |
| 016 | Scheduled bids table (snipe queue) |
| 017 | Business planner tables (business_goals, daily_snapshots, daily_plans, capital_transactions) |
| 018-023 | Additional schema refinements (see `backend/models/` for details) |

**Migration tracking**: `schema_migrations` table on both local + RDS. 24 migrations applied to both.

```bash
# Check migration status
python3 migrate.py --status --both

# Apply pending migrations to both databases
python3 migrate.py --both

# Apply to one target only
python3 migrate.py --local
python3 migrate.py --rds
```

**Rule**: When you add a new migration file to `backend/models/`, run `python3 migrate.py --both` to keep local and RDS in sync.
