# Trading Card Platform

A data-driven platform for detecting trending trading cards by aggregating signals from multiple sources including eBay, PSA, Card Ladder, and social media.

## Project Goal

Build a "hotness score" system that identifies rookie cards gaining momentum before they spike, by analyzing:
- Price velocity (week-over-week changes)
- Sales volume vs active listings
- Grading population spikes
- Social media hype
- Auction close prices vs BIN prices

## Architecture

See [Architecture Documentation](./docs/architecture/) for detailed system design.

### Key Components

1. **Backend Data Pipeline** - Scrapers and aggregators for multiple data sources
2. **Trend Detection Engine** - Algorithms to compute hotness scores
3. **REST API** - Advanced filtering, inventory tracking, watchlist management
4. **Frontend Dashboard** - React app with portfolio analytics
5. **Inventory System** - Track purchases, sales, and profits
6. **Watchlist** - Monitor target cards with price alerts

## Data Sources

| Source | Purpose | Status |
|--------|---------|--------|
| eBay Browse API | Sold listings, price data | ✅ Complete |
| eBay Active Listings | Current market supply | ✅ Complete |
| PSA Population | Grading volume trends | Planned |
| Card Ladder | Price benchmarks | Planned |
| Twitter/Reddit | Social sentiment | Planned |

## Features

### 🔥 Trend Detection
- **Hotness Score Algorithm** - Multi-factor scoring system
- **Price Velocity** - Week-over-week price changes
- **Momentum Tracking** - Sales volume trends
- **Advanced Filtering** - Filter by price, sport, hotness threshold
- **Flexible Sorting** - Sort by any metric

### 💼 Portfolio Management
- **Inventory Tracking** - Record all card purchases
- **Profit/Loss Tracking** - Real-time P&L calculations
- **ROI Analytics** - Portfolio-wide ROI metrics
- **Sales Recording** - Track sales with automatic profit calculation
- **Storage Management** - Know where each card is stored

### 👀 Watchlist
- **Price Monitoring** - Set target prices for cards
- **Price Alerts** - Get notified when cards hit targets
- **Trend Monitoring** - Track hotness scores for watchlist cards

### 📊 Analytics
- **Market Statistics** - Overall market overview
- **Price History** - Historical price trends
- **Volume Analysis** - Sales volume tracking
- **Portfolio Stats** - Total invested, current value, profits

### 🤖 Automation
- **Daily Collection** - Automated data collection at 2 AM
- **Target Lists** - Configure players to track
- **Daily Reports** - CSV and text reports of trending cards

## Documentation

- [Quick Start Guide](./QUICKSTART.md)
- [New Features Quick Start](./docs/QUICKSTART-NEW-FEATURES.md) ⭐ NEW
- [API Enhancements Guide](./docs/API-ENHANCEMENTS.md) ⭐ NEW
- [API Documentation](./backend/api/README.md)
- [Pipeline Documentation](./backend/PIPELINE.md)
- [System Architecture](./docs/architecture/system-architecture.md)
- [Database Schema & ERD](./docs/architecture/database-design.md)
- [Data Flow Diagrams](./docs/architecture/diagrams/)
- [Testing Guide](./docs/TESTING.md)
- [Setup Guide](./docs/setup/installation.md)
- [Architecture Decisions](./docs/architecture/decisions/)
- [Project Status](./docs/PROJECT-STATUS.md)
- [Pipeline Implementation](./docs/PIPELINE-IMPLEMENTATION.md)
- [Deployment Architecture](./docs/DEPLOYMENT-ARCHITECTURE.md)
- [User Authentication Roadmap](./docs/USER-AUTH-ROADMAP.md)
- [Automation Guide](./docs/AUTOMATION.md)

## Quick Start

```bash
# 1. Install all dependencies
./setup.sh  # Linux/Mac
setup.bat   # Windows

# 2. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys and database credentials

# 3. Setup database
psql -U postgres -c "CREATE DATABASE trading_cards;"
psql -U postgres -d trading_cards -f backend/models/schema.sql

# 4. Apply latest migration (inventory system)
./migrate.sh  # Linux/Mac
migrate.bat   # Windows

# 5. Test pipeline with mock data
python3 backend/test_pipeline.py

# 6. Run pipeline with real eBay data
python3 -m backend.run_pipeline --query "Wembanyama rookie" --days 7

# 7. Start API server
python3 -m backend.api.run
# Visit http://localhost:8000/docs for interactive API docs

# 8. Test API
python3 backend/test_api.py

# 9. Run automated collection (test mode)
python3 -m backend.run_scheduler --now

# 10. Start scheduler (runs daily at 2 AM)
python3 -m backend.run_scheduler

# 11. Run tests
./run_tests.sh all

# 12. Start frontend (requires Node.js 16+)
cd frontend
npm install
npm run dev
# Visit http://localhost:3000
```

## Testing

```bash
# Run all tests
./run_tests.sh all

# Run unit tests only (fast)
./run_tests.sh unit

# Run with coverage report
./run_tests.sh coverage
```

See [Testing Guide](./docs/TESTING.md) for detailed testing documentation.

## Project Status

**Current Phase:** Inventory & Portfolio Management - COMPLETE ✅

- [x] Database schema design
- [x] SQLAlchemy ORM models
- [x] Project structure
- [x] eBay scraper implementation
- [x] Trend detection algorithms
- [x] Data pipeline orchestration
- [x] Comprehensive test suite
- [x] REST API endpoints
- [x] Automated scheduler
- [x] Target list configuration
- [x] Daily report generation
- [x] Advanced API filtering & sorting
- [x] Inventory tracking system
- [x] Portfolio analytics
- [x] Watchlist management
- [x] Frontend dashboard (React)
- [ ] PSA population scraper
- [ ] Enhanced profit calculator
- [ ] Production deployment

## Domain

Platform will be hosted at: `<subdomain>.jgaffiliates.com` (subdomain TBD)

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development workflow and standards.

## License

[License TBD]
