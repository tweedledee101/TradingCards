# Data Flow Diagrams

## Overview

Data flows through two pipelines (BIN and Auction). **GitHub Actions** also runs them on a schedule (see `PIPELINE-OPS.md`); **ADR-004** still applies to *data* refresh philosophy (no clock-based SCP re-scrape inside the app). **Multimodal / vision tools are post-pipeline only** — they never include or exclude listings during ingest; they consume bounded samples from `job_runs.results_summary` after a run completes.

## 1. BIN Opportunity Pipeline (SCP-First)

```
find_opportunities.py
    |
    v
[Player List] -- top 40 by eBay volume or --players flag
    |
    v
[SCP Selenium] -- 1 search per player --> full catalog (100 variations + prices + volume)
    |
    v
FILTER -- $20-$1000 SCP price range
       -- Volume filter (reject "rare", "1/year", "2/year")
    |
    v
[eBay Browse API] -- 1 search per variation --> active listings (BIN + Auctions)
    |
    v
VALIDATE -- player name + year + card# + parallel in title
         -- junk filter (you pick, mystery, repack, lots)
         -- factory set filter (complete set, montgomery, walmart/target)
         -- reprint filter (replica, project 2020, shoebox treasures)
         -- wrong set detection
         -- lot detection (multiple #, X & Y & Z, "N cards")
         -- BIN price floor (< 30% of SCP = reject)
    |
    v
CALCULATE -- SCP price - buy price - 13% fees = profit
    |
    v
STORE -- opportunities table (listing_type: buy_it_now or auction)
    |
    v
SAMPLE -- ``vision_post_pipeline_queue_sample`` on ``job_runs`` (cap ~50): BIN price-floor
         rejects + BIN rows still stored with ``flagged`` (30–50% of SCP) for tertiary visual check
    |
    v
[Auto-trigger Auction Pipeline via subprocess]
```

## 2. Auction Opportunity Pipeline (eBay-First)

```
find_auction_opportunities.py
    |
    v
[eBay Browse API] -- 110 queries (30 value-focused + 80 player-specific)
                  -- pagination up to 1000 results/query
                  -- auctions ending within 48h
                  -- category 261328 (Trading Card Singles)
    |
    v
DEDUP -- by eBay item ID across all queries
    |
    v
QUALITY FILTER -- year / card # / player required (title -> aspects -> full item details)
               -- player ID: MLB API + DB + eBay aspects fallback
               -- lot detection
               -- budget check (bid + shipping <= max_budget)
               -- bounded sample of Step 2 drops with images → ``vision_post_pipeline_queue_sample`` (post-pipeline Nova)
    |
    v
SCP VALIDATE -- DB lookup first (4,400 market rates)
              -- SCP cache (24h TTL, scp_cache table)
              -- Selenium fallback (card number verified in SCP URL)
              -- Pass 1: exact parallel match
              -- Pass 2A: strict text match (all SCP words in eBay title)
              -- Pass 2B: fuzzy word-overlap scoring (50%+ match)
              -- Pass 3: signal match (RC/Auto/Relic/print_run)
              -- Diagnostic logging on failures (first 30)
    |
    v
FALLBACK PRICING (when SCP fails)
              -- Tier 2: 130point sold comps (DB cache from worm, instant, free)
              -- Tier 3: eBay active BIN comps (1 API call, median of 3+ listings)
              -- All fallback-priced opportunities flagged for review
    |
    v
SANITY CHECK -- hybrid listing BIN < 50% of SCP = reject (seller disagrees)
    |
    v
SAMPLE -- ``vision_post_pipeline_queue_sample`` merges Step 2 metadata skips (with gallery) +
         no-pricing-after-fallback rows + BIN-sanity rejects (bounded per bucket) for post-run Nova / manual review
    |
    v
PROFIT CHECK -- SCP * 0.87 - (current bid + shipping) >= $10
    |
    v
STORE -- opportunities table (listing_type: auction, shipping, bid_count, end_time)
```

## 3. QA Validation (Post-Pipeline)

```
qa_opportunities.py (runs after pipeline, does NOT block it)
    |
    v
[Read opportunities from DB]
    |
    v
RULES -- extreme_roi (>500% = critical)
      -- high_roi (>300% = warning)
      -- price_ratio_10x
      -- no_scp_url
      -- card_number_mismatch (card# not in SCP URL)
      -- low_bid_high_scp
    |
    v
UPDATE -- qa_status (pending/clean/flagged/critical)
       -- qa_flags (JSONB array of triggered rules)
       -- qa_reviewed_at timestamp
```

## 4. Post-pipeline vision (optional)

```
find_opportunities.py / find_auction_opportunities.py complete
    |
    v
job_runs.results_summary.vision_post_pipeline_queue_sample  (BIN floor + flagged BIN; auction Step 2 skips + Step 3 queues; legacy no_scp_vision_queue_sample on auction)
    |
    v
scripts/vision_retry_scp_from_images.py  (--latest-bin-job | --latest-auction-job | --from-recent-opportunities N | --json)
    |
    v
Download CDN images -> Nova multimodal identity -> find_scp_match_for_vision (vision fallbacks; ingest uses find_scp_match_in_db)
    |
    v
Optional insert into ``opportunities`` on HIT (flagged + ``qa_flags``; ``--no-persist`` to skip)
    |
    v
Human review when vision disagrees with listing or SCP row
```

**When eBay and SCP (or the local SCP-backed catalog row) do not agree:** treat the situation as an **identity problem first**, not a pricing problem. Other signals — CE on the photo, Nova vision, 130point, manual SCP search — exist to **clarify what the listing actually is**. **Only after you are confident the eBay photos match that resolved card** should you treat comps (SCP DB, CE band, 130point) as “the same card” for a buy/sell decision.

Practical ladder (manual / dev tools; does not gate ingest):

1. **Collectors Edge (photo)** on the same CDN image — compare CE identity to the listing; if they diverge, use the photo + CE to hypothesize the true card before trusting title keywords.
2. **Local catalog lookup again** with CE-backed fields: `scripts/scp_lookup_from_ce_json.py` (artifact JSON + optional `--player` / `--year` / `--number` / `--parallel` / `--prefer-db-year`). This only queries PostgreSQL `cards` / `market_rates`; it does not scrape SCP live.
3. If there is still **no DB row**, **CE median/band/confidence** and **130point** / sold comps are for **spot-checking value** once identity is settled; using them while identity is still fuzzy compounds error. Automated scoring from those sources without a clear policy is out of scope here.

**Nova** path (`vision_retry_scp_from_images.py`) is image → identity → same DB lookup without CE; use whichever fits cost and insert difficulty.

Collectors Edge / other browser probes are separate dev workflows; they also do not gate core ingest.

## 5. API Request Flow

```
Client Request --> FastAPI Endpoint
    |
    +-- /api/opportunities --> query opportunities table (BIN + Auction)
    +-- /api/auctions --> query opportunities WHERE listing_type='auction'
    +-- /api/opportunities-stats --> aggregate profit/ROI/counts
    +-- /api/cards --> query cards with filters
    +-- /api/inventory --> portfolio with P&L
    +-- /api/watchlist --> price monitoring
    +-- /api/status --> job_runs table (pipeline health)
    +-- /api/errors --> error_log table (observability)
    |
    v
JSON Response --> React Frontend (Ragnarok Gaming theme)
```

## 6. Observability Flow

```
Any pipeline script
    |
    v
[AppLogger] -- stdout (human-readable)
            -- error_log table (WARN+ persisted, queryable)
            -- request_id tracking for API requests
    |
    v
[JobTracker] -- job_runs table
             -- start, progress, completion, failure
             -- parameters (JSONB), results_summary (JSONB)
    |
    v
/api/status --> UI and tooling check job state
/api/errors --> query error patterns
```

## Data Sources

| Source | Integration | Status |
|--------|------------|--------|
| eBay Browse API | REST API (OAuth, auto-refresh) | Working |
| SportsCardsPro | Selenium/Firefox (headless) | Working |
| MLB Stats API | REST API (free, no auth) | Working |
| 130point.com | HTTP POST (no auth, 10/min) | Working |
| PSA Population | Selenium (infrastructure ready) | Not yet active |
| Card Ladder | Selenium (infrastructure ready) | Not yet active |

## Data Retention

Managed by `run_retention_cleanup()` PostgreSQL function.

| Data | Retention | Rationale |
|------|-----------|-----------|
| Sold listings | Indefinite | Immutable historical data |
| Active listings | Until end_date | Deterministic expiry |
| SCP market rates | 24 hours | Prices update ~daily |
| Opportunities | Per scan | Replaced each pipeline run |
| Job runs | 30 days | Operational history |
| Error log | 30 days | Debugging window |

## 7. Background Data Worm

```
worm_130point.py (runs independently, no eBay API calls)
    |
    v
[Query DB] -- cards lacking recent sold comps (48h TTL)
           -- prioritize: cards with SCP rates, then without
    |
    v
[130point API] -- POST https://back.130point.com/sales/
               -- plain HTTP, returns HTML with eBay sold data
               -- 7s between calls (under 10/min limit)
    |
    v
[Parse] -- sale price, date, listing type (auction/fixed), title
    |
    v
STORE -- sold_comps table (player, year, card#, parallel, price)
      -- pipeline reads this as Tier 2 fallback pricing
```

---

**Last Updated:** 2026-03-27 — vision queues documented as post-pipeline only; scheduling note aligned with Actions.
