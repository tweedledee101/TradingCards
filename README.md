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
| eBay Browse API | Sold listings, price data | In Progress |
| eBay Active Listings | Current market supply | Planned |
| PSA Population | Grading volume trends | Planned |
| Card Ladder | Price benchmarks | Planned |
| Twitter/Reddit | Social sentiment | Planned |

## Documentation

- [System Architecture](./docs/architecture/system-architecture.md)
- [Database Schema & ERD](./docs/architecture/database-design.md)
- [Data Flow Diagrams](./docs/architecture/diagrams/)
- [Testing Guide](./docs/TESTING.md)
- [API Documentation](./docs/api/)
- [Setup Guide](./docs/setup/installation.md)
- [Architecture Decisions](./docs/architecture/decisions/)
- [Project Status](./docs/PROJECT-STATUS.md)

## Quick Start

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and database credentials

# Setup database
psql -U postgres -c "CREATE DATABASE trading_cards;"
psql -U postgres -f backend/models/schema.sql

# Test pipeline with mock data
python backend/test_pipeline.py

# Run pipeline with real eBay data
python -m backend.run_pipeline --query "Wembanyama rookie" --days 7

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

**Current Phase:** Backend Data Pipeline Development

- [x] Database schema design
- [x] Project structure
- [x] eBay scraper implementation
- [x] Comprehensive test suite
- [ ] Trend detection algorithms
- [ ] PSA population scraper
- [ ] API endpoints
- [ ] Frontend dashboard

## Domain

Platform will be hosted at: `<subdomain>.jgaffiliates.com` (subdomain TBD)

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development workflow and standards.

## License

[License TBD]
