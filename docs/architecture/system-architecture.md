# System Architecture

## High-Level Overview

```
                    Data Sources
    ┌──────────┬──────────────┬───────────────┐
    │ eBay     │ SportsCards  │ MLB Stats     │
    │ Browse   │ Pro          │ API           │
    │ API      │ (Selenium)   │ (REST)        │
    └────┬─────┴──────┬───────┴───────┬───────┘
         │            │               │
         v            v               v
    ┌─────────────────────────────────────────┐
    │         Pipeline Layer                   │
    │                                          │
    │  find_opportunities.py (BIN, SCP-first)  │
    │       |                                  │
    │       └─> find_auction_opportunities.py  │
    │           (Auction, eBay-first)          │
    │       |                                  │
    │       └─> qa_opportunities.py            │
    │           (Background QA validation)     │
    └────────────────┬────────────────────────┘
                     │
                     v
    ┌─────────────────────────────────────────┐
    │         PostgreSQL Database               │
    │                                          │
    │  cards | sales | active_listings         │
    │  market_rates | opportunities            │
    │  inventory | watchlist | price_trends    │
    │  job_runs | error_log                    │
    └────────────────┬────────────────────────┘
                     │
                     v
    ┌─────────────────────────────────────────┐
    │         FastAPI REST API (port 8000)      │
    │                                          │
    │  /api/opportunities  /api/auctions       │
    │  /api/cards          /api/inventory       │
    │  /api/watchlist      /api/status          │
    │  /api/errors         /health              │
    └────────────────┬────────────────────────┘
                     │
                     v
    ┌─────────────────────────────────────────┐
    │    React Frontend (port 3000)            │
    │    Ragnarok Gaming dark theme            │
    │                                          │
    │  Trending | Opportunities | Card Detail  │
    │  Inventory | Watchlist                   │
    └─────────────────────────────────────────┘
```

## Component Details

### 1. Pipeline Layer

Two pipelines, unified under one command:

**BIN Pipeline** (`find_opportunities.py`) -- SCP-first
- Scrapes SCP for player catalog (100 variations/player)
- Filters by price range ($20-$1000) and volume
- Searches eBay for matching BIN + auction listings
- Validates: player + year + card# + parallel in title
- Filters: junk, factory sets, reprints, wrong sets, lots
- Calculates profit after 13% eBay fees
- Auto-triggers auction pipeline on completion

**Auction Pipeline** (`find_auction_opportunities.py`) -- eBay-first
- Searches eBay using 110 value-focused + player-specific queries with pagination
- Player identification via MLB Stats API (2,269 players) + period/accent normalization + eBay aspects fallback
- SCP validation: DB first, SCP cache (24h TTL), Selenium fallback with card number verification
- Multi-pass matching: exact -> strict text -> fuzzy word-overlap -> signal-based
- Fallback pricing: 130point sold comps (DB cache) -> eBay BIN comps (1 API call)
- BIN sanity check: hybrid listing BIN < 50% of SCP = reject
- Profit check: SCP * 0.87 - (bid + shipping) >= $10
- Diagnostic logging on no_scp match failures

**Background Worm** (`worm_130point.py`) -- data builder
- Crawls 130point.com for eBay sold data (plain HTTP, no Selenium)
- Builds `sold_comps` cache for pipeline fallback pricing
- Zero eBay API calls, ~14,000 queries/day capacity
- Prioritizes cards with SCP rates (cross-validation), then without (discovery)

**QA Validation** (`qa_opportunities.py`) -- post-pipeline
- Runs after pipeline, does not block it
- Flags: extreme_roi, high_roi, price_ratio_10x, card_number_mismatch
- Updates qa_status/qa_flags on opportunities

### 2. Data Sources

| Source | Method | Rate Limit | Status |
|--------|--------|-----------|--------|
| eBay Browse API | REST (OAuth) | 5,000/day | Working |
| SportsCardsPro | Selenium/Firefox | N/A (headless) | Working |
| MLB Stats API | REST (free) | None | Working |
| 130point.com | HTTP POST (no auth) | 10/min | Working |
| PSA Population | Selenium | N/A | Infrastructure ready |
| Card Ladder | Selenium | N/A | Infrastructure ready |

### 3. Database Layer

PostgreSQL 13+ with 13 migrations applied. Key tables:
- `cards` (25,434) -- master catalog
- `sales` (42,313) -- eBay sold data
- `active_listings` (44,165) -- current eBay listings
- `market_rates` (4,400) -- SCP prices (Ungraded/Grade 9/PSA 10)
- `scp_cache` -- SCP Selenium results cached 24h (migration_013)
- `sold_comps` -- 130point eBay sold data cache (migration_014)
- `opportunities` -- pipeline results with QA fields
- `job_runs` -- pipeline health tracking
- `error_log` -- structured error persistence

See [Database Design](./database-design.md) for full schema.

### 4. REST API

FastAPI with 18+ endpoints. Key routes:
- `/api/opportunities` -- BIN + Auction results with filters
- `/api/auctions` -- Auction-only results
- `/api/opportunities-stats` -- Aggregate metrics
- `/api/status` -- Job health from job_runs table
- `/api/errors` -- Error patterns from error_log

Features: pagination, filtering, sorting, CORS, Swagger docs at `/docs`.

### 5. Frontend

React 18 + Vite + Tailwind CSS.

**Theme**: Ragnarok Gaming dark (charcoal #0f1117 + ember orange #e8590c)
**Fonts**: Cinzel (display), Inter (body)

Pages:
- **Trending** (Home) -- top cards by volume/momentum
- **Opportunities** -- BIN + Auction tabs, Needs Review section, eBay buy links, SCP verify links
- **Card Detail** -- price history, grading data
- **Inventory** -- portfolio with P&L
- **Watchlist** -- price monitoring

### 6. Observability

- **Structured logging** (`backend/utils/logger.py`) -- WARN+ persisted to error_log table
- **Job tracking** (`backend/utils/job_tracker.py`) -- every pipeline run recorded
- **Request tracing** -- request_id on API calls
- **Data retention** -- self-managing via PostgreSQL function

## Deployment Architecture

### Current: Local Development (WSL Ubuntu)
- Backend: Python 3.9, PostgreSQL 13
- Frontend: Node.js 16, Vite dev server
- Selenium: Firefox + geckodriver

### Production (Planned)
- **Domain**: ragnarokgamez.com
- **ACM cert**: `arn:aws:acm:us-east-1:635601810497:certificate/8dda492b-b16f-45bf-965e-9268abaabe78`
- **Core app**: ECS (API + frontend, always running)
- **Worker**: ECS task (pipelines, spins up on demand)
- **Database**: RDS PostgreSQL (deployed: `cardpulse-db.ckvp9bhavaww.us-east-1.rds.amazonaws.com`)
- **Frontend**: CloudFront + S3
- **Refresh**: Demand-driven (ADR-004), no crons

### Already Deployed
- RDS PostgreSQL (free tier, schema + migrations 001-014)
- eBay compliance Lambda + API Gateway
- GitHub Actions workflows (BIN + Auction pipelines)

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Database | PostgreSQL | 13+ |
| Backend | Python | 3.9+ |
| API | FastAPI | 0.104.1 |
| ORM | SQLAlchemy | 2.0.23 |
| Scraping | Selenium + Firefox | 4.15.2 |
| Frontend | React | 18.2.0 |
| Build | Vite | 5.0.0 |
| Styling | Tailwind CSS | 3.3.6 |
| Testing | pytest | 7.4.3 |
| Hosting | AWS (ECS, RDS, CloudFront) | Planned |

## Security

- SQL injection prevention (SQLAlchemy ORM)
- CORS middleware configured
- Secrets in environment variables (.env gitignored)
- eBay OAuth token auto-refresh
- No user auth yet (solo user, pre-launch)

## Key Architectural Decisions

- [ADR-001](decisions/ADR-001-postgresql-database.md) -- PostgreSQL as primary database
- [ADR-002](decisions/ADR-002-ebay-primary-source.md) -- eBay as primary data source
- [ADR-003](decisions/ADR-003-testing-strategy.md) -- pytest testing strategy
- [ADR-004](decisions/ADR-004-demand-driven-refresh.md) -- Demand-driven refresh (no crons)

---

**Last Updated:** 2026-03-22 (Session 12)
