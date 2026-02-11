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
    D --> D2[Sales Count]
    D --> D3[Price Change 7d]
    D --> D4[Price Change 30d]
    
    D1 --> E[Query active_listings]
    D2 --> E
    E --> F[Calculate Velocity Score]
    F --> G[velocity = sales / listings]
    
    G --> H[Query psa_population]
    H --> I[Calculate PSA Growth Rate]
    
    I --> J[Query social_signals]
    J --> K[Get Sentiment Score]
    
    K --> L[Compute Hotness Score]
    L --> M[hotness = velocity*0.4 + momentum*0.3 + psa*0.2 + social*0.1]
    
    M --> N[Insert into price_trends table]
    N --> O[Update API Cache]
```

## 3. API Request Flow

```mermaid
graph LR
    A[Client Request] --> B[FastAPI Endpoint]
    B --> C{Endpoint Type}
    
    C -->|/trending| D[Query price_trends]
    C -->|/cards/:id| E[Query cards + sales]
    C -->|/rookies/hot| F[Query price_trends WHERE is_rookie=true]
    
    D --> G[ORDER BY hotness_score DESC]
    E --> H[JOIN with price_trends]
    F --> I[LIMIT 50]
    
    G --> J[Format JSON Response]
    H --> J
    I --> J
    
    J --> K[Return to Client]
```

## 4. Complete Data Pipeline

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
        B1[eBay Scraper]
        B2[PSA Scraper]
        B3[Card Ladder Scraper]
        B4[Social Scraper]
    end
    
    subgraph "Database Tables"
        C1[(cards)]
        C2[(sales)]
        C3[(active_listings)]
        C4[(psa_population)]
        C5[(social_signals)]
        C6[(price_trends)]
    end
    
    subgraph "Processing"
        D1[Trend Calculator]
        D2[Hotness Score Engine]
    end
    
    subgraph "API Layer"
        E1[FastAPI Endpoints]
    end
    
    subgraph "Clients"
        F1[Frontend Dashboard]
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
    B2 --> C4
    B4 --> C5
    
    C1 --> D1
    C2 --> D1
    C3 --> D1
    C4 --> D1
    C5 --> D1
    
    D1 --> D2
    D2 --> C6
    
    C6 --> E1
    C1 --> E1
    C2 --> E1
    
    E1 --> F1
    E1 --> F2
    E1 --> F3
```

## 5. Hotness Score Calculation Detail

```mermaid
graph TD
    A[Start: Card ID] --> B[Get Last 7 Days Sales]
    B --> C[Calculate Average Price]
    
    C --> D[Get Price 7 Days Ago]
    D --> E[Calculate Price Momentum]
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

## 6. Error Handling Flow

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

## Diagram Notes

- **Mermaid Format:** These diagrams can be rendered in GitHub, GitLab, or any Markdown viewer that supports Mermaid
- **Live Editing:** Use [Mermaid Live Editor](https://mermaid.live/) to modify diagrams
- **Export:** Can export to PNG/SVG for documentation

## Timing Schedule

| Job | Frequency | Duration | Dependencies |
|-----|-----------|----------|--------------|
| eBay Sold Scraper | Daily 2:00 AM | ~15 min | None |
| eBay Active Scraper | Daily 2:30 AM | ~10 min | None |
| Trend Calculator | Daily 3:00 AM | ~20 min | Sales + Listings data |
| PSA Scraper | Weekly Sunday 1:00 AM | ~30 min | None |
| Social Scraper | Every 4 hours | ~5 min | None |
| API Cache Refresh | Daily 3:30 AM | ~2 min | Trend Calculator |

## Data Retention

| Table | Retention | Archive Strategy |
|-------|-----------|------------------|
| sales | 2 years | Move to sales_archive after 2 years |
| active_listings | 90 days | Delete after 90 days |
| price_trends | Indefinite | Keep all historical trends |
| psa_population | Indefinite | Keep all snapshots |
| social_signals | 6 months | Aggregate and delete raw data |

## Version

**Last Updated:** 2025-02-11  
**Diagram Version:** 1.0.0
