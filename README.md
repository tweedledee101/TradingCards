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
3. **REST API** - Expose trending cards and analytics
4. **Frontend Dashboard** - Visualization (future phase)

## Data Sources

| Source | Purpose | Status |
|--------|---------|--------|
| eBay Browse API | Sold listings, price data | ✅ Complete |
| eBay Active Listings | Current market supply | ✅ Complete |
| PSA Population | Grading volume trends | Planned |
| Card Ladder | Price benchmarks | Planned |
| Twitter/Reddit | Social sentiment | Planned |

## Documentation

- [Quick Start Guide](./QUICKSTART.md)
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

## Quick Start

```bash
# 1. Install all dependencies
./setup.sh  # Linux/Mac
setup.bat   # Windows

# 2. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys and database credentials

# Setup database
psql -U postgres -c "CREATE DATABASE trading_cards;"
psql -U postgres -f backend/models/schema.sql

# Test pipeline with mock data
python backend/test_pipeline.py

# Run pipeline with real eBay data
python -m backend.run_pipeline --query "Wembanyama rookie" --days 7

# Start API server
python -m backend.api.run
# Visit http://localhost:8000/docs for interactive API docs

# Test API
python backend/test_api.py

# Run automated collection (test mode)
python -m backend.run_scheduler --now

# Start scheduler (runs daily at 2 AM)
python -m backend.run_scheduler

# Run tests
./run_tests.sh all
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

**Current Phase:** Automation - COMPLETE ✅

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
- [ ] PSA population scraper
- [ ] Frontend dashboard

## Domain

Platform will be hosted at: `<subdomain>.jgaffiliates.com` (subdomain TBD)

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development workflow and standards.

## License

[License TBD]
