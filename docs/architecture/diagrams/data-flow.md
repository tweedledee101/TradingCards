# Data Flow Diagrams

## Overview

This document contains data flow diagrams showing how data moves through the Trading Card Platform.

## 1. Nightly Scraping Pipeline

```mermaid
graph TD
    A[Cron Job 2:00 AM] --> B[eBay Scraper]
    B --> C{API Call Successful?}
    C -->|Yes| D[Parse JSON Response]
    C -->|No| E[Log Error & Retry]
    E --> B
    
    D --> F[Extract Card Info from Titles]
    F --> G{Card Exists in DB?}
    
    G -->|No| H[Insert into cards table]
    G -->|Yes| I[Get card_id]
    H --> I
    
    I --> J[Insert into sales table]
    J --> K[Update timestamp]
    
    K --> L[Scrape Active Listings]
    L --> M[Insert into active_listings table]
    
    M --> N[Trigger Trend Calculator]
```

## 2. Trend Detection Flow

```mermaid
graph TD
    A[Daily Batch Job 3:00 AM] --> B[Query sales table]
    B --> C[Group by card_id and date]
    
    C --> D[Calculate Metrics]
    D --> D1[Average Price]
    D --> D2[Median Price]
    D --> D3[Sales Count]
    D --> D4[Price Change 7d]
    
    D1 --> E[Query active_listings]
    D2 --> E
    D3 --> E
    E --> F[Calculate Velocity Score]
    F --> G[velocity = sales / listings]
    
    G --> H[Calculate Momentum Score]
    H --> I[momentum = price change %]
    
    I --> J[Query psa_population]
    J --> K[Calculate PSA Growth Rate]
    
    K --> L[Query social_signals]
    L --> M[Get Sentiment Score]
    
    M --> N[Compute Hotness Score]
    N --> O[hotness = velocity*0.4 + momentum*0.3 + psa*0.2 + social*0.1]
    
    O --> P[Insert into price_trends table]
    P --> Q[Update API Cache]
```

## 3. API Request Flow

```mermaid
graph LR
    A[Client Request] --> B[FastAPI Endpoint]
    B --> C{Endpoint Type}
    
    C -->|/trending| D[Query price_trends with filters]
    C -->|/cards/:id| E[Query cards + sales + trends]
    C -->|/inventory| F[Query inventory + cards + trends]
    C -->|/watchlist| G[Query watchlist + cards + trends]
    
    D --> H[Apply filters & sorting]
    E --> I[Join with price history]
    F --> J[Calculate P&L]
    G --> K[Check alerts]
    
    H --> L[Format JSON Response]
    I --> L
    J --> L
    K --> L
    
    L --> M[Return to Client]
```

## 4. Inventory Management Flow

```mermaid
graph TD
    A[User Action] --> B{Action Type}
    
    B -->|Add to Inventory| C[POST /api/inventory]
    C --> D[Validate card_id exists]
    D --> E[Insert into inventory table]
    E --> F[Set status = owned]
    F --> G[Return inventory_id]
    
    B -->|Record Sale| H[POST /api/inventory/sales]
    H --> I[Get inventory item]
    I --> J[Calculate net_profit]
    J --> K[Calculate ROI %]
    K --> L[Insert into inventory_sales]
    L --> M[Update inventory status = sold]
    M --> N[Return profit metrics]
    
    B -->|View Portfolio| O[GET /api/inventory/stats]
    O --> P[Sum purchase prices]
    P --> Q[Get current values from price_trends]
    Q --> R[Calculate unrealized profit]
    R --> S[Sum realized profit from sales]
    S --> T[Calculate total ROI]
    T --> U[Return portfolio stats]
```

## 5. Watchlist & Alert Flow

```mermaid
graph TD
    A[User Action] --> B{Action Type}
    
    B -->|Add to Watchlist| C[POST /api/watchlist]
    C --> D[Validate card_id]
    D --> E[Insert into watchlist table]
    E --> F[Set target_price & threshold]
    F --> G[Return watchlist_id]
    
    B -->|Check Alerts| H[GET /api/watchlist/alerts]
    H --> I[Query watchlist + price_trends]
    I --> J{For each card}
    J --> K[Get current_price]
    K --> L[Compare with target_price]
    L --> M{Within threshold?}
    M -->|Yes| N[Add to alerts list]
    M -->|No| O[Skip]
    N --> P[Return alerts]
    O --> P
    
    B -->|View Watchlist| Q[GET /api/watchlist]
    Q --> R[Join watchlist + cards + trends]
    R --> S[Calculate price differences]
    S --> T[Check alert status]
    T --> U[Return watchlist with alerts]
```

## 6. Complete Data Pipeline

```mermaid
graph TB
    subgraph "Data Sources"
        A1[eBay API]
        A2[PSA Website]
        A3[Card Ladder]
        A4[Twitter API]
        A5[Reddit API]
    end
    
    subgraph "Scrapers"
        B1[eBay Scraper ✅]
        B2[PSA Scraper ⏳]
        B3[Card Ladder Scraper ⏳]
        B4[Social Scraper ⏳]
    end
    
    subgraph "Database Tables"
        C1[(cards)]
        C2[(sales)]
        C3[(active_listings)]
        C4[(price_trends)]
        C5[(inventory)]
        C6[(inventory_sales)]
        C7[(watchlist)]
        C8[(psa_population)]
        C9[(social_signals)]
    end
    
    subgraph "Processing"
        D1[Trend Calculator]
        D2[Hotness Score Engine]
        D3[P&L Calculator]
        D4[Alert Checker]
    end
    
    subgraph "API Layer"
        E1[FastAPI - 18 Endpoints]
    end
    
    subgraph "Clients"
        F1[React Frontend]
        F2[Mobile App]
        F3[External API Users]
    end
    
    A1 --> B1
    A2 --> B2
    A3 --> B3
    A4 --> B4
    A5 --> B4
    
    B1 --> C1
    B1 --> C2
    B1 --> C3
    B2 --> C8
    B4 --> C9
    
    C1 --> D1
    C2 --> D1
    C3 --> D1
    C8 --> D1
    C9 --> D1
    
    D1 --> D2
    D2 --> C4
    
    C5 --> D3
    C6 --> D3
    C4 --> D3
    
    C7 --> D4
    C4 --> D4
    
    C1 --> E1
    C2 --> E1
    C4 --> E1
    C5 --> E1
    C6 --> E1
    C7 --> E1
    
    E1 --> F1
    E1 --> F2
    E1 --> F3
```

## 7. Hotness Score Calculation Detail

```mermaid
graph TD
    A[Start: Card ID] --> B[Get Last 7 Days Sales]
    B --> C[Calculate Average Price]
    
    C --> D[Get Price 7 Days Ago]
    D --> E[Calculate Momentum Score]
    E --> F[momentum = current - old / old * 100]
    
    A --> G[Get Active Listings Count]
    B --> H[Get Sales Count]
    G --> I[Calculate Velocity]
    H --> I
    I --> J[velocity = sales / listings]
    
    A --> K[Get PSA Population This Week]
    A --> L[Get PSA Population Last Week]
    K --> M[Calculate PSA Growth]
    L --> M
    M --> N[psa_growth = this_week - last_week / last_week * 100]
    
    A --> O[Get Social Mentions]
    O --> P[Get Sentiment Score]
    P --> Q[social_score = mentions * sentiment]
    
    F --> R[Combine Scores]
    J --> R
    N --> R
    Q --> R
    
    R --> S[hotness = velocity*0.4 + momentum*0.3 + psa*0.2 + social*0.1]
    S --> T[Normalize to 0-100]
    T --> U[Store in price_trends]
```

## 8. Error Handling Flow

```mermaid
graph TD
    A[Scraper Runs] --> B{API Available?}
    B -->|No| C[Log Error]
    C --> D[Wait 5 minutes]
    D --> E{Retry Count < 3?}
    E -->|Yes| A
    E -->|No| F[Send Alert Email]
    F --> G[Skip This Run]
    
    B -->|Yes| H{Valid Response?}
    H -->|No| C
    H -->|Yes| I[Parse Data]
    
    I --> J{Data Quality Check}
    J -->|Fail| K[Log Warning]
    K --> L[Store with flag]
    J -->|Pass| M[Store in Database]
    
    M --> N{DB Write Success?}
    N -->|No| O[Rollback Transaction]
    O --> C
    N -->|Yes| P[Update Last Run Timestamp]
```

## Timing Schedule

| Job | Frequency | Duration | Dependencies |
|-----|-----------|----------|--------------|
| eBay Sold Scraper | Daily 2:00 AM | ~15 min | None |
| eBay Active Scraper | Daily 2:30 AM | ~10 min | None |
| Trend Calculator | Daily 3:00 AM | ~20 min | Sales + Listings data |
| Report Generator | Daily 3:30 AM | ~5 min | Trend Calculator |
| PSA Scraper | Weekly Sunday 1:00 AM | ~30 min | None |
| Social Scraper | Every 4 hours | ~5 min | None |
| Alert Checker | Hourly | ~2 min | Watchlist + Trends |

## Data Retention

| Table | Retention | Archive Strategy |
|-------|-----------|------------------|
| sales | 2 years | Move to sales_archive after 2 years |
| active_listings | 90 days | Delete after 90 days |
| price_trends | Indefinite | Keep all historical trends |
| inventory | Indefinite | Keep all records |
| inventory_sales | Indefinite | Keep all sales history |
| watchlist | Indefinite | User-managed |
| psa_population | Indefinite | Keep all snapshots |
| social_signals | 6 months | Aggregate and delete raw data |

## Version

**Last Updated:** 2025-02-11  
**Diagram Version:** 2.0.0  
**Status:** ✅ Current
