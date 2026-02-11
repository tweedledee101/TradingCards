# Future Scrapers - Phase 2 Implementation

This directory will contain scrapers for additional data sources beyond eBay.

## Planned Scrapers

### 1. PSA Population Scraper (Priority: Critical)
**File:** `psa_scraper.py`  
**Purpose:** Track grading population and detect spikes  
**Data Source:** https://www.psacard.com/pop  
**Method:** Web scraping (no API available)  
**Update Frequency:** Weekly on Sundays  

**Key Metrics:**
- Total population by grade
- PSA 10 population
- PSA 10 rate (PSA 10 / Total)
- Week-over-week population growth
- Grading spike detection

**Database Table:** `psa_population` (already exists in schema)

---

### 2. Card Ladder Scraper (Priority: High)
**File:** `cardladder_scraper.py`  
**Purpose:** Price benchmarks and velocity tracking  
**Data Source:** https://www.cardladder.com  
**Method:** Web scraping or API (if available)  
**Update Frequency:** Daily at 2 AM  

**Key Metrics:**
- Benchmark prices by grade
- 7-day price velocity
- 30-day price velocity
- Market floor prices
- Price trend direction

**Database Table:** `price_benchmarks` (needs creation)

---

### 3. Terapeak Scraper (Priority: High)
**File:** `terapeak_scraper.py`  
**Purpose:** Sell-through rates and market demand  
**Data Source:** eBay Terapeak API  
**Method:** API integration (requires eBay seller account)  
**Update Frequency:** Daily at 2 AM  

**Key Metrics:**
- Sell-through rate (sold / listed)
- Average days to sell
- Successful listing rate
- Price optimization suggestions

**Database Table:** `sell_through_rates` (needs creation)

---

### 4. Twitter Scraper (Priority: Medium)
**File:** `twitter_scraper.py`  
**Purpose:** Social sentiment and hype detection  
**Data Source:** Twitter API v2  
**Method:** API integration (requires Twitter Developer account)  
**Update Frequency:** Every 4 hours  

**Key Metrics:**
- Mention count (last 24h)
- Sentiment score (-1 to 1)
- Engagement rate (likes + retweets)
- Influencer mentions
- Trending hashtags

**Database Table:** `social_signals` (already exists in schema)

---

### 5. Reddit Scraper (Priority: Medium)
**File:** `reddit_scraper.py`  
**Purpose:** Community sentiment and discussion tracking  
**Data Source:** Reddit API  
**Method:** API integration (PRAW library)  
**Update Frequency:** Every 4 hours  

**Subreddits to Monitor:**
- r/basketballcards
- r/baseballcards
- r/footballcards
- r/sportscards

**Key Metrics:**
- Post count (last 24h)
- Comment count
- Upvote ratio
- Sentiment score
- Hot thread detection

**Database Table:** `social_signals` (already exists in schema)

---

### 6. Release Calendar Scraper (Priority: Low)
**File:** `release_calendar.py`  
**Purpose:** Track upcoming product releases  
**Data Sources:**
- https://www.cardboardconnection.com/release-dates
- https://www.beckett.com/news/release-calendar

**Method:** Web scraping  
**Update Frequency:** Weekly on Mondays  

**Key Metrics:**
- Release date
- Manufacturer (Topps, Panini, etc.)
- Product name
- Sport
- Expected rookie class

**Database Table:** `release_calendar` (needs creation)

---

## Implementation Order

### Phase 2A: Critical Data Sources (Weeks 1-2)
1. **PSA Population Scraper** - Highest impact on accuracy

### Phase 2B: Price Intelligence (Weeks 3-4)
2. **Card Ladder Scraper** - Price benchmarks
3. **Terapeak Scraper** - Sell-through rates

### Phase 2C: Social Signals (Weeks 5-6)
4. **Twitter Scraper** - Social sentiment
5. **Reddit Scraper** - Community sentiment

### Phase 2D: Market Timing (Week 7)
6. **Release Calendar Scraper** - Product releases

---

## Database Schema Updates Needed

```sql
-- Sell-through rates (Terapeak)
CREATE TABLE sell_through_rates (
    id SERIAL PRIMARY KEY,
    card_id INTEGER REFERENCES cards(id),
    sell_through_rate DECIMAL(5,2),
    avg_days_to_sell INTEGER,
    successful_listings INTEGER,
    total_listings INTEGER,
    date_recorded DATE,
    source VARCHAR(50) DEFAULT 'terapeak'
);

-- Price benchmarks (Card Ladder)
CREATE TABLE price_benchmarks (
    id SERIAL PRIMARY KEY,
    card_id INTEGER REFERENCES cards(id),
    grade_company VARCHAR(10),
    grade_value DECIMAL(3,1),
    benchmark_price DECIMAL(10,2),
    price_velocity_7d DECIMAL(5,2),
    price_velocity_30d DECIMAL(5,2),
    market_floor DECIMAL(10,2),
    date_recorded DATE,
    source VARCHAR(50) DEFAULT 'cardladder'
);

-- Release calendar
CREATE TABLE release_calendar (
    id SERIAL PRIMARY KEY,
    release_date DATE,
    manufacturer VARCHAR(50),
    product_name VARCHAR(200),
    sport VARCHAR(50),
    rookie_class TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## API Keys Required

| Service | Key Type | Cost | Status |
|---------|----------|------|--------|
| eBay Browse API | OAuth Token | Free (5000 calls/day) | ✅ Have |
| eBay Terapeak | Seller Account | $21.95/mo | ⏳ Need |
| Twitter API | Developer Account | Free (500k tweets/mo) | ⏳ Need |
| Reddit API | App Registration | Free | ⏳ Need |
| PSA | None (web scraping) | Free | ✅ Ready |
| Card Ladder | None (web scraping) | Free | ✅ Ready |

---

## Testing Strategy

Each scraper should include:
- Unit tests for parsing logic
- Mock data fixtures
- Integration tests with real API calls
- Error handling tests
- Rate limit handling

Example test structure:
```
tests/
├── test_psa_scraper.py
├── test_cardladder_scraper.py
├── test_terapeak_scraper.py
├── test_twitter_scraper.py
├── test_reddit_scraper.py
└── fixtures/
    ├── psa_sample.html
    ├── cardladder_sample.json
    └── twitter_sample.json
```

---

## See Also

- [Gap Analysis](../../docs/TRADING-WORKFLOW-GAP-ANALYSIS.md) - Complete roadmap
- [System Architecture](../../docs/architecture/system-architecture.md) - Overall design
- [Project Status](../../docs/PROJECT-STATUS.md) - Current phase
