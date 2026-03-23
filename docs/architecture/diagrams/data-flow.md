# Data Flow Diagrams

## Overview

Data flows through two pipelines (BIN and Auction), both triggered on demand -- no cron jobs. See ADR-004 for the demand-driven refresh philosophy.

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
QUALITY FILTER -- card number required (title -> aspects -> full item details)
               -- player ID: MLB API (2,269) + period/accent normalization + eBay aspects fallback
               -- lot detection
               -- budget check (bid + shipping <= max_budget)
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

## 4. API Request Flow

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

## 5. Observability Flow

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

## 6. Background Data Worm

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

**Last Updated:** 2026-03-22 (Session 12)
