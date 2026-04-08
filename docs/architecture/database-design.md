# Database Design

## Overview

PostgreSQL database storing trading card data, sales, market rates, opportunities, and operational state. All access via SQLAlchemy ORM. All commands use `sudo -u postgres psql` (peer authentication).

## Tables

### Core Data

**cards** -- Master card catalog (25,434 cards, 40 players)
- player_name, card_year, card_set, card_number, parallel, sport
- image_url (eBay thumbnail), **ungraded_price** (optional cache), **ebay_search_url**
- is_rookie, variant columns (grade_company, grade_value)
- Unique: (player_name, card_year, card_set, card_number, parallel, grade_company, grade_value) per migrations

**sales** -- Historical eBay sold data (42,313 sales)
- card_id (FK), sale_price, sale_date, ebay_item_id
- condition, graded, grade_company, grade_value

**active_listings** -- Current eBay listings (44,165 listings)
- card_id (FK), listing_price, listing_type (auction/buy_it_now)
- listing_title, listing_url, ebay_item_id
- end_time (deterministic expiry -- no re-query needed)

**market_rates** -- SCP prices (4,400 rates)
- card_id (FK), source ('sportscardspro')
- ungraded_price, grade_9_price, psa_10_price
- volume_text (e.g., "1 sale per day", "rare")
- scp_url (verification link)
- last_updated

### Opportunity Pipeline

**opportunities** -- Pipeline results (BIN + Auction)
- player_name, card_year, card_set, card_number, parallel
- scp_price, buy_price, profit, roi
- listing_type ('buy_it_now' or 'auction')
- ebay_url, ebay_item_id, image_url
- listing_image_urls (JSONB) — distinct eBay CDN URLs from Browse API (`image` + `thumbnailImages` + `additionalImages`) for gallery / vision-without-browser
- scp_url, grade_9_price, psa_10_price
- shipping, bid_count, end_time, scp_volume
- flagged (boolean), flag_reason
- qa_status ('pending'/'clean'/'flagged'/'critical')
- qa_flags (JSONB array of triggered QA rules)
- qa_reviewed_at (timestamp)
- verification_status (`pending` / `verified` / `conflict` / `skipped`) — cross-source listing check
- verification_detail (JSONB, nullable) — pipeline id, schema version, check results
- sport (VARCHAR) — pipeline context: Baseball / Basketball / Football (UI + API filter)
- scan_id, created_at

**pipeline_listing_skips** — High-signal BIN filter rejects (factory set, price floor, reprint, wrong set, economics) for audits; optional `audit_result` after `scripts/audit_pipeline_skips.py`.

### Portfolio

**inventory** -- User card ownership
- card_id (FK), purchase_date, purchase_price, purchase_source
- quantity, graded, grade_company, grade_value
- storage_location, status (owned/listed/sold), notes
- **ebay_item_id**, **ebay_listing_url**, **listing_ask_price**, **listed_at** (migration 027) — link desk/listing rows to live eBay offers; seller OAuth sync not implemented yet

**inventory_sales** -- Sales from inventory
- inventory_id (FK), sale_date, sale_price
- fees, shipping_cost, net_profit, roi_percentage

**watchlist** -- Price monitoring
- card_id (FK), target_price, alert_threshold, notes

### Analytics

**price_trends** -- Pre-computed daily metrics
- card_id (FK), trend_date
- avg_price, median_price, sales_count
- velocity_score, momentum_score, hotness_score
- price_change_7d, active_listings_count

**grading_population** -- PSA grading data (infrastructure ready)
- card_id (FK), psa_10_count, psa_9_count, total_graded
- psa_10_rate, date_recorded

**price_benchmarks** -- Card Ladder data (infrastructure ready)
- card_id (FK), source, current_price
- price_7d_ago, price_30d_ago, change_7d, change_30d
- velocity_rating, market_cap

### Operational

**scp_cache** -- Cached SCP Selenium search results (migration_013)
- player_name, card_year, card_number, search_query
- variants (JSONB array of variant dicts with parallel, ungraded, grade_9, psa_10, url, is_rc, is_auto, print_run)
- created_at (24h TTL -- cache_cutoff = now - 24h)
- Index: (lower(player_name), card_year, lower(card_number))

**sold_comps** -- 130point eBay sold data cache (migration_014)
- player_name, card_year, card_set, card_number, parallel
- sale_price, sale_type (auction/fixed), sale_date
- listing_title, source ('130point'), search_query
- created_at (48h TTL for worm re-crawl)
- Index: (lower(player_name), card_year, lower(card_number))
- Populated by background worm (`worm_130point.py`), zero eBay API calls

**job_runs** -- Pipeline job tracking
- job_name, status (running/completed/failed)
- started_at, completed_at
- items_processed, items_total
- parameters (JSONB), results_summary (JSONB) — may include **`vision_post_pipeline_queue_sample`** (bounded listing snapshots + **`reason`**) for post-pipeline multimodal follow-up; does not affect ingest

**error_log** -- Structured error logging (WARN+)
- timestamp, level, category, source, message
- context (JSONB), request_id, stack_trace

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
| … | See `backend/models/migration_*.sql` for 015–023 (price_source, scheduled_bids, business planner, auth, etc.) |
| 024 | `opportunities.listing_image_urls` JSONB (Browse API gallery URLs) |

## Key Indexes

- `cards(player_name, card_year, card_set, card_number)` -- dedup
- `sales(card_id, sale_date)` -- time-series queries
- `active_listings(card_id)` -- velocity calculations
- `opportunities(scan_id)` -- per-scan queries
- `opportunities(qa_status)` -- QA filtering
- `job_runs(job_name, started_at)` -- status lookups
- `scp_cache(lower(player_name), card_year, lower(card_number))` -- cache lookups
- `sold_comps(lower(player_name), card_year, lower(card_number))` -- sold comp lookups
- `sold_comps(created_at)` -- TTL pruning

## Data Retention

Managed by `run_retention_cleanup()` PostgreSQL function:
- Active listings: pruned when past end_date
- Error log: 30 days
- Job runs: 30 days
- Sales, market_rates, opportunities: retained per scan lifecycle

## Access Pattern

```
Scrapers/Pipelines --> SQLAlchemy ORM --> PostgreSQL
                                              |
FastAPI (Depends(get_db)) --> SQLAlchemy --> PostgreSQL
                                              |
React Frontend --> API --> JSON responses
```

All database access uses the repository pattern via SQLAlchemy ORM. No raw SQL in application code.

---

**Last Updated:** 2026-03-22 (Session 12)
