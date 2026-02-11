# Future Services - Phase 3 Implementation

This directory will contain decision engines and intelligence services for Phase 3.

## Existing Services ✅

- `data_pipeline.py` - Pipeline orchestration
- `trend_calculator.py` - Velocity, momentum, hotness scoring
- `automated_collector.py` - Scheduled data collection
- `report_generator.py` - Daily CSV/text reports
- `scheduler.py` - APScheduler configuration

---

## Planned Services (Phase 3)

### 1. Intelligence Engine (Priority: Critical)
**File:** `intelligence_engine.py`  
**Purpose:** Aggregate all data sources into unified intelligence  
**Dependencies:** All Phase 2 scrapers  

**Key Functions:**
```python
class IntelligenceEngine:
    def aggregate_all_sources(self, card_id: int) -> Dict:
        """Combine eBay + PSA + Card Ladder + Terapeak + Social"""
        
    def detect_anomalies(self, card_id: int) -> List[Anomaly]:
        """Detect sudden spikes, unusual patterns"""
        
    def calculate_opportunity_score(self, card_id: int) -> float:
        """7-factor opportunity scoring (0-100)"""
        
    def get_market_context(self, card_id: int) -> MarketContext:
        """Overall market conditions for this card"""
```

**Opportunity Score Algorithm:**
```python
opportunity = (
    hotness * 0.25 +           # eBay trends
    sell_through * 0.20 +      # Terapeak
    price_velocity * 0.15 +    # Card Ladder
    grading_spike * 0.15 +     # PSA
    social_momentum * 0.15 +   # Twitter/Reddit
    release_timing * 0.10      # Calendar
)
```

---

### 2. Buy Decision Engine (Priority: Critical)
**File:** `buy_decision_engine.py`  
**Purpose:** Calculate optimal entry prices for cards  
**Dependencies:** `intelligence_engine.py`, `price_benchmarks` table  

**Key Functions:**
```python
class BuyDecisionEngine:
    def calculate_buy_zone(self, card_id: int) -> BuyZone:
        """
        Returns optimal buy price range
        
        Example:
        {
            'target_price': 85.00,
            'max_price': 95.00,
            'confidence': 0.85,
            'reasoning': 'Price 15% below 7-day avg, high velocity'
        }
        """
        
    def get_historical_floor(self, card_id: int) -> float:
        """Historical lowest price (last 90 days)"""
        
    def predict_price_direction(self, card_id: int) -> str:
        """'rising', 'falling', 'stable'"""
        
    def should_buy_now(self, card_id: int, current_price: float) -> bool:
        """True if current price is in buy zone"""
```

**Buy Zone Algorithm:**
```python
# Calculate 7-day and 30-day averages
avg_7d = get_avg_price(card_id, days=7)
avg_30d = get_avg_price(card_id, days=30)

# Determine buy zone based on velocity
if velocity_score > 70:  # Hot card
    buy_zone = avg_7d * 0.85  # Buy at 85% of avg
elif velocity_score > 40:  # Moderate
    buy_zone = avg_7d * 0.75  # Buy at 75% of avg
else:  # Cold card
    buy_zone = avg_7d * 0.60  # Buy at 60% of avg

# Factor in price trend
if price_trending_up:
    buy_zone *= 1.10  # Accept 10% higher if rising
```

---

### 3. Sell Strategy Engine (Priority: Critical)
**File:** `sell_strategy_engine.py`  
**Purpose:** Determine optimal exit strategy (grade vs. raw, timing)  
**Dependencies:** `intelligence_engine.py`, `psa_population` table  

**Key Functions:**
```python
class SellStrategyEngine:
    def calculate_grade_roi(self, card_id: int, purchase_price: float) -> GradeROI:
        """
        Compare grade vs. raw profit
        
        Returns:
        {
            'grade_and_sell': {
                'expected_grade': 9.5,
                'psa_10_rate': 0.35,
                'graded_value': 450.00,
                'grading_cost': 25.00,
                'net_profit': 375.00,
                'roi': 250%
            },
            'sell_raw': {
                'raw_value': 200.00,
                'net_profit': 150.00,
                'roi': 100%
            },
            'recommendation': 'grade_and_sell'
        }
        """
        
    def get_psa_10_rate(self, card_id: int) -> float:
        """Historical PSA 10 rate for this card"""
        
    def calculate_timing_score(self, card_id: int) -> TimingScore:
        """Should you sell now or hold?"""
        
    def get_exit_strategy(self, card_id: int, purchase_price: float) -> Strategy:
        """Complete exit strategy with timing"""
```

**Grade vs. Raw Decision:**
```python
# Get PSA 10 rate from population data
psa_10_rate = get_psa_10_rate(card_id)

# Get price premiums
raw_price = get_avg_price(card_id, graded=False)
psa_10_price = get_avg_price(card_id, grade_company='PSA', grade_value=10)

# Calculate expected values
grading_cost = 25.00  # PSA regular service
expected_graded_value = psa_10_price * psa_10_rate
expected_raw_value = raw_price

# Compare ROI
grade_roi = (expected_graded_value - grading_cost - purchase_price) / purchase_price
raw_roi = (expected_raw_value - purchase_price) / purchase_price

# Recommend grading if:
# 1. PSA 10 rate > 30%
# 2. Grade ROI > Raw ROI + 50%
# 3. PSA 10 premium > 2x raw price
```

---

### 4. Morning Report Generator (Priority: High)
**File:** `morning_report_generator.py`  
**Purpose:** Generate daily actionable intelligence briefing  
**Dependencies:** All Phase 3 engines  

**Key Functions:**
```python
class MorningReportGenerator:
    def generate_daily_briefing(self) -> DailyBriefing:
        """
        Complete morning intelligence report
        
        Returns:
        {
            'date': '2024-01-15',
            'top_opportunities': [
                {
                    'card': 'Wembanyama 2023 Prizm RC PSA 10',
                    'opportunity_score': 87.5,
                    'buy_price': 450.00,
                    'current_floor': 425.00,
                    'action': 'BUY NOW',
                    'sell_strategy': 'Hold 30 days, sell as single',
                    'expected_roi': '45%',
                    'reasoning': 'Grading spike +25%, social momentum high'
                },
                # ... 9-19 more cards
            ],
            'market_summary': {
                'hot_players': ['Wembanyama', 'Henderson'],
                'cooling_players': ['Miller'],
                'trending_sets': ['Prizm', 'Optic']
            }
        }
        """
        
    def send_email_report(self, email: str):
        """Email daily briefing"""
        
    def save_to_file(self, format: str = 'pdf'):
        """Save as PDF or HTML"""
```

**Report Structure:**
```
DAILY TRADING INTELLIGENCE REPORT
Date: January 15, 2024

=== TOP 10 OPPORTUNITIES ===

1. Victor Wembanyama 2023 Prizm RC PSA 10
   Opportunity Score: 87.5 🔥
   
   BUY DECISION:
   - Target Price: $450 or below
   - Current Floor: $425 ✅ IN BUY ZONE
   - Confidence: 85%
   
   SELL STRATEGY:
   - Strategy: Hold 30 days, sell as single
   - Expected Sale Price: $650
   - Expected ROI: 45%
   
   REASONING:
   - PSA population spike +25% (grading rush)
   - Social mentions up 150% (Twitter hype)
   - Sell-through rate: 78% (high demand)
   - Price velocity: +12% week-over-week

2. [Next card...]

=== MARKET SUMMARY ===
- Hot Players: Wembanyama, Henderson, Holliday
- Cooling: Miller, Williams
- Trending Sets: Prizm, Optic, Bowman Chrome
```

---

### 5. Alert System (Priority: Medium)
**File:** `alert_system.py`  
**Purpose:** Notify when cards hit buy zones or watchlist targets  
**Dependencies:** `buy_decision_engine.py`, `watchlist` table  

**Key Functions:**
```python
class AlertSystem:
    def check_buy_zone_alerts(self) -> List[Alert]:
        """Check if any cards entered buy zones"""
        
    def check_watchlist_alerts(self) -> List[Alert]:
        """Check watchlist price targets"""
        
    def send_alerts(self, alerts: List[Alert], method: str = 'email'):
        """Send via email, SMS, or push notification"""
```

---

## Database Schema Updates (Phase 3)

```sql
-- Buy recommendations
CREATE TABLE buy_recommendations (
    id SERIAL PRIMARY KEY,
    card_id INTEGER REFERENCES cards(id),
    target_price DECIMAL(10,2),
    max_price DECIMAL(10,2),
    confidence DECIMAL(3,2),
    reasoning TEXT,
    date_generated DATE,
    expires_at DATE
);

-- Sell strategies
CREATE TABLE sell_strategies (
    id SERIAL PRIMARY KEY,
    card_id INTEGER REFERENCES cards(id),
    strategy_type VARCHAR(50),  -- 'grade_and_sell', 'sell_raw', 'hold'
    expected_sale_price DECIMAL(10,2),
    expected_roi DECIMAL(5,2),
    timing_recommendation VARCHAR(100),
    reasoning TEXT,
    date_generated DATE
);

-- Alerts log
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(50),  -- 'buy_zone', 'watchlist', 'opportunity'
    card_id INTEGER REFERENCES cards(id),
    message TEXT,
    sent_at TIMESTAMP,
    method VARCHAR(20)  -- 'email', 'sms', 'push'
);
```

---

## Implementation Timeline

### Week 7-8: Intelligence Engine
- [ ] Multi-source data aggregation
- [ ] Opportunity scoring algorithm
- [ ] Anomaly detection
- [ ] Unit tests

### Week 9: Buy Decision Engine
- [ ] Buy zone calculator
- [ ] Historical floor analysis
- [ ] Price direction prediction
- [ ] Integration tests

### Week 10: Sell Strategy Engine
- [ ] Grade vs. raw ROI calculator
- [ ] PSA 10 rate analysis
- [ ] Market timing signals
- [ ] Integration tests

### Week 11: Morning Report
- [ ] Report generator
- [ ] Email delivery
- [ ] PDF export
- [ ] Automated daily run

### Week 12: Alert System
- [ ] Buy zone alerts
- [ ] Watchlist alerts
- [ ] Email/SMS integration
- [ ] Alert history tracking

---

## Testing Requirements

Each service must include:
- Unit tests (>80% coverage)
- Integration tests with database
- Mock data fixtures
- Performance tests (response time <500ms)
- Error handling tests

---

## See Also

- [Gap Analysis](../../docs/TRADING-WORKFLOW-GAP-ANALYSIS.md) - Complete roadmap
- [System Architecture](../../docs/architecture/system-architecture.md) - Overall design
- [Project Status](../../docs/PROJECT-STATUS.md) - Current phase
