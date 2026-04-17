# Session Prompt -- Trading Card Platform (Ragnarok Gaming)

## Start Here

Read these files in order before doing anything:
1. `STATUS.md` -- current state (honest assessment, updated this session)
2. `README.md` -- project overview
3. `.amazonq/rules/memory-bank/structure.md` -- codebase layout
4. `.amazonq/rules/memory-bank/product.md` -- what we're building
5. `PIPELINE-OPS.md` -- how to run things

## What This Project Is

A data-driven arbitrage opportunity finder for trading card dealers. Finds cards listed below market value on eBay, validates pricing against SportsCardsPro (SCP), and surfaces profitable flips. Two pipelines: BIN (buy-it-now) and Auction.

## Success Criteria (Not Met Yet)

- **~1,000 opportunities** (BIN + Auction combined) that are **accurately identified cards**
- Currently at **~150 opportunities**, and **many are wrong matches** (wrong card, wrong parallel, wrong grade tier)
- The tool is not trustworthy enough to make buying decisions from

## What Actually Works (Prod / RDS)

- **Auction pipeline**: runs 2x/day via GitHub Actions, finds 15-32 opps per run, writes to RDS
- **BIN pipeline**: FIXED -- uses SCP cache (no Selenium), hardcoded 40 players (no Browse discovery), 500 variations/shard cap. Will resume on next cron (2AM/2PM ET).
- **SCP cache**: 12,806 cached SCP lookups (1,352 unique players, 43K+ variants)
- **sold_comps**: 446+ rows (worm seeding from opportunities, 130point rate limited)
- **CE API direct**: Collectors Edge `cards.identifyByImage` tRPC endpoint -- 30s per card, structured JSON, no browser needed. Integrated into `collectors_edge_photo_run.py` (API-first, Playwright fallback)
- **Full-size image URLs**: `listing_image_urls` on opportunities now sorted so s-l1600.jpg comes first (critical for CE accuracy)
- **GitHub Actions CI**: QA pipeline (221 tests pass), auction pipeline (scheduled), BIN pipeline (sharded 8-way, SCP cache mode)
- **Frontend**: React SPA at ragnarokgamez.com with Cognito auth, Opportunities page, Business Dashboard
- **API**: FastAPI Lambda at api.ragnarokgamez.com
- **Database**: RDS PostgreSQL, 30 migrations applied

## What Is Broken (Prod / RDS)

- **Card data pipeline never ran on RDS**: `cards`=1, `sales`=0, `active_listings`=0. Trending page is empty.
- **market_rates: 0 rows on RDS** -- pipeline uses scp_cache only, no persistent pricing
- **52% of opportunities are flagged** -- 76 of 146 have `flagged=true`
- **Identity accuracy is poor**: CE verification showed wrong parallel IDs, wrong player matches, grade mismatches
- **147,060 error_log entries** -- mostly eBay Browse HTTP errors and discovery failures
- **inventory, scheduled_bids: empty** -- no user data entered

## The Core Problem (Why We're Stuck at 150 Instead of 1,000)

Three compounding issues:

### 1. Coverage Too Narrow
- Only 40 players scanned
- ~1,665 SCP variations searched per BIN run
- eBay has 1.1M+ listings for 2025 Topps Chrome alone
- We're searching a tiny slice of the market

### 2. Identity Matching Is Wrong Too Often
- Text-only matching (eBay title -> SCP catalog) misidentifies cards
- Sellers use vague titles, rely on images to sell
- Grade mismatch: graded listings compared to ungraded SCP prices
- Parallel mismatch: "Magenta Speckle" matched to "Magenta"
- 33,110 economics rejects in `pipeline_listing_skips` -- many are wrong matches, not genuinely unprofitable cards
- 14,500 skips where buy > 3x SCP -- strong signal of wrong card match

### 3. No Visual Verification in Pipeline
- CE can identify cards from images (player, year, set, variant, print run, pricing)
- CE API direct call works: 30s, structured JSON, no browser
- But CE is post-pipeline only -- not integrated into the actual opportunity flow
- CE catches both false positives (wrong matches we show) and false negatives (value we miss)

## What We Proved This Session

1. **Web search (ddgs/primp)**: Works but doesn't beat Browse API for volume. DDG returns 6-20 results vs Browse's 200+/query. Not the path forward for listing discovery.

2. **CE API direct**: The breakthrough. `POST collectorsedgeai.com/api/trpc/cards.identifyByImage` with base64 image returns structured JSON in ~30s. No Playwright needed. Returns: cardName, player, year, set, variant, printRun, pricing (low/median/high with methodology), imageDescription, condition, rarity. Integrated into existing `collectors_edge_photo_run.py` with `--no-api` flag for Playwright fallback.

3. **Full-size images matter**: CE with 225px thumbnails misidentified cards or got stuck on variant picker. With 1600px images, identification improved significantly. Fixed `opportunity_image_urls.py` to sort s-l1600 first.

4. **Funnel analysis**: 33,110 of 41,544 pipeline skips are "economics_below_threshold". Of those, 32,059 have buy > SCP (wrong match signal). 31,141 skips are on cards with SCP < $20 (wasted effort). The pipeline is spending most of its time on cheap cards that will never be profitable.

5. **CE batch results (20 cards)**: 2 cards where CE found 2x+ more value than SCP (hidden opportunities), 10 where CE priced much lower (possible wrong SCP matches or CE underpricing), 1 wrong player match by CE, 7 roughly aligned. CE is not perfect but catches real problems.

## Architecture (What Exists)

```
Pipeline Layer:
  find_opportunities.py          -- BIN pipeline (SCP-first, sharded in CI)
  find_auction_opportunities.py  -- Auction pipeline (eBay-first)
  qa_opportunities.py            -- Post-pipeline QA rules
  worm_130point.py               -- Background sold comps builder
  daily_report.py                -- Operations health check

CE Verification (dev tooling, not in pipeline yet):
  scripts/dev/collectors_edge_photo_run.py  -- API-first + Playwright fallback
  scripts/dev/collectors_edge_explore.py    -- Cohort sampling
  scripts/ce_verify_skips.py               -- Verify economics rejects
  backend/utils/collectors_edge_result.py  -- Parse CE responses (API + HTML)
  backend/utils/ce_scp_identity.py         -- Map CE identity to SCP lookup
  backend/utils/collectors_edge_qa_merge.py -- Merge CE flags into opportunities

API + Frontend:
  backend/api/                    -- FastAPI (Lambda on api.ragnarokgamez.com)
  frontend/                       -- React SPA (CloudFront on ragnarokgamez.com)

Infrastructure:
  .github/workflows/              -- 6 workflows (BIN, Auction, Card Data, Daily Report, QA, Nova Act)
  aws/                            -- CloudFormation, deploy scripts
  migrate.py                      -- Schema migrations (30 applied, local + RDS + dev)
```

## Next Steps (Priority Order)

### 1. Verify Pipeline Results (morning of April 16)
- 2AM cron runs with accuracy fix + volume-targeted search + 7-day auction window
- Check ragnarokgamez.com -- opportunities should be more accurate but VERIFY before buying
- Spot-check 5-10 opportunities against SCP product pages (correct parallel? correct price?)
- Check GitHub Actions logs for liquid card count and hit rate

### 2. Keep Running SCP Volume Worm
- `/usr/bin/python3 worm_scp_volume.py --limit 2000` (round-robins across all players)
- More liquid cards = more targeted eBay searches = more real opportunities
- Currently 56 liquid cards indexed, target 200+

### 3. Risk Filters (next code iteration)
- **Trend direction**: declining prices = don't buy. Use SCP sold dates/prices (worm captures these).
- **Supply/competition**: eBay `total` field shows active listing count. High supply = slow sell.
- **Price freshness**: reject cards where last sale was 3+ months ago.
- **True sell-through**: sales per week / active listings = actual turnover rate.
- **2026 volatility**: new products need higher margin buffer.

### 4. Apply for eBay Compatible Application
- https://developer.ebay.com/my/keys
- Free, 3-5 days, 50K+ calls/day (currently 5K)
- With volume-targeted search at 210x efficiency, 50K calls = massive coverage

### 5. Spike Detection
- Daily eBay Browse `total` per player (120 calls)
- Compare day-over-day: big jump = something happened (call-up, trade, injury)
- Flag spiking players for priority SCP + 130point scraping
- Feed into pipeline as high-priority search targets

## Key Files Changed This Session

- `.github/workflows/pipeline.yml` -- BIN pipeline overhaul: hardcoded 40 players (no Browse discovery), `--use-scp-cache` (no Selenium), `--max-ebay-variations 500` per shard, removed Firefox/geckodriver from BIN shards
- `worm_130point.py` -- Fixed `--opportunities` SQL error (ORDER BY column not in SELECT DISTINCT)
- `backend/utils/collectors_edge_result.py` -- Added `call_ce_identify_api()` and `ce_extracted_from_api_json()` for direct tRPC API calls (session 84)
- `backend/utils/opportunity_image_urls.py` -- Sort URLs so s-l1600 (full-size) comes first (session 84)
- `scripts/dev/collectors_edge_photo_run.py` -- API-first flow in `run_flow()` and `run_flow_db_sequence()`, `--no-api` flag (session 84)
- `scripts/ce_verify_skips.py` -- NEW: verify economics rejects via CE (session 84)
- `backend/services/web_search_discovery.py` -- NEW: ddgs web search adapter (experimental, session 83)
- `tests/unit/test_web_search_discovery.py` -- NEW: tests for web search (need Python 3.12, session 83)

## Temp/Measurement Files to Clean Up

Root directory has many one-off measurement scripts from this session:
`measure_*.py`, `parse_ce_*.py`, `test_*.py` (ddgs/primp/brave), `check_skip_images.py`, `snapshot_*.py`, `intercept_ce_api.py`, `_check_*.py`, `_debug_*.py`, `_test_*.py`, `_verify_*.py`

## User Preferences
- No emojis without asking
- No flattery, direct communication
- $10 minimum profit non-negotiable
- QA does NOT block pipeline
- Wants 1,000 accurate opportunities, not 150 questionable ones
- Frustrated with identity accuracy -- CE is the path forward
- WSL Ubuntu, Python 3.8 (system) + 3.12 (ddgs/playwright/CE)
- `sudo -u postgres psql` for local DB
- RDS is primary: `cardpulse-db.ckvp9bhavaww.us-east-1.rds.amazonaws.com`
