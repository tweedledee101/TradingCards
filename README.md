# Ragnarok Gaming - Trading Card Platform

A data-driven arbitrage opportunity finder for trading card dealers. Identifies profitable card flips by comparing eBay BIN and auction listings against SportsCardsPro market rates, 130point eBay sold comps, and eBay BIN comps with variant matching and volume filtering.

## How It Works

1. **Discover** top 40 players by eBay sales volume (45 seed players, ranked automatically)
2. **Catalog** all card variations per player from SportsCardsPro (100 variations/player with prices + volume)
3. **Filter** by SCP price range ($20-$1000) and volume (reject dead cards with rare/1-2 sales per year)
4. **Search** eBay for active BIN and auction listings matching each variation
5. **Validate** listings: player + year + card# + parallel in title, reject junk/reprints/factory sets/wrong sets
6. **Calculate** profit: SCP price - buy price - 13% eBay fees
7. **Store** opportunities in database with listing_type (BIN or auction), serve via API

## Current State (March 2026)

- **40 players** targeted and fully imported
- **25,434 cards**, 42,313 sales, 44,165 active listings, 4,400 SCP market rates
- **133 opportunities** from latest scan (BIN + Auctions)
- **167 tests passing** in CI (63 unit + 11 integration + 70 QA + frontend build)
- **Business Operating System**: goal tracking, daily plans, capital management, 12-month trajectory
- **Three-tier pricing**: SCP -> 130point sold comps -> eBay BIN comps
- **Unified pipeline**: one command runs BIN + Auction pipelines sequentially
- **Scheduled pipelines**: GitHub Actions cron (BIN 2AM/2PM ET, Auction 5AM/5PM ET, Daily Report 7PM ET)
- **Auction pipeline**: MLB Stats API for 2,269 player roster, 110 value+player eBay queries with pagination, SCP validation with multi-pass fuzzy matching
- **Pipeline quality filters**: price floor (30% of SCP), volume filter, factory set detection, reprint detection, wrong set detection, lot detection, suspicious price flagging
- **QA validation**: post-pipeline background rules (extreme_roi, card_number_mismatch, etc.) -- does not block pipeline
- **67 QA tests passing**: SCP matching (40), opportunity analyzer (19), API contract (8)
- **CI/CD**: GitHub Actions -- BIN, Auction, Daily Report, QA workflows (all green)
- **Multi-source pricing**: SCP primary, 130point sold comps (free, background worm), eBay BIN comps fallback
- **Snipe UI**: calculated recommended bid (SCP - fees - profit), live profit preview, Schedule Bid manual entry, My Bids strip
- **Dual database**: RDS primary + local PostgreSQL synced via `migrate.py --both` (24 migrations, 23 tables)
- **Observability**: structured logging, error tracking, job tracking, data retention
- **Infrastructure**: GitHub Actions workflows (BIN + Auction) + RDS deployed + ACM cert issued
- **Domain**: ragnarokgamez.com (ACM cert covers root + wildcard)
- **Sport**: Baseball (Basketball/Football seed players and sets ready)
- **UI**: Ragnarok Gaming dark theme (Trending + Opportunities + Business Dashboard pages live)
- **See [STATUS.md](./STATUS.md) for full details**

## Quick Start

```bash
cd /home/tweedledee101/TradingCards

# Run unified pipeline (BIN + Auction)
python3 find_opportunities.py --max-budget 200 --min-profit 10 --min-roi 20 --top-players 40

# Start services
nohup /usr/bin/python3 -m backend.api.run > /tmp/api.log 2>&1 &
cd frontend && nohup npm run dev > /tmp/frontend.log 2>&1 &

# Database migrations (keeps local + RDS in sync)
python3 migrate.py --both
```

See [PIPELINE-OPS.md](./PIPELINE-OPS.md) for all pipeline options and troubleshooting.

## Data Sources

| Source | Purpose | Status |
|--------|---------|--------|
| eBay Browse API | Sold listings, active listings (BIN + Auction), images | Working |
| SportsCardsPro | Market rates (Ungraded/Grade 9/PSA 10) + volume | Working (Selenium, graduated search) |
| 130point.com | eBay sold comps (actual sale prices + volume) | Working (HTTP POST, no auth) |
| MLB Stats API | Player roster identification (2,269 players) | Working (free, no auth) |
| PSA Population | Grading spikes | Infrastructure Ready |
| Card Ladder | Price velocity | Infrastructure Ready |

## Features

### Opportunity Finder (Primary)
- SCP-required for primary pricing; 130point sold comps and eBay BIN comps as fallbacks
- BIN + Auction: unified pipeline, one command runs both
- Lot detection: multiple # signs, X & Y & Z patterns, "N cards" language
- Volume filtering: rejects cards with "rare", "1 sale per year", "2 sales per year"
- Price floor: BIN below 30% of SCP hard-rejected (different product)
- Suspicious flagging: BIN between 30-50% of SCP flagged for "Needs Review"
- Factory set filter: complete set, montgomery club, walmart/target exclusive
- Reprint filter: replica, project 2020, shoebox treasures, sticker, ACEO
- Wrong set detection: rejects listings with mismatched set names
- Direct buy links: clickable eBay listing URLs with price and net profit
- Card images from eBay thumbnails
- SCP verification links for manual price checking
- All 3 SCP price tiers shown (Ungraded, Grade 9, PSA 10)

### Card Identity
- 80+ parallel variants extracted (Lime Green, Blue Foil Pattern II, Raywave Refractor, etc.)
- Insert set detection (Master Of The Game, 1986 Retro, Milestone, National Chicle, etc.)
- 79 card sets including 16 Leaf sub-sets
- Card numbers from titles
- Grading: PSA, BGS, SGC with grade values

### Portfolio & Watchlist
- Inventory tracking with P&L calculations
- Watchlist with target prices

## What's Next
- **Tighten volume filter** -- reject "3 sales per year" (every card at that level was a pass during validation)
- **Fix grade mismatch** -- compare ungraded-to-ungraded, graded-to-graded
- **Fix variant matching** -- "Magenta Speckle" != "Magenta"
- **Add minimum profit threshold** -- $6 profit isn't worth the research time
- **Expand auction pipeline player coverage** -- checklist scraping for broader player matching beyond 40 DB players
- **Worker separation** -- data gathering in separate process from core app (see [ADR-004](./docs/architecture/decisions/ADR-004-demand-driven-refresh.md))
- **Demand-driven refresh** -- no crons, data refreshes only when stale
- **Cross-validate SCP prices** -- check eBay sold data for high-value opportunities
- **eBay account integration** -- OAuth login, auto-import purchases, auto-track sales
- **Apply for eBay Compatible Application** -- upgrade from 5,000 to 50,000+ API calls/day
- Redesign Inventory, Watchlist, CardDetail pages (Ragnarok Gaming theme)
- AWS deployment (ECS + RDS + CloudFront)
- Basketball/Football support

See [ROADMAP.md](./docs/ROADMAP.md) for full feature roadmap with milestones.

## Documentation

- [STATUS.md](./STATUS.md) - Current project status (start here)
- [ROADMAP.md](./docs/ROADMAP.md) - Feature roadmap and milestones
- [PIPELINE-OPS.md](./PIPELINE-OPS.md) - Pipeline operations guide
- [KNOWN-ISSUES.md](./docs/KNOWN-ISSUES.md) - Documented false positive patterns
- [Opportunity Finder](./docs/OPPORTUNITY-FINDER.md) - How arbitrage scoring works
- [Architecture](./docs/architecture/) - System design, database schema, data flow
- [ADR-004](./docs/architecture/decisions/ADR-004-demand-driven-refresh.md) - Demand-driven refresh (no crons)
- [API Docs](http://localhost:8000/docs) - Swagger UI (when API is running)

## Domain

**`ragnarokgamez.com`** (planned)
