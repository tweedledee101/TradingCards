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

| Source | Purpose | Status | Priority |
|--------|---------|--------|----------|
| eBay Browse API | Sold listings, price data | ✅ Complete | - |
| eBay Active Listings | Current market supply | ✅ Complete | - |
| Terapeak | Sell-through rates | ⏳ Planned | High |
| Card Ladder | Price velocity, benchmarks | ⏳ Planned | High |
| PSA Population | Grading spikes | ⏳ Planned | Critical |
| Twitter/Reddit | Social sentiment | ⏳ Planned | Medium |
| Release Calendars | Topps/Panini releases | ⏳ Planned | Low |

**Data Coverage:** 2/7 sources (29%) - See [Gap Analysis](./docs/TRADING-WORKFLOW-GAP-ANALYSIS.md)

## Features

### 🔥 Trend Detection
- **Hotness Score Algorithm** - Multi-factor scoring system (15-90 range)
- **Price Velocity** - Week-over-week price changes with historical trends
- **Momentum Tracking** - Sales volume trends over 14 days
- **Advanced Filtering** - Filter by price, sport, hotness threshold, budget
- **Flexible Sorting** - Sort by hotness, velocity, price, volume, or profit margin
- **Budget Filter** - Only see cards within your budget
- **Profit Margin Display** - See potential profit % at a glance
- **Pagination** - Browse 100 cards (25 per page)
- **Column Tooltips** - Hover explanations for all metrics

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
- **Price History** - Historical price trends (14-day data)
- **Volume Analysis** - Sales volume tracking
- **Portfolio Stats** - Total invested, current value, profits
- **Card Detail Pages** - Full metadata with placeholder images
- **Buy Zone Calculator** - Velocity-adjusted buy recommendations
- **Row Color Coding** - Green (buy), yellow (watch), white (skip)

### 🤖 Automation
- **Daily Collection** - Automated data collection at 2 AM
- **Target Lists** - Configure players to track (25 pre-configured)
- **Daily Reports** - CSV and text reports of trending cards
- **Sample Data Generator** - 25 realistic cards for testing

## Documentation

### Getting Started
- [Quick Start Guide](./QUICKSTART.md)
- [Setup Guide](./docs/setup/installation.md)
- [Testing Guide](./docs/TESTING.md)

### Architecture & Design
- [System Architecture](./docs/architecture/system-architecture.md)
- [Database Schema & ERD](./docs/architecture/database-design.md)
- [Data Flow Diagrams](./docs/architecture/diagrams/)
- [Architecture Decisions](./docs/architecture/decisions/)

### Features & API
- [API Documentation](./backend/api/README.md)
- [API Enhancements Guide](./docs/API-ENHANCEMENTS.md)
- [New Features Quick Start](./docs/QUICKSTART-NEW-FEATURES.md)
- [Pipeline Documentation](./backend/PIPELINE.md)
- [Automation Guide](./docs/AUTOMATION.md)

### Project Planning
- [Project Status](./docs/PROJECT-STATUS.md) - Current phase & metrics
- [Gap Analysis](./docs/TRADING-WORKFLOW-GAP-ANALYSIS.md) ⭐ - What's missing & roadmap
- [UI Enhancements](./docs/UI-ENHANCEMENTS-BUDGET-MARGIN.md) ⭐ NEW - Budget filter & profit margin
- [Quick Reference](./docs/QUICK-REFERENCE-BUDGET-MARGIN.md) ⭐ NEW - Feature guide
- [Visual Guide](./docs/VISUAL-GUIDE-BEFORE-AFTER.md) ⭐ NEW - Before/after comparison
- [Pipeline Implementation](./docs/PIPELINE-IMPLEMENTATION.md)
- [Deployment Architecture](./docs/DEPLOYMENT-ARCHITECTURE.md)
- [User Authentication Roadmap](./docs/USER-AUTH-ROADMAP.md)

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

# 5. Generate sample data (25 realistic cards)
/usr/bin/python3 -m backend.generate_sample_data

# 6. Test pipeline with mock data
python3 backend/test_pipeline.py

# 6. Run pipeline with real eBay data
python3 -m backend.run_pipeline --query "Wembanyama rookie" --days 7

# 7. Start API server
/usr/bin/python3 -m backend.api.run
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

**Current Phase:** Phase 1 Complete + UI Enhancements ✅  
**Next Phase:** CSV Export, Budget Presets, PSA Scraper (NovaAct)

### ✅ Phase 1: Foundation (COMPLETE)
- [x] Database schema design (9 tables)
- [x] SQLAlchemy ORM models
- [x] eBay scraper implementation
- [x] Trend detection algorithms (velocity, momentum, hotness)
- [x] Data pipeline orchestration
- [x] REST API endpoints (18 total)
- [x] Automated scheduler (daily at 2 AM)
- [x] Target list configuration (25 players)
- [x] Daily report generation
- [x] Advanced API filtering & sorting
- [x] Inventory tracking system
- [x] Portfolio analytics
- [x] Watchlist management
- [x] Frontend dashboard (React)
- [x] Comprehensive test suite
- [x] Complete documentation
- [x] Budget filter & profit margin display
- [x] Pagination (100 cards)
- [x] Column tooltips
- [x] Sample data generator (25 realistic cards)
- [x] Card detail pages with metadata
- [x] Varied hotness scores (15-90 range)
- [x] Historical price trends (14-day data)

### 🎯 Phase 1.5: Quick Wins (IN PROGRESS)
- [ ] CSV export with share functionality
- [ ] Budget presets ($25, $50, $100, $250, $500, $1000)
- [ ] Advanced filters (sport, year range, hotness range)
- [ ] Keyboard shortcuts
- [ ] Portfolio dashboard enhancements

### ⏳ Phase 2: Multi-Source Intelligence (PLANNED - NovaAct Integration)
- [ ] PSA population scraper (grading spikes) - NovaAct agent
- [ ] Card Ladder scraper (price benchmarks) - NovaAct agent
- [ ] 130point scraper (market data) - NovaAct agent
- [ ] Webhook endpoints for NovaAct data
- [ ] Intelligence aggregation engine
- [ ] Enhanced opportunity scoring algorithm (multi-factor)

### ⏳ Phase 3: Decision Engines (PLANNED)
- [ ] Buy decision engine (optimal entry prices)
- [ ] Sell strategy engine (grade vs. raw ROI)
- [ ] Morning intelligence report generator
- [ ] Price alert system
- [ ] Auto-watchlist population
- [ ] ROI projections

### ⏳ Phase 4: Production & Scale (PLANNED)
- [ ] Enhanced profit calculator (shipping, grading fees)
- [ ] Production deployment
- [ ] User authentication
- [ ] Email alerts
- [ ] Mobile optimization

**See [Gap Analysis](./docs/TRADING-WORKFLOW-GAP-ANALYSIS.md) for detailed roadmap.**

## Domain

Platform will be hosted at: `<subdomain>.jgaffiliates.com` (subdomain TBD)

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development workflow and standards.

## License

[License TBD]
