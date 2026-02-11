# Changelog

All notable changes to the Trading Card Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-02-11

### Added - Inventory & Portfolio Management
- **Inventory tracking system** with 3 new database tables
- **Portfolio analytics** with P&L and ROI calculations
- **Watchlist management** with price alerts
- **13 new API endpoints** (5 inventory, 4 watchlist, 3 trending enhancements, 1 stats)
- **React frontend** with 4 pages (Trending, Card Detail, Inventory, Watchlist)
- **Advanced API filtering** (price, hotness, sport)
- **Flexible API sorting** (hotness, velocity, price, volume)
- **Pagination support** for card search
- **Market statistics endpoint**
- **Price history** with configurable days
- **Auto-calculated metrics** (profit, ROI, alerts)
- **Migration scripts** (migrate.sh, migrate.bat)
- **Comprehensive documentation** (API-ENHANCEMENTS.md, QUICKSTART-NEW-FEATURES.md)

### Database Changes
- Added `inventory` table for card ownership tracking
- Added `inventory_sales` table for sales history
- Added `watchlist` table for price monitoring
- Updated `active_listings` with listing_title and listing_url fields
- Updated `price_trends` with momentum_score field

### API Changes
- Enhanced `/api/trending` with filtering and sorting
- Enhanced `/api/cards/{id}` with price history
- Enhanced `/api/cards` with pagination
- Added `/api/stats` for market statistics
- Added `/api/inventory` endpoints (5 total)
- Added `/api/watchlist` endpoints (4 total)
- Total endpoints: 5 → 18

### Frontend
- Created React application with Vite
- Added TailwindCSS for styling
- Added Recharts for data visualization
- Created 4 pages: Home, CardDetail, Inventory, Watchlist
- Created 3 components: TrendingTable, PriceChart, ProfitCalculator
- Integrated all 18 API endpoints

### Documentation
- Updated system-architecture.md with all components
- Updated database-design.md with 9 tables
- Updated PROJECT-STATUS.md with current phase
- Updated data-flow.md with inventory/watchlist flows
- Updated installation.md with migration steps
- Updated QUICKSTART.md with all features
- Updated API-IMPLEMENTATION.md with 18 endpoints
- Created docs/README.md as documentation index
- Created DOCUMENTATION-AUDIT.md with audit results
- Created IMPLEMENTATION-SUMMARY.md

## [1.0.0] - 2025-02-11

### Added - Backend Data Pipeline
- **PostgreSQL database schema** with 6 core tables
- **SQLAlchemy ORM models** for all database tables
- **eBay Browse API scraper** with title parsing
- **Trend detection algorithms** (velocity, momentum, hotness)
- **Data pipeline orchestration** connecting scraper → database → trends
- **Pipeline runner CLI tool** for manual execution
- **Automated collector** with APScheduler
- **Target list configuration** (YAML) for 8 players
- **Daily report generation** (CSV and text formats)
- **REST API with FastAPI** (5 initial endpoints)
- **Interactive API documentation** (Swagger UI)
- **Comprehensive test suite** (unit + integration tests)
- **Test fixtures** with sample eBay API responses
- **Configuration management** (settings.py, .env)

### Database Tables
- `cards` - Master card catalog
- `sales` - Historical transactions
- `active_listings` - Current market supply
- `price_trends` - Pre-computed metrics
- `psa_population` - Grading data (schema only)
- `social_signals` - Social media data (schema only)

### API Endpoints (Initial 5)
- `GET /health` - Health check
- `GET /api/trending` - Top trending cards
- `GET /api/trending/rookies` - Hot rookie cards
- `GET /api/cards/{id}` - Card details
- `GET /api/cards` - Search cards

### Automation
- APScheduler for daily collection at 2 AM
- Target list configuration (8 pre-configured players)
- Daily report generation
- Automated trend calculation

### Documentation
- System architecture with component diagrams
- Database ERD and design documentation
- Data flow diagrams (Mermaid format)
- API documentation (Swagger + README)
- Testing guide and test results
- Setup and installation guide
- Architecture Decision Records (ADR-001, ADR-002, ADR-003)
- Pipeline implementation guide
- Automation guide
- Deployment architecture
- User authentication roadmap

### Testing
- Unit tests for scraper and trend calculator
- Integration tests for database operations
- Test fixtures with sample data
- Test runner scripts (run_tests.sh)
- pytest configuration with coverage reporting

## [0.1.0] - 2025-02-11

### Added - Initial Setup
- Initial repository setup
- Facebook Marketplace acquisition module (NovaAct integration)
- Basic test structure
- Project documentation structure

---

## Version History

- **2.0.0** - Complete platform with inventory, watchlist, and frontend
- **1.0.0** - Backend data pipeline with API and automation
- **0.1.0** - Initial setup with Facebook Marketplace scraper

## Migration Guide

### Upgrading from 1.0.0 to 2.0.0

1. **Apply database migration:**
   ```bash
   psql -U postgres -d trading_cards -f backend/models/migration_001.sql
   ```

2. **Update dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Restart API server:**
   ```bash
   python3 -m backend.api.run
   ```

4. **Optional: Setup frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Breaking Changes

### 2.0.0
- None - All changes are additive

### 1.0.0
- Initial release - No breaking changes

## Deprecations

None

## Security

- All database credentials stored in environment variables
- SQL injection prevention via SQLAlchemy ORM
- Input validation on all API endpoints
- CORS configured for frontend integration

## Performance

- Database indexes on frequently queried columns
- Pre-computed metrics in price_trends table
- Efficient joins for inventory and watchlist queries
- Pagination support for large result sets

## Known Issues

- Node.js version 10.19.0 too old for frontend (requires 16+)
- eBay API approval pending for production use
- PSA population scraper not yet implemented
- Social media scrapers not yet implemented

## Roadmap

### Short Term (Next 2 Weeks)
- Enhanced profit calculator (shipping, grading fees)
- More data visualizations
- Improved trend detection algorithms
- PSA population scraper

### Medium Term (Next Month)
- Card Ladder integration
- Social media scrapers
- User authentication
- Production deployment

### Long Term (Next Quarter)
- Multi-user support
- Mobile app
- Email alerts
- Advanced analytics
- Machine learning for trend prediction

---

**Current Version:** 2.0.0  
**Last Updated:** 2025-02-11  
**Status:** ✅ Production Ready (pending deployment)
