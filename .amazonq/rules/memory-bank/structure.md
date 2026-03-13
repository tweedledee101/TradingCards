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
│   │   ├── ebay_scraper.py      # eBay Browse API scraper
│   │   ├── psa_scraper.py       # PSA population scraper
│   │   └── cardladder_scraper.py # Card Ladder price scraper
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

### 1. Backend Data Pipeline
**Location**: `backend/services/data_pipeline.py`

Orchestrates data collection from multiple sources:
- Coordinates scraper execution (eBay, PSA, Card Ladder)
- Processes raw data into normalized format
- Calculates trend metrics (velocity, momentum, hotness)
- Stores results in PostgreSQL database

**Key Services**:
- `data_pipeline.py`: Main orchestration
- `trend_calculator.py`: Hotness score algorithm (15-90 range)
- `opportunity_analyzer.py`: Arbitrage detection (profit after fees)
- `sell_through_calculator.py`: Market confidence metrics

### 2. Scrapers
**Location**: `backend/scrapers/`

Data collection from external sources:
- **eBay Scraper**: Browse API for sold listings and active listings
- **PSA Scraper**: Selenium-based scraper for grading population data
- **Card Ladder Scraper**: Selenium-based scraper for price benchmarks

**Integration Pattern**: Scrapers → Webhooks → Database → Frontend

### 3. REST API
**Location**: `backend/api/`

FastAPI-based REST API with 18+ endpoints:
- `/api/cards` - Card listings with filtering/sorting
- `/api/opportunities` - Arbitrage opportunities
- `/api/inventory` - Portfolio management
- `/api/watchlist` - Price monitoring
- `/api/grading/{card_id}` - PSA population data
- `/api/price-benchmarks/{card_id}` - Card Ladder benchmarks
- `/api/webhooks/novaact/*` - Scraper data intake

**Features**: Advanced filtering, pagination, sorting, CSV export

### 4. Frontend Dashboard
**Location**: `frontend/src/`

React SPA with Vite + Tailwind CSS:
- **Pages**: Dashboard, Card Details, Inventory, Watchlist
- **Components**: CardTable, FilterPanel, PriceChart, GradingPopulation
- **State Management**: React hooks + localStorage
- **Styling**: Tailwind CSS utility classes

**Key Features**: Budget filters, profit margin display, price history charts, responsive design

### 5. Database Schema
**Location**: `backend/models/schema.sql`

PostgreSQL database with 9 tables:
- `cards` - Core card data
- `price_history` - Historical price tracking (14 days)
- `sales_data` - Individual sale records
- `grading_population` - PSA grading data
- `price_benchmarks` - Card Ladder benchmarks
- `inventory` - User portfolio tracking
- `watchlist` - Price monitoring
- `accuracy_tracking` - Prediction validation
- `sell_through_metrics` - Market confidence

### 6. Automation System
**Location**: `backend/services/scheduler.py`

APScheduler-based automation:
- Daily data collection at 2 AM
- Target list processing (25 players)
- Report generation (CSV + TXT)
- Automated trend detection

## Architectural Patterns

### Data Flow Architecture
```
External Sources → Scrapers → Webhooks → Database → API → Frontend
                                    ↓
                            Trend Calculator
                                    ↓
                          Opportunity Analyzer
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
- **Domain**: cardpulse.jgaffiliated.com
- **Backend**: AWS ECS (Docker containers)
- **Frontend**: AWS CloudFront + S3
- **Database**: AWS RDS (PostgreSQL)
- **Scrapers**: AWS Lambda (scheduled)
- **IaC**: CloudFormation templates
