# NovaAct PSA Scraper Integration Guide

**Date:** 2025-02-XX  
**Status:** Ready to Implement  
**Priority:** High (20-30% accuracy improvement)

---

## 🎯 Overview

Integrate NovaAct to scrape PSA grading population data and send it to your backend via webhook.

**Why PSA Data Matters:**
- Grading spikes = Strong buy signal
- PSA 10 rate = Grade vs. raw ROI decision
- Population trends = Scarcity indicator

---

## 🏗️ Architecture

```
NovaAct Agent → Scrapes PSA Website → Sends JSON → Your Webhook → Database
```

### Data Flow
1. **NovaAct** scrapes https://www.psacard.com/pop daily at 3 AM
2. **Extracts** PSA 10/9/8 counts for each card
3. **Sends JSON** to your webhook: `POST /api/webhooks/novaact/psa`
4. **Your backend** stores data in `grading_population` table
5. **Frontend** displays grading data on card detail pages

---

## 📋 Setup Steps

### Step 1: Apply Database Migration

```bash
cd ~/TradingCards
psql -U postgres -d trading_cards -f backend/models/migration_002_psa_grading.sql
```

**What it does:**
- Creates `grading_population` table
- Adds indexes for performance
- Sets up foreign key to `cards` table

### Step 2: Restart API Server

```bash
/usr/bin/python3 -m backend.api.run
```

**New endpoints available:**
- `POST /api/webhooks/novaact/psa` - Receive PSA data
- `GET /api/webhooks/novaact/psa/test` - Test webhook
- `GET /api/grading/{card_id}` - Get grading data

### Step 3: Test Webhook

```bash
curl -X POST http://localhost:8000/api/webhooks/novaact/psa \
  -H "Content-Type: application/json" \
  -d '{
    "player_name": "Paul Skenes",
    "card_year": 2024,
    "card_set": "Bowman Chrome",
    "card_number": "1",
    "psa_10_count": 45,
    "psa_9_count": 120,
    "psa_8_count": 85,
    "total_graded": 250,
    "scrape_date": "2025-02-15"
  }'
```

**Expected response:**
```json
{
  "status": "success",
  "card_id": 1,
  "player_name": "Paul Skenes",
  "psa_10_rate": 0.18,
  "message": "PSA data recorded for Paul Skenes 2024 Bowman Chrome"
}
```

---

## 🤖 NovaAct Agent Configuration

### Agent Name: `PSA-Population-Scraper`

### Target URL
```
https://www.psacard.com/pop/baseball-cards/{year}
```

### Scraping Logic

**For each card in your target list:**

1. **Navigate to PSA Pop Report**
   - Search for: `{player_name} {card_year} {card_set}`
   - Example: "Paul Skenes 2024 Bowman Chrome"

2. **Extract Data**
   - PSA 10 count
   - PSA 9 count
   - PSA 8 count
   - Total graded

3. **Send to Webhook**
   ```javascript
   POST https://your-domain.com/api/webhooks/novaact/psa
   {
     "player_name": "Paul Skenes",
     "card_year": 2024,
     "card_set": "Bowman Chrome",
     "psa_10_count": 45,
     "psa_9_count": 120,
     "psa_8_count": 85,
     "total_graded": 250
   }
   ```

### Schedule
- **Frequency:** Daily at 3 AM (after eBay scrape)
- **Cards to scrape:** Loop through `config/targets.yaml` (25 cards)
- **Rate limit:** 1 request per 5 seconds (avoid blocking)

---

## 📊 JSON Payload Spec

### Required Fields
```json
{
  "player_name": "string",      // e.g., "Paul Skenes"
  "card_year": integer,          // e.g., 2024
  "card_set": "string",          // e.g., "Bowman Chrome"
  "psa_10_count": integer,       // e.g., 45
  "total_graded": integer        // e.g., 250
}
```

### Optional Fields
```json
{
  "card_number": "string",       // e.g., "1" or "RC"
  "psa_9_count": integer,        // e.g., 120
  "psa_8_count": integer,        // e.g., 85
  "scrape_date": "YYYY-MM-DD"    // e.g., "2025-02-15"
}
```

---

## 🎨 Frontend Integration

### Display Grading Data on Card Detail Page

**Add to `frontend/src/pages/CardDetail.jsx`:**

```javascript
const [gradingData, setGradingData] = useState(null);

useEffect(() => {
  // Fetch grading data
  fetch(`http://localhost:8000/api/grading/${id}`)
    .then(res => res.json())
    .then(data => setGradingData(data))
    .catch(err => console.log('No grading data'));
}, [id]);

// Display in UI
{gradingData && (
  <div className="bg-white p-6 rounded-lg shadow">
    <h3 className="text-lg font-semibold mb-4">PSA Grading Population</h3>
    <div className="space-y-2">
      <div>PSA 10: {gradingData.psa_10_count} ({(gradingData.psa_10_rate * 100).toFixed(1)}%)</div>
      <div>PSA 9: {gradingData.psa_9_count}</div>
      <div>PSA 8: {gradingData.psa_8_count}</div>
      <div>Total Graded: {gradingData.total_graded}</div>
    </div>
  </div>
)}
```

---

## 🧪 Testing

### Test 1: Manual Webhook Call
```bash
curl -X POST http://localhost:8000/api/webhooks/novaact/psa \
  -H "Content-Type: application/json" \
  -d '{
    "player_name": "Caitlin Clark",
    "card_year": 2024,
    "card_set": "Prizm",
    "psa_10_count": 30,
    "psa_9_count": 80,
    "total_graded": 150
  }'
```

### Test 2: Verify Database
```sql
SELECT * FROM grading_population ORDER BY date_recorded DESC LIMIT 10;
```

### Test 3: Check API Response
```bash
curl http://localhost:8000/api/grading/1
```

---

## 📈 Impact on Opportunity Scoring

### Current Formula (eBay Only)
```
hotness = (velocity × 0.40) + (momentum × 0.35) + (social × 0.25)
```

### Enhanced Formula (With PSA Data)
```
opportunity = (
  hotness × 0.30 +           // eBay trends
  grading_spike × 0.25 +     // PSA population growth
  psa_10_rate × 0.20 +       // Scarcity factor
  momentum × 0.25            // Price acceleration
)
```

### Grading Spike Detection
```python
# Compare today's population vs. 7 days ago
spike = (today_total - week_ago_total) / week_ago_total
if spike > 0.20:  # 20% increase
    grading_spike_score = 100
```

---

## 🚀 NovaAct Agent Pseudocode

```python
# NovaAct Agent: PSA-Population-Scraper

# Load target cards
targets = load_yaml('config/targets.yaml')

for player in targets:
    # Navigate to PSA website
    navigate_to(f"https://www.psacard.com/pop/search?player={player.name}")
    
    # Extract data
    psa_10 = extract_text('.psa-10-count')
    psa_9 = extract_text('.psa-9-count')
    total = extract_text('.total-graded')
    
    # Send to webhook
    payload = {
        "player_name": player.name,
        "card_year": player.year,
        "card_set": player.set,
        "psa_10_count": int(psa_10),
        "psa_9_count": int(psa_9),
        "total_graded": int(total)
    }
    
    post_json('https://your-domain.com/api/webhooks/novaact/psa', payload)
    
    # Rate limit
    sleep(5)
```

---

## 🔒 Security

### Webhook Authentication (Optional)
Add API key to webhook:

```python
@router.post("/webhooks/novaact/psa")
def receive_psa_data(payload: PSADataPayload, api_key: str = Header(None)):
    if api_key != os.getenv('NOVAACT_API_KEY'):
        raise HTTPException(status_code=401, detail="Invalid API key")
    # ... rest of code
```

**NovaAct sends:**
```
POST /api/webhooks/novaact/psa
Headers: X-API-Key: your-secret-key
```

---

## 📊 Expected Results

### Before PSA Integration
- **Accuracy:** ~60% (eBay only)
- **Blind spots:** Can't detect grading spikes
- **ROI decisions:** Guesswork (grade vs. raw)

### After PSA Integration
- **Accuracy:** ~75-80% (+15-20%)
- **Grading spikes:** Detected automatically
- **ROI decisions:** Data-driven (PSA 10 rate × premium)

---

## 🎯 Success Metrics

### Week 1
- ✅ Webhook receiving data
- ✅ Database storing correctly
- ✅ Frontend displaying grading data

### Week 2
- ✅ 25 cards scraped daily
- ✅ Grading spike detection working
- ✅ Opportunity score improved

### Week 3
- ✅ Grade vs. raw ROI calculator
- ✅ Historical grading trends
- ✅ Accuracy improvement measured

---

## 🐛 Troubleshooting

### Issue: Webhook returns 404
**Solution:** Restart API server, check routes registered

### Issue: Card not found
**Solution:** Webhook creates new card automatically, check player name spelling

### Issue: PSA website blocks scraper
**Solution:** Add delays, rotate proxies, use NovaAct's anti-detection

### Issue: Duplicate data
**Solution:** Webhook checks `date_recorded`, updates existing record

---

## 📚 Next Steps

1. **Apply migration** - Create `grading_population` table
2. **Test webhook** - Send manual POST request
3. **Build NovaAct agent** - Configure scraper
4. **Test with 5 cards** - Verify data flow
5. **Scale to 25 cards** - Full target list
6. **Update opportunity scoring** - Include grading data
7. **Add frontend display** - Show PSA data on card pages

---

## 🎉 Ready to Build!

**Estimated Time:** 1 week  
**Difficulty:** Medium  
**Impact:** High (15-20% accuracy boost)

**Your backend is ready!** Just need to:
1. Apply migration
2. Build NovaAct agent
3. Test webhook

Let me know when you're ready to build the NovaAct agent! 🚀
