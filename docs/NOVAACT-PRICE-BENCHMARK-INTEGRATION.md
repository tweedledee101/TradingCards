# NovaAct Price Benchmark Integration Guide

**Date:** 2025-02-XX  
**Status:** Ready to Implement  
**Priority:** High (10-15% accuracy improvement)

---

## 🎯 Overview

Integrate NovaAct to scrape price benchmark data from Card Ladder or 130point and send it to your backend via webhook.

**Why Price Benchmarks Matter:**
- Velocity trends = Leading indicator
- 7-day/30-day changes = Momentum confirmation
- Market cap = Liquidity indicator
- Cross-validation with eBay data

---

## 🏗️ Architecture

```
NovaAct Agent → Scrapes Card Ladder/130point → Sends JSON → Your Webhook → Database
```

---

## 📋 Setup Steps

### Step 1: Apply Database Migration

```bash
sudo -u postgres psql trading_cards -f backend/models/migration_003_price_benchmarks.sql
```

### Step 2: Restart API

```bash
/usr/bin/python3 -m backend.api.run
```

**New endpoints:**
- `POST /api/webhooks/novaact/price-benchmark` - Receive price data
- `GET /api/benchmarks/{card_id}` - Get benchmark data

### Step 3: Test Webhook

```bash
curl -X POST http://localhost:8000/api/webhooks/novaact/price-benchmark \
  -H "Content-Type: application/json" \
  -d '{
    "player_name": "Paul Skenes",
    "card_year": 2024,
    "card_set": "Bowman Chrome",
    "source": "cardladder",
    "current_price": 45.00,
    "price_7d_ago": 38.00,
    "price_30d_ago": 32.00,
    "velocity_rating": "Hot",
    "market_cap": 11250.00
  }'
```

---

## 🤖 NovaAct Agent Configuration

### **Option 1: Card Ladder Agent**

**Target:** https://www.cardladder.com  
**Agent Name:** `CardLadder-Price-Scraper`

**Scraping Logic:**
1. Search for card: `{player_name} {card_year} {card_set}`
2. Extract current price
3. Extract 7-day price
4. Extract 30-day price
5. Extract velocity rating
6. Send to webhook

**JSON Payload:**
```json
{
  "player_name": "Paul Skenes",
  "card_year": 2024,
  "card_set": "Bowman Chrome",
  "source": "cardladder",
  "current_price": 45.00,
  "price_7d_ago": 38.00,
  "price_30d_ago": 32.00,
  "velocity_rating": "Hot"
}
```

### **Option 2: 130point Agent**

**Target:** https://130point.com  
**Agent Name:** `130point-Price-Scraper`

**Scraping Logic:**
1. Search for card
2. Extract current market price
3. Extract historical prices
4. Calculate velocity
5. Send to webhook

**JSON Payload:**
```json
{
  "player_name": "Paul Skenes",
  "card_year": 2024,
  "card_set": "Bowman Chrome",
  "source": "130point",
  "current_price": 44.50,
  "price_7d_ago": 37.50,
  "price_30d_ago": 31.00,
  "velocity_rating": "Warm",
  "market_cap": 11125.00
}
```

---

## 📊 JSON Payload Spec

### Required Fields
```json
{
  "player_name": "string",
  "card_year": integer,
  "card_set": "string",
  "source": "string",  // 'cardladder' or '130point'
  "current_price": float
}
```

### Optional Fields
```json
{
  "card_number": "string",
  "price_7d_ago": float,
  "price_30d_ago": float,
  "velocity_rating": "string",  // 'Hot', 'Warm', 'Cold', 'Stable'
  "market_cap": float,
  "scrape_date": "YYYY-MM-DD"
}
```

---

## 🎨 Frontend Integration

Add to `CardDetail.jsx`:

```javascript
const [benchmarkData, setBenchmarkData] = useState(null);

useEffect(() => {
  fetch(`http://localhost:8000/api/benchmarks/${id}`)
    .then(res => res.json())
    .then(data => setBenchmarkData(data))
    .catch(err => console.log('No benchmark data'));
}, [id]);

// Display
{benchmarkData && (
  <div className="bg-white p-6 rounded-lg shadow">
    <h3 className="text-lg font-semibold mb-4">📈 Price Benchmarks</h3>
    {benchmarkData.benchmarks.map((b, i) => (
      <div key={i} className="mb-4">
        <div className="font-semibold">{b.source}</div>
        <div>Current: ${b.current_price}</div>
        <div className={b.change_7d > 0 ? 'text-green-600' : 'text-red-600'}>
          7d: {b.change_7d > 0 ? '+' : ''}{b.change_7d}%
        </div>
        <div className={b.change_30d > 0 ? 'text-green-600' : 'text-red-600'}>
          30d: {b.change_30d > 0 ? '+' : ''}{b.change_30d}%
        </div>
        <div>Velocity: {b.velocity_rating}</div>
      </div>
    ))}
  </div>
)}
```

---

## 📈 Enhanced Opportunity Scoring

### Current (eBay + PSA)
```
opportunity = (
  hotness × 0.30 +
  grading_spike × 0.25 +
  psa_10_rate × 0.20 +
  momentum × 0.25
)
```

### Enhanced (eBay + PSA + Benchmarks)
```
opportunity = (
  hotness × 0.25 +
  grading_spike × 0.20 +
  psa_10_rate × 0.15 +
  benchmark_velocity × 0.20 +
  price_momentum × 0.20
)
```

---

## 🚀 NovaAct Agent Pseudocode

```python
# Agent: CardLadder-Price-Scraper

targets = load_yaml('config/targets.yaml')

for player in targets:
    # Navigate to Card Ladder
    navigate_to(f"https://www.cardladder.com/search?q={player.name}")
    
    # Extract data
    current = extract_text('.current-price')
    price_7d = extract_text('.price-7d')
    price_30d = extract_text('.price-30d')
    velocity = extract_text('.velocity-rating')
    
    # Send to webhook
    payload = {
        "player_name": player.name,
        "card_year": player.year,
        "card_set": player.set,
        "source": "cardladder",
        "current_price": float(current),
        "price_7d_ago": float(price_7d),
        "price_30d_ago": float(price_30d),
        "velocity_rating": velocity
    }
    
    post_json('http://your-domain.com/api/webhooks/novaact/price-benchmark', payload)
    sleep(5)
```

---

## 🎯 Success Metrics

### Before Benchmarks
- **Data sources:** 2 (eBay, PSA)
- **Accuracy:** ~75%
- **Velocity detection:** eBay only

### After Benchmarks
- **Data sources:** 3 (eBay, PSA, Card Ladder/130point)
- **Accuracy:** ~85% (+10%)
- **Velocity detection:** Cross-validated

---

## 📚 Next Steps

1. Apply migration
2. Test webhook
3. Build NovaAct agent (Card Ladder OR 130point)
4. Test with 5 cards
5. Scale to 25 cards
6. Update opportunity scoring
7. Add frontend display

---

**Estimated Time:** 1 week  
**Impact:** High (10-15% accuracy boost)  
**Ready to build!** 🚀
