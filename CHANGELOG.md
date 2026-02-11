# Changelog

All notable changes to the Trading Card Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure
- PostgreSQL database schema with 6 core tables
- Documentation structure (architecture, API, deployment)
- Database ERD and design documentation
- System architecture documentation with data flow diagrams
- ADR-001: PostgreSQL database decision
- ADR-002: eBay as primary data source
- Backend configuration management (settings.py)
- Environment variable template (.env.example)
- Python requirements.txt with core dependencies
- Project README with overview and quick start

### In Progress
- eBay Browse API scraper implementation
- Trend detection algorithms (velocity, momentum, hotness score)

### Planned
- [ ] Complete eBay scraper with title parsing
- [ ] Database connection utilities
- [ ] Nightly scraper scheduler
- [ ] PSA population scraper
- [ ] Card Ladder price scraper
- [ ] Social media signal scrapers (Twitter/Reddit)
- [ ] Trend calculation batch job
- [ ] REST API with FastAPI
- [ ] API endpoints for trending cards
- [ ] Frontend dashboard (React)
- [ ] Deployment to jgaffiliates.com subdomain

## [0.1.0] - 2025-02-11

### Added
- Initial repository setup
- Facebook Marketplace acquisition module (NovaAct integration)
- Basic test structure

---

## Version History

- **0.1.0** - Initial setup with Facebook Marketplace scraper
- **Unreleased** - Backend data pipeline development

## Notes

- Project is in active development
- Backend data pipeline is current focus
- Frontend development will begin after data pipeline is stable
- Subdomain name for jgaffiliates.com TBD
