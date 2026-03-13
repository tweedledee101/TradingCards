# System Redesign: From "Trending" to "Opportunities"

**Date**: 2025-02-15  
**Status**: ✅ Complete - Ready for Testing

---

## What Changed

### Old System: "Trending Cards"
- Focused on "hotness scores" and momentum
- Academic metrics (velocity, momentum, social signals)
- No clear buy/sell guidance
- Showed all cards with recent sales
- No profit calculations

### New System: "Opportunities"
- Focused on **arbitrage profit** with momentum validation
- Dealer-focused metrics (buy price, sell price, ROI, fees)
- Clear buy/sell/profit for each card
- Only shows **profitable** opportunities
- Includes eBay/PayPal fees (13%)

---

## New Files Created

1. **`backend/services/opportunity_analyzer.py`**
   - Core logic for finding arbitrage opportunities
   - Calculates market rate, profit, ROI, momentum
   - Filters by budget, profit, ROI, momentum

2. **`backend/api/routes/opportunities.py`**
   - New API endpoints: `/opportunities`, `/opportunities/{id}`, `/opportunities/stats`
   - Replaces `/trending` as primary endpoint

3. **`backend/test_opportunities.py`**
   - Test script to verify the new system works
   - Shows example queries and responses

4. **`docs/OPPORTUNITY-FINDER.md`**
   - Complete documentation of new system
   - Usage examples, API reference, decision framework

---

## Files Modified

1. **`backend/api/main.py`**
   - Added opportunities router
   - Old trending endpoint still available (for now)

---

## How to Test

### 1. Restart API Server
```bash
# Stop current server (Ctrl+C)
/usr/bin/python3 -m backend.api.run
```

### 2. Run Test Script
```bash
/usr/bin/python3 -m backend.test_opportunities
```

**Expected Output:**
```
🎯 TESTING OPPORTUNITIES API
================================================================================

1️⃣  GET ALL OPPORTUNITIES
--------------------------------------------------------------------------------
✅ Found X opportunities

1. Victor Wembanyama 2023 Prizm Silver
   💰 ARBITRAGE:
      Buy: $420 | Sell: $460
      Profit: $20 (5% ROI)
   📈 MOMENTUM:
      Price Trend: ↑ +15.0% (14d)
      Sales: 3.5/week | STR: 175%
      Listings: 4
   ⭐ SCORE: 85/100 | Confidence: VERY HIGH 🔥
```

### 3. Test in Browser
```
http://localhost:8000/docs
```

Navigate to **"Opportunities"** section and try:
- `GET /api/opportunities` - See all opportunities
- `GET /api/opportunities?max_budget=100` - Filter by budget
- `GET /api/opportunities?min_roi=25` - Filter by ROI
- `GET /api/opportunities/stats` - Market overview

---

## Key Metrics Explained

### Arbitrage Metrics (70% of score)

| Metric | Description | Example |
|--------|-------------|---------|
| **Buy Price** | Cheapest current listing | $420 |
| **Sell Price** | Market rate (recent avg) | $460 |
| **Gross Profit** | Sell - Buy | $40 |
| **Fees** | 13% of sell price | $59.80 |
| **Net Profit** | Gross - Fees | -$19.80 ❌ |
| **ROI** | (Net / Buy) × 100 | -4.7% |
| **Profit Score** | ROI × 2 (max 100) | 0 |

### Momentum Metrics (30% of score)

| Metric | Description | Example |
|--------|-------------|---------|
| **Price Change** | % change last 14d | +15% ↑ |
| **Sales/Week** | Recent sales velocity | 3.5/week |
| **STR** | (Sales / Listings) × 100 | 175% 🔥 |
| **Active Listings** | Current supply | 4 |
| **Momentum Score** | Price + STR (0-100) | 87.5 |

### Combined Score

**Opportunity Score = (Profit Score × 0.7) + (Momentum Score × 0.3)**

Example:
- Profit Score: 0 (not profitable)
- Momentum Score: 87.5 (very strong)
- **Opportunity Score: 26.3** (poor - not profitable despite momentum)

---

## Decision Matrix

| Profit | Momentum | Action | Example |
|--------|----------|--------|---------|
| ✅ High | ✅ Rising | **BUY NOW** 🔥 | Buy $380, sell $460, +15% trend |
| ✅ High | → Stable | **BUY** ✓ | Buy $50, sell $75, stable market |
| ✅ High | ❌ Falling | **RISKY** ⚠️ | Profit looks good but market declining |
| ❌ Low | ✅ Rising | **WAIT** ⏳ | Good momentum, wait for better price |
| ❌ Low | → Stable | **SKIP** | No opportunity |
| ❌ Low | ❌ Falling | **AVOID** 🚫 | Dead market |

---

## Usage Scenarios

### Scenario 1: Quick Flips ($100 budget)
```bash
curl "http://localhost:8000/api/opportunities?max_budget=100&min_roi=50&momentum=rising"
```
**Shows**: Cards under $100 with 50%+ ROI and rising prices

### Scenario 2: High Value ($500 budget)
```bash
curl "http://localhost:8000/api/opportunities?min_budget=200&max_budget=500&min_profit=50"
```
**Shows**: Cards $200-500 with $50+ profit

### Scenario 3: Safe Bets Only
```bash
curl "http://localhost:8000/api/opportunities?momentum=rising&min_roi=20"
```
**Shows**: Only rising markets with 20%+ ROI

---

## What's Next

### Immediate (Testing Phase)
1. ✅ Test with current database
2. ⏳ Verify calculations are correct
3. ⏳ Adjust filters based on real data
4. ⏳ Identify any bugs or edge cases

### Short Term (Frontend)
1. Build UI to display opportunities
2. Add budget/ROI/momentum filter controls
3. Show buy/sell/profit prominently
4. Color code by confidence level

### Medium Term (Enhancements)
1. Track actual listing dates (not estimated)
2. Add grading ROI calculator (raw → PSA 10)
3. Price alerts when opportunities appear
4. Historical opportunity tracking

### Long Term (Intelligence)
1. Machine learning for price predictions
2. Optimal buy zone recommendations
3. Seasonal trend analysis
4. Player performance correlation

---

## Migration Path

**Old `/trending` endpoint still works** - no breaking changes.

**Recommended transition:**
1. Test `/opportunities` endpoint thoroughly
2. Update frontend to use `/opportunities`
3. Deprecate `/trending` after 30 days
4. Remove `/trending` in next major version

---

## Questions to Answer During Testing

1. **Are profit calculations accurate?**
   - Verify fees (13%) are correct
   - Check ROI math

2. **Are momentum signals useful?**
   - Does price trend match reality?
   - Is STR a good confidence indicator?

3. **Are filters appropriate?**
   - Do budget ranges make sense?
   - Is min_roi threshold useful?

4. **Are there enough opportunities?**
   - If too few: Lower profit threshold
   - If too many: Raise quality bar

5. **Is the scoring fair?**
   - 70/30 split (arbitrage/momentum) feel right?
   - Should we weight differently?

---

## Success Criteria

✅ **System is successful if:**
1. Shows only cards you can actually profit from
2. Provides clear buy/sell/profit numbers
3. Momentum signals increase confidence
4. Filters let you find opportunities for YOUR budget
5. You can make buying decisions without additional research

❌ **System needs work if:**
1. Shows unprofitable cards
2. Profit calculations are wrong
3. Momentum signals are misleading
4. Too many/too few results
5. Still confused about what to buy

---

**Ready to test! Start the API and run the test script.**
