# Opportunity Finder - Arbitrage + Momentum System

**Replaces "Trending Cards" with actionable arbitrage opportunities**

---

## Philosophy

Professional card dealers don't chase "hot" cards - they find **arbitrage opportunities** where they can buy below market rate and flip for profit. Momentum signals (price trends, sales velocity) provide **confidence**, not the primary decision.

### Decision Framework

**Primary Filter: Arbitrage (70% weight)**
- Can I buy this card below market rate?
- Will I profit after eBay/PayPal fees (13%)?
- What's my ROI?

**Confidence Booster: Momentum (30% weight)**
- Is the price trending up? (safer buy)
- Are sales accelerating? (will sell faster)
- Is supply decreasing? (less competition)

---

## API Endpoints

### `GET /api/opportunities`

Find all arbitrage opportunities with momentum validation.

**Query Parameters:**
- `min_budget` - Minimum card price (e.g., 50 for $50+)
- `max_budget` - Maximum card price (e.g., 200 for under $200)
- `min_profit` - Minimum net profit after fees (e.g., 10 for $10+)
- `min_roi` - Minimum ROI percentage (e.g., 20 for 20%+)
- `momentum` - Filter by momentum: `rising`, `stable`, `all`
- `limit` - Max results (default 20, max 100)

**Example:**
```bash
# Find opportunities under $100 with 25%+ ROI
curl "http://localhost:8000/api/opportunities?max_budget=100&min_roi=25"
```

**Response:**
```json
{
  "count": 5,
  "opportunities": [
    {
      "card_id": 42,
      "player_name": "Victor Wembanyama",
      "card_year": 2023,
      "card_set": "Prizm Silver",
      "is_rookie": true,
      "sport": "Basketball",
      "market_data": {
        "avg_price": 460.0,
        "min_price": 440.0,
        "max_price": 480.0,
        "price_range": 40.0,
        "is_consistent": true,
        "sales_count": 7,
        "avg_days_to_sell": 12.0
      },
      "arbitrage": {
        "is_profitable": true,
        "buy_price": 420.0,
        "sell_price": 460.0,
        "gross_profit": 40.0,
        "fees": 59.8,
        "net_profit": -19.8,
        "roi": -4.7,
        "profit_score": 0.0,
        "available_listings": 4
      },
      "momentum": {
        "price_change_14d": 15.0,
        "price_trend": "↑",
        "sales_per_week": 3.5,
        "str_rate": 175.0,
        "active_listings": 4,
        "momentum_score": 87.5
      },
      "opportunity_score": 26.3,
      "confidence": "VERY HIGH 🔥"
    }
  ]
}
```

### `GET /api/opportunities/{card_id}`

Get detailed opportunity analysis for a specific card.

**Example:**
```bash
curl "http://localhost:8000/api/opportunities/42"
```

### `GET /api/opportunities/stats`

Get overall market statistics.

**Response:**
```json
{
  "total_opportunities": 15,
  "avg_roi": 18.5,
  "avg_profit": 25.30,
  "high_confidence_count": 8,
  "best_opportunity": { ... }
}
```

---

## How It Works

### 1. Data Requirements

**Minimum criteria to show a card:**
- ✅ At least 3 sales in last 30 days (proven demand)
- ✅ Price consistency within 20% (predictable market)
- ✅ Active listings available (can actually buy it)
- ✅ Positive profit after fees (worth your time)

### 2. Market Data Calculation

For each card with enough sales:
- **Market Rate**: SportsCardsPro ungraded/grade 9/PSA 10 price (REQUIRED - no SCP = no opportunity)
- **Graduated SCP Search**: Tries 3 query formats, validates set on every result, rejects wrong-product matches
- **SCP Sanity Check**: If SCP rate is 3x+ off from both avg AND median sales, reject it (bad match)
- **Price Range**: Min to max (consistency check)
- **Days to Sell**: Estimated from sales count over 30-day window

### 3. Arbitrage Analysis

- **Buy Price**: Cheapest current BIN listing or current auction bid
- **Sell Price**: SCP market rate (must pass set validation + sanity check + card number verification in SCP URL)
- **Fees**: 13% (eBay 12.9% + PayPal ~0.1%)
- **Net Profit**: Sell price - fees - buy price (minimum $5 BIN, $10 auction)
- **ROI**: (Net profit / Buy price) x 100
- **Buy Listings**: Direct eBay links to each profitable BIN listing with price and net profit
- **Auction Listings**: Shown separately with current bid, shipping, bid count, end time, and potential profit
- **QA Validation**: Post-pipeline rules flag extreme_roi, card_number_mismatch, etc. (does not block pipeline)

### 4. Momentum Signals

**Price Trend:**
- Compare last 14 days vs previous 14 days
- ↑ = Rising (5%+ increase)
- → = Stable (-5% to +5%)
- ↓ = Falling (5%+ decrease)

**Sales Velocity:**
- Sales per week in last 30 days
- Higher = faster turnover

**Sell-Through Rate (STR):**
- (Sales / Active listings) × 100
- 100%+ = Hot market (more sales than supply)
- 50-99% = Moderate market
- <50% = Slow market

**Momentum Score (0-100):**
- Price trend: +20% = 50 points, 0% = 25 points
- STR: 100% = 50 points, 50% = 25 points

### 5. Opportunity Score

**Final Score = (Profit Score × 0.7) + (Momentum Score × 0.3)**

- 80-100: ⭐⭐⭐⭐⭐ Excellent opportunity
- 60-79: ⭐⭐⭐⭐ Good opportunity
- 40-59: ⭐⭐⭐ Decent opportunity
- 20-39: ⭐⭐ Marginal opportunity
- 0-19: ⭐ Poor opportunity

### 6. Confidence Level

Based on momentum score:
- 70-100: VERY HIGH 🔥 (strong momentum)
- 50-69: HIGH ✅ (good momentum)
- 30-49: MEDIUM ⚠️ (moderate momentum)
- 0-29: LOW 🥶 (weak momentum)

---

## Usage Examples

### Scenario 1: Quick Flips ($100 budget)

**Goal**: Buy 5-10 cards at $10-20 each, flip fast for 2x return

```bash
curl "http://localhost:8000/api/opportunities?min_budget=10&max_budget=20&min_roi=100&momentum=rising"
```

Shows cards:
- Priced $10-20 (within budget)
- 100%+ ROI (2x return)
- Rising prices (momentum confidence)

### Scenario 2: High Value Flips ($500 budget)

**Goal**: Buy 1-2 cards at $200-400, willing to wait for 50%+ return

```bash
curl "http://localhost:8000/api/opportunities?min_budget=200&max_budget=400&min_roi=50"
```

Shows cards:
- Priced $200-400 (higher value)
- 50%+ ROI (significant profit)
- Any momentum (willing to wait)

### Scenario 3: Safe Bets Only

**Goal**: Only show cards with high confidence (strong momentum)

```bash
curl "http://localhost:8000/api/opportunities?momentum=rising&min_roi=20"
```

Shows cards:
- Rising prices only
- 20%+ ROI minimum
- Sorted by opportunity score

---

## Testing

### 1. Start API Server
```bash
/usr/bin/python3 -m backend.api.run
```

### 2. Run Test Script
```bash
/usr/bin/python3 -m backend.test_opportunities
```

### 3. View in Browser
```
http://localhost:8000/docs
```

Navigate to "Opportunities" section and try the endpoints.

---

## Next Steps

1. **Grade matching** - Compare ungraded-to-ungraded, graded-to-graded
2. **Variant precision** - "Magenta Speckle" != "Magenta"
3. **Volume threshold** - Reject "3 sales per year" and below
4. **Sold price validation** - Cross-check SCP with eBay sold comps for high-value opportunities

---

## Key Differences from "Trending"

| Old (Trending) | New (Opportunities) |
|----------------|---------------------|
| "Hotness score" | Arbitrage profit + ROI |
| Predicts future trends | Shows current opportunities |
| No buy/sell prices | Exact buy/sell/profit |
| No fee calculation | Includes 13% fees |
| Vague "momentum" | Specific price trend, STR, velocity |
| Shows all cards | Only profitable opportunities (SCP-verified) |
| Academic metrics | Actionable decisions |
| Single search query | Graduated SCP search (3 formats + set validation) |
| Trusted SCP blindly | Validates set + 3x sanity check |

---

**This is a dealer's tool, not a speculator's tool.**
