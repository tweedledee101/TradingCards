# System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Data Sources                            │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│  eBay    │   PSA    │  Card    │ Twitter  │    Reddit       │
│  API     │  Website │  Ladder  │   API    │     API         │
└────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬────────────┘
     │          │          │          │          │
     │          │          │          │          │
     ▼          ▼          ▼          ▼          ▼
┌────────────────────────────────────────────────────────────┐
│                    Scraper Layer                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  eBay    │  │   PSA    │  │  Card    │  │  Social  │  │
│  │ Scraper  │  │ Scraper  │  │  Ladder  │  │ Scraper  │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└────────┬───────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                   PostgreSQL Database                        │
│  ┌──────┐  ┌───────┐  ┌──────────┐  ┌──────────────┐      │
│  │cards │  │ sales │  │ listings │  │ psa_pop      │      │
│  └──────┘  └───────┘  └──────────┘  └──────────────┘      │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│              Trend Detection Engine                          │
│  ┌────────────────┐  ┌────────────────┐                    │
│  │  Price Velocity│  │ Hotness Score  │                    │
│  │  Calculator    │  │  Calculator    │                    │
│  └────────────────┘  └────────────────┘                    │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                    REST API Layer                            │
│  ┌────────────────────────────────────────────────────┐    │
│  │  FastAPI Endpoints                                  │    │
│  │  - GET /api/trending                               │    │
│  │  - GET /api/cards/{id}/trends                      │    │
│  │  - GET /api/rookies/hot                            │    │
│  └────────────────────────────────────────────────────┘    │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Frontend Dashboard                          │
│                  (Future Phase)                              │
│  - Trending cards visualization                             │
│  - Price charts                                              │
│  - Hotness score rankings                                   │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Scraper Layer

**Purpose:** Collect raw data from multiple sources

**Components:**
- **eBay Scraper** - Sold listings via Browse API
- **PSA Scraper** - Population reports via web scraping
- **Card Ladder Scraper** - Price benchmarks
- **Social Scraper** - Twitter/Reddit mentions

**Schedule:**
- eBay: Nightly at 2 AM EST
- PSA: Weekly on Sundays
- Social: Every 4 hours

**Technology:** Python, requests, BeautifulSoup, Selenium

### 2. Database Layer

**Purpose:** Persistent storage for all data

**Technology:** PostgreSQL 14+

**Key Tables:**
- `cards` - Master card catalog
- `sales` - Historical transactions
- `active_listings` - Current market supply
- `price_trends` - Pre-computed metrics
- `psa_population` - Grading data
- `social_signals` - Social media data

See [Database Design](./database-design.md) for detailed schema.

### 3. Trend Detection Engine

**Purpose:** Compute hotness scores and identify trending cards

**Algorithms:**

**Velocity Score:**
```python
velocity = sales_count / active_listings_count
```

**Price Momentum:**
```python
momentum = (current_avg_price - price_7d_ago) / price_7d_ago * 100
```

**Hotness Score:**
```python
hotness = (
    velocity * 0.4 +
    momentum * 0.3 +
    psa_growth_rate * 0.2 +
    social_sentiment * 0.1
)
```

**Execution:** Daily batch job at 3 AM EST (after scraping)

### 4. REST API Layer

**Purpose:** Expose data to frontend and external consumers

**Technology:** FastAPI, Uvicorn

**Key Endpoints:**
- `GET /api/trending` - Top trending cards
- `GET /api/cards/{id}` - Card details
- `GET /api/cards/{id}/trends` - Historical trends
- `GET /api/rookies/hot` - Hot rookie cards
- `GET /api/search?q={query}` - Search cards

**Authentication:** API key (future)

### 5. Frontend Dashboard (Future)

**Purpose:** Visualize trending cards and analytics

**Technology:** React, Chart.js, TailwindCSS

**Features:**
- Real-time trending cards table
- Price history charts
- Hotness score visualization
- Player search
- Alerts for spike detection

## Data Flow

### Nightly Pipeline

```
1. 2:00 AM - eBay scraper runs
   ├─> Fetch sold listings (last 24h)
   ├─> Parse card details
   └─> Insert into `sales` table

2. 2:30 AM - Active listings scraper
   ├─> Fetch current BIN/auction listings
   └─> Insert into `active_listings` table

3. 3:00 AM - Trend calculator runs
   ├─> Aggregate sales by card
   ├─> Calculate velocity scores
   ├─> Compute price changes
   ├─> Calculate hotness scores
   └─> Insert into `price_trends` table

4. 3:30 AM - API cache refresh
   └─> Pre-compute trending cards list
```

### Weekly Pipeline

```
Sunday 1:00 AM - PSA scraper
   ├─> Scrape population reports
   ├─> Compare with previous week
   ├─> Calculate growth rates
   └─> Insert into `psa_population` table
```

### Hourly Pipeline

```
Every 4 hours - Social scraper
   ├─> Fetch Twitter mentions
   ├─> Fetch Reddit posts
   ├─> Analyze sentiment
   └─> Insert into `social_signals` table
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
│  │  │  (Nginx) │◄───┤  (FastAPI)  │ │ │
│  │  └──────────┘    └──────┬──────┘ │ │
│  │                          │        │ │
│  │                  ┌───────▼──────┐ │ │
│  │                  │  PostgreSQL  │ │ │
│  │                  └──────────────┘ │ │
│  │                                   │ │
│  │  ┌────────────────────────────┐  │ │
│  │  │  Cron Jobs (Scrapers)      │  │ │
│  │  └────────────────────────────┘  │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology | Justification |
|-------|-----------|---------------|
| Database | PostgreSQL | Robust, time-series support, JSON fields |
| Backend | Python 3.11+ | Rich scraping libraries, data processing |
| API | FastAPI | Fast, async, auto-documentation |
| Scraping | Requests, BeautifulSoup, Selenium | Industry standard |
| Scheduling | APScheduler | Python-native, flexible |
| Frontend | React | Modern, component-based |
| Hosting | TBD | AWS/DigitalOcean/Vercel |

## Scalability Considerations

**Current Phase:** Single server, ~1000 cards tracked

**Future Scaling:**
- Database read replicas for API queries
- Redis cache for trending cards
- Celery for distributed scraping
- S3 for historical data archival
- CDN for frontend assets

## Security

- API rate limiting
- Database connection pooling
- Secrets in environment variables
- HTTPS only
- Input sanitization
- SQL injection prevention (SQLAlchemy ORM)

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

## Next Steps

1. ✅ Database schema
2. ✅ Documentation structure
3. 🔄 eBay scraper implementation
4. ⏳ Trend detection algorithms
5. ⏳ REST API endpoints
6. ⏳ Frontend dashboard
