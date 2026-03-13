# Discovery System Pivot - Card Ladder Movers

## Problem Statement

**Original Approach**: eBay API-based discovery
- Searched 8 broad queries for trending cards
- Attempted to extract player names from item details
- Required 1,000+ API calls per discovery run

**Fatal Flaw**: eBay rate limiting (429 errors)
- Hit rate limits after 3-5 queries
- 2-second delays insufficient
- Makes daily automated discovery impossible

## New Approach: Card Ladder Movers

### Why Card Ladder?

Card Ladder's "Movers" page shows cards with highest price velocity - exactly what we need for arbitrage.

**Data Available**:
- Player names (structured, no parsing needed)
- Price velocity (% change over time periods)
- Current market prices
- Card set and year
- Sport/category

**Advantages**:
1. **Zero eBay API calls** - Web scraping only
2. **Pre-filtered signals** - Already sorted by momentum
3. **Structured data** - Player names in clean format
4. **Daily updates** - Aligns with our workflow
5. **Arbitrage-ready** - Price velocity IS the signal

### Implementation Plan

#### Phase 1: Card Ladder Scraper (NEW)
**File**: `backend/scrapers/cardladder_movers_scraper.py`

**Functionality**:
- Scrape https://www.cardladder.com/movers daily
- Extract top 50-100 gaining cards
- Parse player name, sport, year, set, price velocity
- Return structured discovery data

**Technology**: Selenium (site requires JavaScript)

#### Phase 2: Discovery Service Update
**File**: `backend/services/target_discovery.py`

**Changes**:
- Replace eBay discovery with Card Ladder movers
- Keep same discovery scoring algorithm
- Maintain targets.yaml auto-population
- Preserve manual favorites

#### Phase 3: Scheduler Update
**File**: `backend/run_discovery.py`

**Changes**:
- Point to new Card Ladder scraper
- Keep 1 AM daily schedule
- Add error handling for scraping failures

### Migration Path

1. **Build Card Ladder scraper** (this session)
2. **Test scraper** - Verify data quality
3. **Update discovery service** - Swap data source
4. **Deprecate eBay discovery** - Archive old approach
5. **Update all documentation** - Reflect new architecture

### Files to Create

- `backend/scrapers/cardladder_movers_scraper.py` - New scraper
- `docs/DISCOVERY-PIVOT.md` - This document
- `docs/CARDLADDER-MOVERS-INTEGRATION.md` - Integration guide

### Files to Update

- `backend/services/target_discovery.py` - Use Card Ladder data
- `backend/run_discovery.py` - Point to new scraper
- `CHANGELOG.md` - Document pivot
- `README.md` - Update data sources table
- `docs/PROJECT-STATUS.md` - Update Phase 2.5 status
- `docs/AUTOMATED-TARGET-DISCOVERY.md` - Update architecture
- `.amazonq/rules/memory-bank/product.md` - Update data sources

### Files to Archive

- `backend/scrapers/ebay_discovery_workaround.py` - Move to archive/
- `backend/test_ebay_fields.py` - Move to archive/
- `backend/test_product_api.py` - Move to archive/

## Expected Outcomes

### Before (eBay Discovery)
- 8 API queries
- 1,353 sales found
- 1,197 unique cards
- Hit rate limits after 3 queries
- 0 usable discoveries
- 20-40 minute runtime (if it worked)

### After (Card Ladder Movers)
- 1 web scrape
- 50-100 pre-filtered cards
- 100% have player names
- No rate limits
- 50-100 usable discoveries
- 30-60 second runtime

## Success Metrics

- [ ] Card Ladder scraper extracts 50+ cards
- [ ] 100% of cards have valid player names
- [ ] Discovery runs in under 2 minutes
- [ ] Zero eBay API calls for discovery
- [ ] targets.yaml auto-populated daily
- [ ] Scraper runs at 2 AM successfully

## Timeline

- **Session 1** (Current): Build Card Ladder scraper
- **Session 2**: Test and validate data quality
- **Session 3**: Integrate with discovery service
- **Session 4**: Update all documentation
- **Session 5**: Deploy and monitor

## Risk Mitigation

**Risk**: Card Ladder blocks scraping
**Mitigation**: Respectful scraping (1x per day), user agent rotation, fallback to manual targets

**Risk**: Site structure changes
**Mitigation**: Robust CSS selectors, error handling, alerts on failure

**Risk**: Data quality issues
**Mitigation**: Validation layer, manual review of first 10 runs

## Decision Record

**Date**: 2026-02-13
**Decision**: Pivot from eBay API discovery to Card Ladder movers scraping
**Rationale**: eBay rate limits make API-based discovery impossible
**Impact**: Complete redesign of discovery system
**Status**: In Progress
