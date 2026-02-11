# Database Design

## Overview

PostgreSQL database designed to store historical trading card data, sales transactions, and computed trend metrics.

## Entity Relationship Diagram

```
┌─────────────────┐
│     cards       │
│─────────────────│
│ id (PK)         │
│ player_name     │
│ card_year       │
│ card_set        │
│ card_number     │
│ is_rookie       │
│ sport           │
└────────┬────────┘
         │
         │ 1:N
         │
    ┌────┴─────────────────────────────────────┐
    │                                           │
    │                                           │
┌───▼──────────┐  ┌──────────────────┐  ┌──────▼─────────┐
│    sales     │  │ active_listings  │  │ price_trends   │
│──────────────│  │──────────────────│  │────────────────│
│ id (PK)      │  │ id (PK)          │  │ id (PK)        │
│ card_id (FK) │  │ card_id (FK)     │  │ card_id (FK)   │
│ sale_price   │  │ listing_price    │  │ trend_date     │
│ sale_date    │  │ listing_type     │  │ avg_price      │
│ ebay_item_id │  │ ebay_item_id     │  │ sales_count    │
│ condition    │  │ snapshot_date    │  │ velocity_score │
│ graded       │  └──────────────────┘  │ hotness_score  │
│ grade_value  │                        └────────────────┘
└──────────────┘
         │
         │
┌────────▼──────────┐  ┌──────────────────┐
│ psa_population    │  │ social_signals   │
│───────────────────│  │──────────────────│
│ id (PK)           │  │ id (PK)          │
│ card_id (FK)      │  │ card_id (FK)     │
│ grade_value       │  │ platform         │
│ population_count  │  │ mention_count    │
│ snapshot_date     │  │ sentiment_score  │
└───────────────────┘  │ signal_date      │
                       └──────────────────┘
```

## Table Descriptions

### cards
**Purpose:** Master table of all trading cards tracked by the system

**Key Fields:**
- `player_name` - Athlete name
- `card_year` - Year card was issued
- `is_rookie` - Boolean flag for rookie cards
- `sport` - Basketball, Baseball, Football, etc.

**Unique Constraint:** (player_name, card_year, card_set, card_number)

### sales
**Purpose:** Historical sales data from eBay and other marketplaces

**Key Fields:**
- `sale_price` - Final sale price
- `sale_date` - When the sale completed
- `ebay_item_id` - Unique eBay listing ID
- `graded` - Whether card is professionally graded
- `grade_company` - PSA, BGS, SGC, etc.
- `grade_value` - Numeric grade (e.g., 9.5)

**Indexes:**
- `(card_id, sale_date)` - For time-series queries
- `(sale_date)` - For daily aggregations

### active_listings
**Purpose:** Snapshot of current market supply

**Key Fields:**
- `listing_price` - Current asking price
- `listing_type` - 'auction' or 'buy_it_now'
- `snapshot_date` - When snapshot was taken

**Usage:** Calculate velocity score (sales / active listings)

### price_trends
**Purpose:** Pre-computed daily metrics for each card

**Key Fields:**
- `avg_price` - Average sale price for the day
- `sales_count` - Number of sales
- `active_listings_count` - Number of active listings
- `price_change_7d` - % change vs 7 days ago
- `velocity_score` - sales / listings ratio
- `hotness_score` - Composite trending metric

**Indexes:**
- `(trend_date)` - For date range queries
- `(hotness_score DESC)` - For "top trending" queries

### psa_population
**Purpose:** Track grading volume changes over time

**Key Fields:**
- `grade_value` - PSA grade (1-10)
- `population_count` - Total cards graded at this level
- `snapshot_date` - When data was scraped

**Usage:** Detect grading spikes (indicator of rising interest)

### social_signals
**Purpose:** Social media mentions and sentiment

**Key Fields:**
- `platform` - 'twitter', 'reddit', etc.
- `mention_count` - Number of mentions
- `sentiment_score` - -1 (negative) to 1 (positive)

**Usage:** Correlate social hype with price movements

## Data Flow

1. **Nightly Scrape** → Insert into `sales` and `active_listings`
2. **Daily Aggregation** → Compute `price_trends` metrics
3. **Weekly PSA Scrape** → Update `psa_population`
4. **Hourly Social Scrape** → Update `social_signals`
5. **API Queries** → Read from `price_trends` (pre-computed)

## Hotness Score Algorithm

```sql
hotness_score = (
    velocity_score * 0.4 +           -- Sales momentum
    price_change_7d * 0.3 +          -- Price acceleration
    psa_growth_rate * 0.2 +          -- Grading interest
    social_sentiment * 0.1           -- Hype factor
)
```

## Performance Considerations

- **Partitioning:** Consider partitioning `sales` by date for large datasets
- **Materialized Views:** `price_trends` acts as materialized view
- **Archival:** Archive sales older than 2 years to separate table

## Schema Version

**Current Version:** 1.0.0  
**Last Updated:** 2025-02-11  
**Schema File:** `backend/models/schema.sql`
