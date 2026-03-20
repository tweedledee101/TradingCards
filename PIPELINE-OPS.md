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

## Running Opportunity Finder

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

The pipeline can run on GitHub Actions instead of the local laptop. Requires RDS database.

### Setup
1. Deploy RDS: `aws cloudformation create-stack --stack-name cardpulse-rds --template-body file://aws/cloudformation/rds.yaml`
2. Migrate data: `bash aws/migrate-to-rds.sh`
3. Set GitHub secrets: `DATABASE_URL`, `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`
4. Trigger: Actions tab -> "Run Pipeline" -> Run workflow

### Workflow Inputs
- `players`: comma-separated (default: top 40 by volume)
- `max_budget`: default 200
- `min_profit`: default 5
- `min_roi`: default 20
- `min_scp_price`: default 20
- `max_scp_price`: default 1000

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
