# API Enhancements & Inventory System

## Overview
Major platform upgrade adding advanced filtering, inventory tracking, and watchlist management.

## 🎯 What's New

### 1. Enhanced API Endpoints

#### Trending Cards - Advanced Filtering
**Endpoint:** `GET /api/trending`

**New Query Parameters:**
- `min_hotness` - Filter by minimum hotness score
- `min_price` / `max_price` - Price range filtering
- `sport` - Filter by sport (Basketball, Baseball, etc.)
- `sort_by` - Sort by: hotness, velocity, price, volume

**Example:**
```bash
# Get hot basketball cards under $100
curl "http://localhost:8000/api/trending?sport=basketball&max_price=100&min_hotness=40"

# Sort by price velocity
curl "http://localhost:8000/api/trending?sort_by=velocity&limit=50"
```

#### Market Statistics
**Endpoint:** `GET /api/stats`

Returns overall market metrics:
- Total cards tracked
- Average hotness score
- Average price
- Total sales volume
- Count of "hot" cards (hotness >= 50)

#### Card Details - Enhanced
**Endpoint:** `GET /api/cards/{id}?days=30`

Now includes:
- Price history over time (configurable days)
- Recent sales with full details
- Active listings with URLs
- Current trend metrics (velocity, momentum, hotness)

#### Card Search - Pagination
**Endpoint:** `GET /api/cards`

**New Parameters:**
- `offset` - Pagination offset
- `limit` - Results per page
- `card_set` - Filter by card set
- `sport` - Filter by sport

Returns total count for pagination.

---

### 2. Inventory Tracking System

Track cards you own, calculate profits, and manage your portfolio.

#### Add to Inventory
**Endpoint:** `POST /api/inventory`

```json
{
  "card_id": 1,
  "purchase_date": "2024-01-15",
  "purchase_price": 45.00,
  "purchase_source": "eBay",
  "quantity": 1,
  "condition": "Near Mint",
  "graded": true,
  "grade_company": "PSA",
  "grade_value": 9.0,
  "storage_location": "Box A",
  "notes": "Great centering"
}
```

#### Get Inventory
**Endpoint:** `GET /api/inventory?status=owned`

**Status Options:**
- `owned` - Cards you currently own
- `listed` - Cards listed for sale
- `sold` - Cards you've sold

**Returns:**
- Purchase details
- Current market value
- Unrealized profit/loss
- ROI percentage
- Storage location

#### Record Sale
**Endpoint:** `POST /api/inventory/sales`

```json
{
  "inventory_id": 1,
  "sale_date": "2024-02-01",
  "sale_price": 65.00,
  "sale_platform": "eBay",
  "fees": 8.45,
  "shipping_cost": 4.00,
  "notes": "Sold to collector"
}
```

**Auto-calculates:**
- Net profit (sale_price - fees - shipping - purchase_price)
- ROI percentage
- Updates inventory status to "sold"

#### Portfolio Statistics
**Endpoint:** `GET /api/inventory/stats`

**Returns:**
- Total invested
- Current portfolio value
- Total cards owned
- Realized profit (from sales)
- Unrealized profit (current holdings)
- Overall ROI percentage

---

### 3. Watchlist System

Monitor cards and get alerts when they hit target prices.

#### Add to Watchlist
**Endpoint:** `POST /api/watchlist`

```json
{
  "card_id": 5,
  "target_price": 50.00,
  "alert_threshold": 5.0,
  "notes": "Buy if under $52"
}
```

#### Get Watchlist
**Endpoint:** `GET /api/watchlist`

**Returns:**
- Target price vs current price
- Price difference and percentage
- Alert status (triggers when within threshold)
- Current trend metrics

#### Get Alerts
**Endpoint:** `GET /api/watchlist/alerts`

Returns only cards that have hit target prices.

#### Remove from Watchlist
**Endpoint:** `DELETE /api/watchlist/{id}`

---

## 📊 Database Schema Updates

### New Tables

**inventory**
- Tracks cards you own
- Purchase details, condition, grading
- Storage location
- Status (owned/listed/sold)

**inventory_sales**
- Sales from your inventory
- Fees, shipping costs
- Auto-calculated profit and ROI

**watchlist**
- Cards to monitor
- Target prices and alert thresholds

### Schema Updates

**active_listings** - Added:
- `listing_title` - Full listing title
- `listing_url` - Direct link to listing

**price_trends** - Added:
- `momentum_score` - Price momentum metric

---

## 🎨 Frontend Updates

### New Pages

#### Inventory Page (`/inventory`)
- Portfolio statistics dashboard
- Filter by status (owned/listed/sold)
- Real-time profit/loss tracking
- ROI calculations
- Quick links to card details

#### Watchlist Page (`/watchlist`)
- Monitor target cards
- Price alerts
- Current vs target price comparison
- Hotness score tracking

### Updated Components

**Navigation Bar**
- Links to Trending, Inventory, Watchlist

**API Client**
- All new endpoints integrated
- Enhanced filtering support

---

## 🚀 Setup Instructions

### 1. Run Database Migration

```bash
# Apply new schema
psql -U postgres -d trading_cards -f backend/models/migration_001.sql
```

### 2. Install Dependencies (if needed)

```bash
cd backend
pip install -r requirements.txt
```

### 3. Restart API Server

```bash
python3 -m backend.api.run
```

### 4. Update Frontend (when Node.js updated)

```bash
cd frontend
npm install
npm run dev
```

---

## 📝 Usage Examples

### Track a Card Purchase

```python
import requests

# Add to inventory
response = requests.post('http://localhost:8000/api/inventory', json={
    "card_id": 1,
    "purchase_date": "2024-01-15",
    "purchase_price": 45.00,
    "purchase_source": "eBay",
    "quantity": 1
})

print(f"Added to inventory: {response.json()}")
```

### Monitor Portfolio Performance

```python
# Get portfolio stats
stats = requests.get('http://localhost:8000/api/inventory/stats').json()

print(f"Total Invested: ${stats['total_invested']}")
print(f"Current Value: ${stats['current_value']}")
print(f"Total Profit: ${stats['total_profit']}")
print(f"ROI: {stats['roi_percentage']}%")
```

### Set Price Alerts

```python
# Add to watchlist
requests.post('http://localhost:8000/api/watchlist', json={
    "card_id": 5,
    "target_price": 50.00,
    "alert_threshold": 5.0,
    "notes": "Buy if under $52"
})

# Check alerts
alerts = requests.get('http://localhost:8000/api/watchlist/alerts').json()
for alert in alerts['alerts']:
    print(f"{alert['card']['player_name']}: ${alert['current_price']} (Target: ${alert['target_price']})")
```

---

## 🎯 Next Steps

1. ✅ Enhanced API with filtering/sorting
2. ✅ Inventory tracking system
3. ✅ Watchlist management
4. ⏳ Enhanced profit calculator (shipping, grading fees)
5. ⏳ More data visualizations
6. ⏳ Improved trend detection algorithm
7. ⏳ PSA population scraper
8. ⏳ Production deployment

---

## 🔧 API Testing

Test the new endpoints:

```bash
# Market stats
curl http://localhost:8000/api/stats

# Filtered trending
curl "http://localhost:8000/api/trending?min_hotness=40&sort_by=velocity"

# Card with history
curl "http://localhost:8000/api/cards/1?days=60"

# Inventory stats
curl http://localhost:8000/api/inventory/stats

# Watchlist
curl http://localhost:8000/api/watchlist
```

---

## 📚 Documentation

- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:3000 (after Node.js update)
- Database Schema: `backend/models/migration_001.sql`
- Models: `backend/models/__init__.py`
