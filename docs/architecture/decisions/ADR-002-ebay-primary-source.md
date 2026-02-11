# ADR-002: eBay as Primary Data Source

**Date:** 2025-02-11  
**Status:** Accepted  
**Deciders:** Development Team

## Context

We need reliable, comprehensive sales data to detect trending trading cards. Multiple marketplaces exist:

- eBay
- COMC (Check Out My Cards)
- StockX
- Goldin Auctions
- PWCC Marketplace
- Facebook Marketplace

## Decision

We will use **eBay Browse API** as our primary data source, supplemented by other sources.

## Rationale

### Why eBay Primary?

1. **Largest Volume:** 80%+ of online card sales happen on eBay
2. **Official API:** eBay Browse API provides structured access to sold listings
3. **Historical Data:** Can query sold listings up to 90 days back
4. **Comprehensive:** Includes graded and raw cards, all sports
5. **Price Discovery:** True market prices (auctions + BIN)

### Why Not Others as Primary?

**COMC:**
- Smaller volume
- Mostly consignment, not true market prices
- No public API

**StockX:**
- Limited to high-end cards
- Opaque pricing
- No API access

**Goldin/PWCC:**
- Auction houses, not continuous market
- High-end only
- Delayed data

**Facebook Marketplace:**
- Already have NovaAct scraper (see `acquisition/facebook_marketplace/`)
- Good for local deals, but inconsistent data
- Use as supplementary source

## Implementation Strategy

### Phase 1: eBay Only
- Build robust eBay scraper
- Validate trend detection algorithms
- Prove concept with single source

### Phase 2: Add Supplementary Sources
- PSA population data (grading trends)
- Card Ladder (price benchmarks)
- Social signals (Twitter/Reddit)

### Phase 3: Additional Marketplaces
- COMC sales velocity
- Facebook Marketplace (integrate existing NovaAct scraper)
- StockX (if API becomes available)

## eBay API Details

**Endpoint:** `https://api.ebay.com/buy/browse/v1/item_summary/search`

**Key Parameters:**
- `q` - Search query (e.g., "Wembanyama rookie PSA 10")
- `filter` - Date range, buying options, condition
- `sort` - Sort by end date, price, etc.
- `limit` - Results per page (max 200)

**Rate Limits:**
- 5,000 calls/day (free tier)
- 100,000 calls/day (paid tier)

**Data Returned:**
- Item ID, title, price
- Sale date, condition
- Buying option (auction/BIN)
- Seller info

## Consequences

**Positive:**
- Official API = reliable, structured data
- Large sample size for statistical significance
- Can detect trends before they hit other platforms
- Well-documented API

**Negative:**
- Rate limits may constrain scraping frequency
- API costs if we exceed free tier
- eBay-specific quirks (title parsing, etc.)
- Need to handle API changes/deprecations

**Neutral:**
- Will need eBay developer account
- Must comply with eBay API terms of service
- Data quality depends on seller listing accuracy

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| API rate limits | Cache results, optimize queries, upgrade tier if needed |
| API downtime | Retry logic, queue failed requests |
| Data quality | Robust title parsing, outlier detection |
| API changes | Version pinning, monitor eBay developer updates |
| Terms of service | Review ToS, ensure compliance, no reselling data |

## Related Decisions

- ADR-003: Supplementary data sources (planned)
- ADR-004: Scraping schedule and frequency (planned)

## References

- [eBay Browse API Documentation](https://developer.ebay.com/api-docs/buy/browse/overview.html)
- [eBay Developer Program](https://developer.ebay.com/)
