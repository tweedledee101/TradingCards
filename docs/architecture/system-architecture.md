# System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Data Sources                            │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│  eBay    │ Facebook │  COMC    │ Whatnot  │    Mercari      │
│  API     │Marketplace│  Web    │   Web    │     Web         │
│  ✅      │   ✅     │   ✅     │   ✅     │     ✅          │
└────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬────────────┘
     │          │          │          │          │
     ▼          ▼          ▼          ▼          ▼
┌────────────────────────────────────────────────────────────┐
│              Multi-Platform Sourcing Layer                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  eBay    │  │ Facebook │  │  COMC    │  │ Whatnot  │  │
│  │ Scraper  │  │  Search  │  │  Search  │  │  Search  │  │
│  │   ✅     │  │   ✅     │  │   ✅     │  │   ✅     │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│  ┌──────────┐  ┌──────────┐                               │
│  │ Mercari  │  │130point  │                               │
│  │  Search  │  │ Scraper  │                               │
│  │   ✅     │  │   ✅     │                               │
│  └──────────┘  └──────────┘                               │
└────────┬───────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                   PostgreSQL Database                        │
│  ┌──────┐  ┌───────┐  ┌──────────┐  ┌───────────┐         │
│  │cards │  │ sales │  │ listings │  │ inventory │         │
│  │  ✅  │  │  ✅   │  │   ✅     │  │    ✅     │         │
│  │+image│  │       │  │          │  │           │         │
│  │+card#│  │       │  │          │  │           │         │
│  │+paral│  │       │  │          │  │           │         │
│  │+grade│  │       │  │          │  │           │         │
│  └──────┘  └───────┘  └──────────┘  └───────────┘         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │  trends  │  │watchlist │  │inv_sales │                 │
│  │   ✅     │  │   ✅     │  │   ✅     │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│              Arbitrage Detection Engine                      │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │  Multi-Platform│  │  Arbitrage     │  │  ROI         │ │
│  │  Sourcing      │  │  Calculator    │  │  Analyzer    │ │
│  │     ✅         │  │     ✅         │  │     ✅       │ │
│  └────────────────┘  └────────────────┘  └──────────────┘ │
│  ┌────────────────┐  ┌────────────────┐                   │
│  │  Variant       │  │  Visual        │                   │
│  │  Matcher       │  │  Identifier    │                   │
│  │     ✅         │  │     ✅         │                   │
│  └────────────────┘  └────────────────┘                   │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                    REST API Layer (FastAPI)                  │
│  ┌────────────────────────────────────────────────────┐    │
│  │  19 Endpoints - ✅ Complete                        │    │
│  │  - GET /api/trending (filtering, sorting)         │    │
│  │  - GET /api/trending/rookies                      │    │
│  │  - GET /api/stats                                 │    │
│  │  - GET /api/cards/{id} (price history)           │    │
│  │  - GET /api/cards (pagination)                    │    │
│  │  - GET /api/sourcing/{id} (multi-platform) ✨    │    │
│  │  - POST /api/inventory                            │    │
│  │  - GET /api/inventory (by status)                 │    │
│  │  - GET /api/inventory/stats                       │    │
│  │  - POST /api/inventory/sales                      │    │
│  │  - GET /api/inventory/{id}                        │    │
│  │  - POST /api/watchlist                            │    │
│  │  - GET /api/watchlist                             │    │
│  │  - DELETE /api/watchlist/{id}                     │    │
│  │  - GET /api/watchlist/alerts                      │    │
│  │  - GET /health                                    │    │
│  └────────────────────────────────────────────────────┘    │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│              Frontend Dashboard (React + Vite)               │
│  ┌────────────────────────────────────────────────────┐    │
│  │  ✅ Complete                                       │    │
│  │  - Trending cards with card images ✨             │    │
│  │  - Multi-platform sourcing links ✨               │    │
│  │  - Variant differentiation (card #, parallel) ✨  │    │
│  │  - Card detail pages with price charts            │    │
│  │  - Profit calculator with eBay fees               │    │
│  │  - Inventory dashboard with P&L tracking          │    │
│  │  - Watchlist with price alerts                    │    │
│  │  - Navigation between all features                │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Scraper Layer

**Purpose:** Collect raw data from multiple sources

**Components:**
- **eBay Scraper** ✅ - Sold listings and active listings via Browse API
- **PSA Scraper** ⏳ - Population reports via web scraping (Phase 2)
- **Card Ladder Scraper** ⏳ - Price benchmarks (Phase 2)
- **Terapeak Scraper** ⏳ - Sell-through rates (Phase 2)
- **Social Scraper** ⏳ - Twitter/Reddit mentions (Phase 2)
- **Release Calendar Scraper** ⏳ - Topps/Panini releases (Phase 2)

**Schedule:**
- eBay: Daily at 2 AM EST (via APScheduler)
- PSA: Weekly on Sundays (planned)
- Social: Every 4 hours (planned)

**Technology:** Python, requests, BeautifulSoup, Selenium

**Features:**
- Title parsing (player, year, rookie status, grading)
- Duplicate detection by eBay item ID
- Error handling and retry logic
- Target list configuration (YAML)
- Daily report generation (CSV + text)

### 2. Database Layer

**Purpose:** Persistent storage for all data

**Technology:** PostgreSQL 14+

**Tables (9 total, 5 more planned):**
- `cards` ✅ - Master card catalog
- `sales` ✅ - Historical transactions
- `active_listings` ✅ - Current market supply (with title/URL)
- `price_trends` ✅ - Pre-computed metrics (with momentum_score)
- `inventory` ✅ - User card ownership
- `inventory_sales` ✅ - Sales from inventory
- `watchlist` ✅ - Price monitoring
- `psa_population` ⏳ - Grading data (table exists, scraper needed - Phase 2)
- `social_signals` ⏳ - Social media data (table exists, scrapers needed - Phase 2)
- `sell_through_rates` ⏳ - Terapeak data (Phase 2)
- `price_benchmarks` ⏳ - Card Ladder data (Phase 2)
- `release_calendar` ⏳ - Product releases (Phase 2)
- `buy_recommendations` ⏳ - Optimal entry prices (Phase 3)
- `sell_strategies` ⏳ - Exit recommendations (Phase 3)

See [Database Design](./database-design.md) for detailed schema.

### 3. Trend Detection Engine

**Purpose:** Compute hotness scores and identify trending cards

**Algorithms:**

**Velocity Score:**
```python
velocity = sales_count / active_listings_count
```

**Momentum Score:**
```python
momentum = (current_avg_price - price_7d_ago) / price_7d_ago * 100
```

**Hotness Score (Current - Phase 1):**
```python
# eBay-only scoring (~60% accuracy)
hotness = (
    velocity * 0.4 +      # eBay sales/listings
    momentum * 0.35 +     # eBay price change
    social * 0.25         # Placeholder (0)
)
```

**Opportunity Score (Target - Phase 2):**
```python
# Multi-source scoring (~85-90% accuracy)
opportunity = (
    hotness * 0.25 +           # eBay trends
    sell_through * 0.20 +      # Terapeak
    price_velocity * 0.15 +    # Card Ladder
    grading_spike * 0.15 +     # PSA
    social_momentum * 0.15 +   # Twitter/Reddit
    release_timing * 0.10      # Calendar
)
```

**Execution:** Daily batch job at 3 AM EST (after scraping)

**Status:** ✅ Complete (Phase 1 - eBay only)

**Planned Enhancements (Phase 2-3):**
- Multi-source opportunity scoring
- Buy decision engine
- Sell strategy engine
- Morning intelligence report

### 4. REST API Layer

**Purpose:** Expose data to frontend and external consumers

**Technology:** FastAPI, Uvicorn

**Endpoints (18 total):**

**Trending & Stats:**
- `GET /api/trending` - Top trending cards with filtering/sorting
- `GET /api/trending/rookies` - Hot rookie cards
- `GET /api/stats` - Market statistics

**Cards:**
- `GET /api/cards/{id}` - Card details with price history
- `GET /api/cards` - Search cards with pagination

**Inventory:**
- `POST /api/inventory` - Add card to inventory
- `GET /api/inventory` - Get inventory by status
- `GET /api/inventory/stats` - Portfolio statistics
- `POST /api/inventory/sales` - Record sale
- `GET /api/inventory/{id}` - Item details

**Watchlist:**
- `POST /api/watchlist` - Add to watchlist
- `GET /api/watchlist` - Get watchlist with alerts
- `DELETE /api/watchlist/{id}` - Remove from watchlist
- `GET /api/watchlist/alerts` - Get price alerts

**Health:**
- `GET /health` - Health check

**Features:**
- Advanced filtering (price, hotness, sport)
- Flexible sorting (hotness, velocity, price, volume)
- Pagination support
- Swagger documentation
- CORS enabled

**Authentication:** None (future: API key + OAuth)

**Status:** ✅ Complete

### 5. Frontend Dashboard

**Purpose:** Visualize trending cards and analytics

**Technology:** React, Vite, Recharts, TailwindCSS

**Pages:**
- **Home** (`/`) - Trending cards table
- **Card Detail** (`/card/:id`) - Price charts, profit calculator
- **Inventory** (`/inventory`) - Portfolio dashboard
- **Watchlist** (`/watchlist`) - Price monitoring

**Components:**
- `TrendingTable` - Sortable table with buy recommendations
- `PriceChart` - Historical price visualization
- `ProfitCalculator` - Interactive calculator with eBay fees

**Features:**
- Real-time profit/loss calculations
- ROI percentages
- Price alerts
- Status filtering (owned/listed/sold)
- Navigation between all features

**Status:** ✅ Complete (requires Node.js 16+)

### 6. Automation Layer

**Purpose:** Scheduled data collection and processing

**Technology:** APScheduler

**Jobs:**
- **Daily Collection** - 2 AM EST
- **Target Lists** - YAML configuration
- **Report Generation** - CSV and text reports

**Configuration:**
```yaml
players:
  - name: "Victor Wembanyama"
    queries: ["Wembanyama rookie", "Wembanyama Prizm"]
  - name: "Scoot Henderson"
    queries: ["Henderson rookie"]
  # ... 6 more players
```

**Status:** ✅ Complete

## Data Flow

### Nightly Pipeline

```
1. 2:00 AM - eBay scraper runs
   ├─> Fetch sold listings (last 7 days)
   ├─> Parse card details from titles
   ├─> Find or create card in database
   └─> Insert into `sales` table

2. 2:30 AM - Active listings scraper
   ├─> Fetch current BIN/auction listings
   └─> Insert into `active_listings` table

3. 3:00 AM - Trend calculator runs
   ├─> Aggregate sales by card
   ├─> Calculate velocity scores
   ├─> Compute price changes
   ├─> Calculate momentum scores
   ├─> Calculate hotness scores
   └─> Insert into `price_trends` table

4. 3:30 AM - Report generator
   ├─> Query top 25 trending cards
   ├─> Generate CSV report
   └─> Generate text report
```

### User Actions

```
Inventory Management:
   User adds card → POST /api/inventory → Insert into `inventory`
   User records sale → POST /api/inventory/sales → Calculate profit/ROI
   User views portfolio → GET /api/inventory/stats → Aggregate P&L

Watchlist:
   User adds card → POST /api/watchlist → Insert into `watchlist`
   System checks prices → Compare with target → Trigger alerts
   User views alerts → GET /api/watchlist/alerts → Return matches
```

## Deployment Architecture

```
┌─────────────────────────────────────────┐
│         jgaffiliates.com                │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  <subdomain>.jgaffiliates.com     │ │
│  │                                   │ │
│  │  ┌──────────┐    ┌─────────────┐ │ │
│  │  │ Frontend │    │  API Server │ │ │
│  │  │  (React) │◄───┤  (FastAPI)  │ │ │
│  │  │  Port    │    │  Port 8000  │ │ │
│  │  │  3000    │    └──────┬──────┘ │ │
│  │  └──────────┘           │        │ │
│  │                  ┌───────▼──────┐ │ │
│  │                  │  PostgreSQL  │ │ │
│  │                  │  Port 5432   │ │ │
│  │                  └──────────────┘ │ │
│  │                                   │ │
│  │  ┌────────────────────────────┐  │ │
│  │  │  APScheduler (Cron Jobs)   │  │ │
│  │  │  - Daily at 2 AM           │  │ │
│  │  └────────────────────────────┘  │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology | Version | Status |
|-------|-----------|---------|--------|
| Database | PostgreSQL | 14+ | ✅ |
| Backend | Python | 3.11+ | ✅ |
| API | FastAPI | Latest | ✅ |
| ORM | SQLAlchemy | Latest | ✅ |
| Scraping | Requests | Latest | ✅ |
| Scheduling | APScheduler | Latest | ✅ |
| Frontend | React | 18 | ✅ |
| Build Tool | Vite | Latest | ✅ |
| Styling | TailwindCSS | Latest | ✅ |
| Charts | Recharts | Latest | ✅ |
| Hosting | TBD | - | ⏳ |

## Scalability Considerations

**Current Phase:** Single server, unlimited cards tracked

**Future Scaling:**
- Database read replicas for API queries
- Redis cache for trending cards
- Celery for distributed scraping
- S3 for historical data archival
- CDN for frontend assets

## Security

- API rate limiting (planned)
- Database connection pooling ✅
- Secrets in environment variables ✅
- HTTPS only (production)
- Input sanitization ✅
- SQL injection prevention (SQLAlchemy ORM) ✅

## Monitoring

**Planned:**
- Scraper success/failure logs
- API response times
- Database query performance
- Alert on scraper failures
- Daily data quality checks

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-02-11 | Initial architecture design |
| 2.0.0 | 2025-02-11 | Added inventory, watchlist, frontend |

## Next Steps

### Phase 1: Foundation ✅ COMPLETE
- ✅ All 18 endpoints operational
- ✅ Frontend dashboard deployed
- ✅ eBay data collection automated
- ✅ Documentation complete

### Phase 2: Multi-Source Intelligence ⏳ PLANNED
1. **PSA Population Scraper** (Week 1-2)
   - Web scraping implementation
   - Grading spike detection
   - PSA 10 rate calculations

2. **Card Ladder & Terapeak** (Week 3-4)
   - Price benchmark scraper
   - Sell-through rate integration
   - Velocity calculations

3. **Social Signals** (Week 5-6)
   - Twitter/Reddit API integration
   - Sentiment analysis
   - Social momentum scoring

### Phase 3: Decision Engines ⏳ PLANNED
4. **Intelligence Engine** (Week 7-8)
   - Multi-source aggregation
   - Opportunity scoring (7-factor)
   - Anomaly detection

5. **Buy/Sell Engines** (Week 9-10)
   - Buy decision engine (optimal prices)
   - Sell strategy engine (grade vs. raw)
   - Morning intelligence report

### Phase 4: Production ⏳ PLANNED
6. **Deployment** (Week 11-13)
   - Production hosting
   - User authentication
   - Email alerts
   - Mobile optimization

**See [Gap Analysis](../TRADING-WORKFLOW-GAP-ANALYSIS.md) for detailed implementation plan.**
