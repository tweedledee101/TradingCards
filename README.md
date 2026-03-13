# Trading Card Platform

A data-driven platform for detecting trending trading cards by aggregating signals from multiple sources including eBay, PSA, Card Ladder, and social media.

## Project Goal

Build an **arbitrage opportunity finder** that identifies profitable card flips by analyzing:
- Market rate vs current listings (buy below market)
- Profit after eBay/PayPal fees (13%)
- Price momentum (rising/stable/falling)
- Sales velocity (demand strength)
- Sell-through rates (market confidence)

**Focus**: Professional dealer approach - find cards you can buy below market and flip for guaranteed profit, validated by momentum signals.

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
| eBay Browse API | Sold listings, price data | ✅ Working (Sample Data) | Critical |
| Facebook Marketplace | Local deals (40-60% margins) | ✅ Search URLs Generated | Critical |
| COMC | Bulk buying at wholesale | ✅ Search URLs Generated | High |
| Whatnot | Live auction sniping | ✅ Search URLs Generated | High |
| Mercari | Fast turnover deals | ✅ Search URLs Generated | High |
| PSA Population | Grading spikes | ⚠️ Infrastructure Ready | Medium |
| Card Ladder Benchmarks | Price velocity | ⚠️ Infrastructure Ready | Medium |
| 130point.com | Variant-specific comps | ✅ Scraper Built | Medium |

**Data Coverage:** 5/8 sources implemented - Multi-platform sourcing complete!

## Features

### 🎯 Multi-Platform Sourcing (NEW)
- **Facebook Marketplace** - Find local deals at 40-60% below market
- **COMC** - Bulk buying at wholesale prices
- **Whatnot** - Snipe deals during live auctions
- **Mercari** - Fast turnover, motivated sellers
- **eBay** - Market rate baseline for selling
- **Arbitrage Calculator** - Net profit after fees (13.15%) + shipping ($5)
- **ROI Analysis** - Sorts opportunities by return on investment
- **Visual Card Matching** - Card images for cross-platform verification

### 🎯 Opportunity Finder
- **Arbitrage Analysis** - Buy price, sell price, profit after fees, ROI
- **Momentum Validation** - Price trends, sales velocity, sell-through rates
- **Opportunity Score** - 70% arbitrage + 30% momentum (0-100)
- **Confidence Levels** - VERY HIGH 🔥, HIGH ✅, MEDIUM ⚠️, LOW 🥶
- **Dynamic Filters** - Budget range, min profit, min ROI, momentum direction
- **Market Data** - Recent sales, price consistency, days to sell
- **Fee Calculation** - Includes eBay (12.9%) + PayPal fees
- **Dealer Focus** - Only shows profitable opportunities

### 🔥 Variant Differentiation (NEW)
- **Card Numbers** - Exact card identification (#150, #258, etc.)
- **Parallel Types** - Base, Silver, Red Ice, Purple, Orange
- **Grading Info** - PSA/BGS/Raw with grade values (9, 9.5, 10)
- **Visual Identification** - Card images in trending table
- **Exact eBay Searches** - Search for specific variants, not generic

### 🔥 Trend Detection
- **Hotness Score Algorithm** - Multi-factor scoring system (15-90 range)
- **Price Velocity** - Week-over-week price changes with historical trends
- **Momentum Tracking** - Sales volume trends over 14 days
- **Advanced Filtering** - Filter by price, sport, hotness threshold, budget
- **Note**: Being replaced by Opportunity Finder (see above)

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
- **Automated Target Discovery** ⭐ NEW - Card Ladder movers scraper (50-100 trending cards daily)
- **Daily Collection** - Automated data collection at 2 AM
- **Target Lists** - Auto-generated from Card Ladder price momentum (zero manual curation)
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
- [Automated Target Discovery](./docs/AUTOMATED-TARGET-DISCOVERY.md) ⭐ NEW - Zero manual curation
- [Opportunity Finder Guide](./docs/OPPORTUNITY-FINDER.md) ⭐ NEW - Arbitrage + momentum system
- [System Redesign Summary](./docs/SYSTEM-REDESIGN-SUMMARY.md) ⭐ NEW - What changed
- [API Documentation](./backend/api/README.md)
- [API Enhancements Guide](./docs/API-ENHANCEMENTS.md)
- [New Features Quick Start](./docs/QUICKSTART-NEW-FEATURES.md)
- [Pipeline Documentation](./backend/PIPELINE.md)
- [Automation Guide](./docs/AUTOMATION.md)

### Project Planning
- [Project Status](./docs/PROJECT-STATUS.md) - Current phase & metrics
- [Gap Analysis](./docs/TRADING-WORKFLOW-GAP-ANALYSIS.md) ⭐ - What's missing & roadmap
- [Data Sources Setup](./DATA-SOURCES-SETUP.md) ⭐ NEW - Connect PSA & Card Ladder
- [NovaAct Quick Start](./NOVAACT-QUICKSTART.md) ⭐ NEW - Test scrapers in 5 minutes
- [NovaAct PSA Integration](./docs/NOVAACT-PSA-INTEGRATION.md) - PSA scraper guide
- [NovaAct Price Benchmarks](./docs/NOVAACT-PRICE-BENCHMARK-INTEGRATION.md) - Card Ladder guide
- [Phase 2 Complete](./PHASE2-INFRASTRUCTURE-COMPLETE.md) ⭐ NEW - Infrastructure summary
- [Multi-Source Visual Guide](./MULTI-SOURCE-VISUAL-GUIDE.md) - What you'll see
- [UI Enhancements](./docs/UI-ENHANCEMENTS-BUDGET-MARGIN.md) - Budget filter & profit margin
- [Quick Reference](./docs/QUICK-REFERENCE-BUDGET-MARGIN.md) - Feature guide
- [Visual Guide](./docs/VISUAL-GUIDE-BEFORE-AFTER.md) - Before/after comparison
- [Pipeline Implementation](./docs/PIPELINE-IMPLEMENTATION.md)
- [Deployment Architecture](./docs/DEPLOYMENT-ARCHITECTURE.md)
- [AWS Deployment Guide](./docs/AWS-DEPLOYMENT-GUIDE.md) ⭐ NEW - CloudFormation templates
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

# 8b. Test new Opportunity Finder
python3 -m backend.test_opportunities

# 9. Test automated target discovery
python3 backend/test_discovery.py

# 10. Run discovery immediately (test mode)
python3 -m backend.run_discovery --now

# 11. Start discovery scheduler (runs daily at 1 AM)
python3 -m backend.run_discovery

# 12. Run automated collection (test mode)
python3 -m backend.run_scheduler --now

# 13. Start scraper scheduler (runs daily at 2 AM)
python3 -m backend.run_scheduler

# 14. Run tests
./run_tests.sh all

# 15. Start frontend (requires Node.js 16+)
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

**Current Phase:** Phase 2 Complete - Budget + Opportunity Filtering  
**Next Phase:** Phase 3 - API Endpoints & Frontend Integration

### Phase 1: Foundation (COMPLETE)
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

### Phase 2: Volume-Based Discovery (COMPLETE)
- [x] Volume discovery service (Phase 1)
- [x] Budget + opportunity filtering (Phase 2)
- [x] OpportunityAnalyzer integration
- [x] Multi-factor arbitrage scoring
- [x] Profit after fees calculation
- [x] ROI calculation
- [x] Flip speed indicators
- [x] Mock data generator for testing
- [x] System architecture verified
- [x] End-to-end testing complete

**Test Results**: 9 players with opportunities, 13-22% ROI, $500-$2000 budget

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

### ✅ Phase 1.5: Quick Wins (COMPLETE)
- [x] CSV export with filtered/sorted results
- [x] Budget presets ($25, $50, $100, $250, $500, $1000)
- [x] Budget saved to localStorage
- [x] Advanced filters (sport, year range, hotness range)
- [x] Collapsible filter panel

### ⚠️ Phase 2: Multi-Source Intelligence (80% COMPLETE - TESTING NOW)
- [x] PSA population scraper infrastructure (webhook)
- [x] PSA grading display on card detail pages
- [x] Price benchmark infrastructure (webhook)
- [x] Price benchmark display on frontend
- [x] Database migrations (grading_population, price_benchmarks)
- [x] **PSA scraper (Selenium)** - Infrastructure ready, testing on real site now ⬅️ IN PROGRESS
- [x] **Card Ladder scraper (Selenium)** - Infrastructure ready, testing on real site now ⬅️ IN PROGRESS
- [x] **Sell-through calculator (from eBay)** - Code ready, blocked by eBay API
- [x] Data sources setup guide
- [ ] Real data flowing from PSA ⬅️ TESTING NOW
- [ ] Real data flowing from Card Ladder ⬅️ TESTING NOW
- [ ] Intelligence aggregation engine ⬅️ NEXT
- [ ] Enhanced opportunity scoring (multi-factor) ⬅️ NEXT

### 🚀 Phase 2.5: Automated Discovery (PIVOTED - IN PROGRESS)
- [x] eBay trending discovery scraper (deprecated - rate limited)
- [x] Card Ladder movers scraper ⬅️ NEW APPROACH
- [x] Discovery scoring algorithm (price velocity + price range)
- [x] Auto-update targets.yaml service
- [x] Daily discovery scheduler (1 AM)
- [x] Manual favorites preservation
- [ ] Card Ladder movers integration ⬅️ TESTING NOW
- [ ] PSA grading spike detection ⬅️ NEXT

### ⏳ Phase 3: Decision Engines (PLANNED)
- [ ] Buy decision engine (optimal entry prices)
- [ ] Sell strategy engine (grade vs. raw ROI)
- [ ] Morning intelligence report generator
- [ ] Price alert system
- [ ] Auto-watchlist population
- [ ] ROI projections

### ⏳ Phase 4: Production & Scale (IN PROGRESS)
- [x] AWS infrastructure planning
- [x] CloudFormation templates (eBay compliance)
- [x] Domain selection (cardpulse.jgaffiliated.com)
- [ ] eBay compliance deployment ⬅️ NEXT
- [ ] Full platform deployment (ECS + RDS)
- [ ] Enhanced profit calculator (shipping, grading fees)
- [ ] User authentication (Cognito)
- [ ] Email alerts (SES)
- [ ] Mobile optimization

**See [Gap Analysis](./docs/TRADING-WORKFLOW-GAP-ANALYSIS.md) for detailed roadmap.**

## Domain

Platform will be hosted at: **`cardpulse.jgaffiliated.com`**

- **Production API:** `https://cardpulse.jgaffiliated.com/api`
- **Frontend:** `https://cardpulse.jgaffiliated.com`
- **Infrastructure:** 100% AWS (Lambda, ECS, RDS, CloudFront)
- **Deployment:** CloudFormation (Infrastructure as Code)

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development workflow and standards.

## License

[License TBD]
