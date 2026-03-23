# Trading Card Platform - Project Structure

## Directory Organization

```
TradingCards/
├── backend/              # Python backend (data pipeline, API, scrapers)
│   ├── api/             # FastAPI REST API
│   │   ├── routes/      # API endpoint definitions
│   │   ├── main.py      # API application setup
│   │   └── run.py       # API server entry point
│   ├── config/          # Configuration management
│   │   └── settings.py  # Environment and app settings
│   ├── models/          # Database schema and migrations
│   │   ├── schema.sql   # Main database schema (9 tables)
│   │   └── migration_*.sql  # Database migrations
│   ├── scrapers/        # Data collection scrapers
│   │   ├── ebay_scraper.py           # eBay Browse API scraper
│   │   ├── sportscardspro_scraper.py # SportsCardsPro market rates (Selenium/Firefox)
│   │   ├── psa_scraper.py            # PSA population scraper
│   │   └── cardladder_scraper.py     # Card Ladder price scraper
│   ├── services/        # Business logic services
│   │   ├── data_pipeline.py          # Data orchestration
│   │   ├── trend_calculator.py       # Hotness/momentum algorithms
│   │   ├── opportunity_analyzer.py   # Arbitrage detection
│   │   ├── scheduler.py              # Automated task scheduling
│   │   └── report_generator.py       # Daily report generation
│   ├── utils/           # Shared utilities
│   │   ├── database.py          # Database connection management
│   │   ├── player_extractor.py  # Player name parsing
│   │   └── token_manager.py     # eBay OAuth token management
│   └── requirements.txt # Python dependencies
├── frontend/            # React frontend (Vite + Tailwind CSS)
│   ├── src/
│   │   ├── api/         # API client functions
│   │   ├── components/  # Reusable React components
│   │   ├── pages/       # Page-level components
│   │   ├── App.jsx      # Main application component
│   │   └── main.jsx     # Application entry point
│   ├── package.json     # Node.js dependencies
│   └── vite.config.js   # Vite build configuration
├── acquisition/         # Facebook Marketplace integration
│   └── facebook_marketplace/
│       └── novaact_intake.py  # NovaAct scraper integration
├── aws/                 # AWS deployment infrastructure
│   ├── cloudformation/  # CloudFormation templates
│   │   └── ebay-compliance-lambda.yaml
│   └── lambda/          # Lambda function code
│       └── ebay_compliance.py
├── config/              # Application configuration
│   └── targets.yaml     # Target players list (25 players)
├── docs/                # Comprehensive documentation
│   ├── architecture/    # System design documents
│   │   ├── system-architecture.md
│   │   ├── database-design.md
│   │   ├── diagrams/    # Architecture diagrams
│   │   └── decisions/   # Architecture decision records
│   ├── setup/           # Installation guides
│   └── *.md             # Feature guides and references
├── tests/               # Test suite
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── fixtures/        # Test data fixtures
└── reports/             # Generated daily reports (CSV, TXT)
```

## Core Components

### 1. Opportunity Pipelines
**BIN Pipeline**: `find_opportunities.py` (SCP-first, then eBay BIN search)
**Auction Pipeline**: `find_auction_opportunities.py` (eBay-first, then SCP validation)
**Unified**: `find_opportunities.py --max-budget 200` runs BIN then auto-runs auction via subprocess

**Auction Pipeline Steps**:
1. Search eBay for auctions ending within N hours (110 queries: 30 value-focused + 80 player-specific, with pagination up to 1000/query)
2. Quality filter: card number + player (period-normalized, accent-stripped) + not junk + within budget
3. SCP validation: DB lookup first, then SCP cache (24h TTL), then Selenium fallback
4. Multi-pass SCP matching: Pass 1 exact parallel, Pass 2A strict text match, Pass 2B fuzzy word-overlap scoring, Pass 3 signal match (RC/Auto/Relic/print_run)
5. BIN sanity check: if hybrid listing's BIN price < 50% of SCP, reject (seller disagrees with SCP)
6. Fallback pricing: 130point sold comps (DB cache) -> eBay BIN comps (1 API call) when SCP fails
7. Profit check: SCP * 0.87 - (current_bid + shipping) >= min_profit
8. Store in DB with listing_type='auction'
9. Diagnostic logging: first 30 no_scp cards show variants found, pass attempts, and failure reason

**Key Services**:
- `data_pipeline.py`: BIN orchestration
- `opportunity_analyzer.py`: BIN arbitrage detection
- `find_auction_opportunities.py`: Auction pipeline (standalone)
- `qa_opportunities.py`: Post-pipeline QA validation

### 2. Scrapers
**Location**: `backend/scrapers/`

Data collection from external sources:
- **eBay Scraper**: Browse API for sold listings and active listings (WORKING)
  - 80+ parallel patterns (Lime Green, Blue Foil Pattern II, Raywave Refractor, Silver Refractor, wave variants, etc.)
  - Insert set detection (Master Of The Game, 1986 Retro, Milestone, National Chicle, Decade's Next, etc.)
  - 79 card sets including 16 Leaf sub-sets
  - Hybrid auction+BIN detection: uses `currentBidPrice` for actual bid, stores BIN price separately
  - Player aspect extraction: accepts Player, Player/Athlete, Athlete, Player Name fields
- **SportsCardsPro Scraper**: Selenium/Firefox for Ungraded/Grade 9/PSA 10 market rates (WORKING)
- **PSA Scraper**: Selenium-based scraper for grading population data (untested)
- **Card Ladder Scraper**: Selenium-based scraper for price benchmarks (untested)

**SportsCardsPro URL Pattern**: `/search-products?q={query}&type=prices`
**SportsCardsPro Table Classes**: `used_price` (Ungraded), `cib_price` (Grade 9), `new_price` (PSA 10)

**Integration Pattern**: Scrapers → Database → API → Frontend

### 3. REST API
**Location**: `backend/api/`

FastAPI-based REST API with 20+ endpoints:
- `/api/opportunities` - BIN opportunities (default BIN-only, `listing_type=all` for both)
- `/api/auctions` - Auction opportunities (auto-filters expired auctions by default)
- `/api/opportunities-stats` - Quick stats
- `/api/cards` - Card listings with filtering/sorting
- `/api/inventory` - Portfolio management
- `/api/watchlist` - Price monitoring
- `/api/status` - Job tracker status
- `/api/webhooks/novaact/*` - Scraper data intake

**Features**: Advanced filtering, pagination, sorting, expired auction filtering

### 4. Frontend Dashboard
**Location**: `frontend/src/`

React SPA with Vite + Tailwind CSS:
- **Theme**: Ragnarok Gaming dark theme (charcoal #0f1117 + ember orange #e8590c)
- **Fonts**: Cinzel for display headings, Inter for body
- **Pages**: Trending (Home), Opportunities, Card Details, Inventory, Watchlist
- **Components**: CardTable, FilterPanel, PriceChart, OpportunityCard
- **State Management**: React hooks + localStorage
- **Styling**: Tailwind CSS utility classes

### 6. Job Tracking
**Location**: `backend/utils/job_tracker.py`

Runtime state management for all background jobs:
- Every script records start, progress, completion, and failure
- API exposes `/api/status` for UI and tooling to check job state
- Designed for AWS migration: same table in RDS, or swap to DynamoDB/Step Functions
- No polling, no process checks -- state lives in the database

**Database Table**: `job_runs` (migration_006_job_runs.sql)
- job_name, status (running/completed/failed), started_at, completed_at
- items_processed, items_total (progress tracking)
- parameters (JSONB -- what args was it called with)
- results_summary (JSONB -- key metrics from the run)

### 7. Database Schema
**Location**: `backend/models/schema.sql`

PostgreSQL database with 11+ tables:
- `cards` - Core card data
- `sales` - Individual sale records
- `active_listings` - Current eBay listings
- `market_rates` - SCP prices (Ungraded/Grade 9/PSA 10)
- `scp_cache` - Cached SCP Selenium search results (24h TTL, migration_013)
- `sold_comps` - 130point eBay sold data cache (48h TTL, migration_014)
- `opportunities` - Pipeline-discovered arbitrage (BIN + auction)
- `scheduled_bids` - Snipe queue (max_bid, snipe_seconds, end_time, status)
- `schema_migrations` - Migration tracking (filename, applied_at)
- `job_runs` - Background job state tracking
- `error_log` - Runtime error/event log
- `inventory` - User portfolio tracking
- `watchlist` - Price monitoring
- `grading_population` - PSA grading data
- `price_benchmarks` - Card Ladder benchmarks

### 8. Data Refresh Architecture (ADR-004)
**Pattern**: Demand-driven refresh with deterministic staleness. No crons.

Core principle: the data knows when it's stale.
- Active listings have end dates -- expiry is deterministic, no API call needed
- Sold listings are immutable -- never re-fetch
- SCP prices move slowly -- trust for 24 hours
- Opportunities are only stale when underlying data expires

Refresh triggers:
- User requests data and cache is older than staleness threshold
- Valid opportunity pool drops below threshold (too many listings expired)
- Manual trigger via API (admin use)

NEVER refresh because a clock says so. Every API call and scrape must produce value.

See: `docs/architecture/decisions/ADR-004-demand-driven-refresh.md`

### 9. Database Migration Runner
**Location**: `migrate.py`

Tracks and applies database migrations to any target database:
- `schema_migrations` table records which migration files have been applied
- `python3 migrate.py --both`: applies pending to local + RDS
- `python3 migrate.py --status --both`: shows applied vs pending per target
- `python3 migrate.py --local` / `--rds`: target one database
- Handles already-existing objects gracefully (records as applied)
- Rule: if you update cloud DB structurally, run `--both` to keep local in sync

## Architectural Patterns

### Data Flow Architecture
```
BIN Pipeline:  SCP-first → eBay search per variation → profit check → DB
Auction Pipeline: eBay auction search → quality filter → SCP validation (cache + Selenium) → profit check → DB
Both: → API → Frontend (Opportunities page, BIN + Auction sections)
```

### Service Layer Pattern
Business logic separated into focused services:
- `data_pipeline.py` - Orchestration
- `trend_calculator.py` - Analytics
- `opportunity_analyzer.py` - Decision logic
- `report_generator.py` - Output formatting

### Repository Pattern
Database access abstracted through SQLAlchemy ORM:
- Models define schema
- Services use ORM for queries
- Migrations manage schema changes

### Webhook Integration Pattern
External scrapers (NovaAct) push data via webhooks:
1. Scraper collects data
2. POST to `/api/webhooks/novaact/{source}`
3. API validates and stores data
4. Frontend fetches via GET endpoints

## Configuration Management

### Environment Variables
**Location**: `backend/.env`

Required configuration:
- `DATABASE_URL` - PostgreSQL connection string
- `EBAY_APP_ID` - eBay API credentials
- `EBAY_CERT_ID` - eBay API credentials
- `EBAY_DEV_ID` - eBay API credentials

### Target Configuration
**Location**: `config/targets.yaml`

YAML-based player targeting:
```yaml
players:
  - name: "Victor Wembanyama"
    sport: "Basketball"
    queries:
      - "{name} prizm"
      - "{name} select"
```

## Deployment Architecture

### Local Development
- Backend: Python 3.9+ with virtual environment
- Frontend: Node.js 16+ with Vite dev server
- Database: PostgreSQL 13+

### Production (Planned)
- **Domain**: ragnarokgamez.com
- **Backend**: AWS ECS (Docker containers)
- **Frontend**: AWS CloudFront + S3
- **Database**: AWS RDS (PostgreSQL) -- deployed: `cardpulse-db.ckvp9bhavaww.us-east-1.rds.amazonaws.com` (legacy name)
- **ACM cert**: `arn:aws:acm:us-east-1:635601810497:certificate/8dda492b-b16f-45bf-965e-9268abaabe78` (ragnarokgamez.com + *.ragnarokgamez.com)
- **Scrapers**: AWS ECS Tasks or Lambda (demand-driven, NOT scheduled)
- **IaC**: CloudFormation templates
- **Refresh**: Demand-driven with caching (ADR-004), no crons
