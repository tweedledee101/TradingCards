# 🚀 Quick Start Guide

## What's Built

✅ **Complete Trading Card Platform**
- eBay scraper → Database → Trend calculations
- REST API with 18 endpoints
- React frontend with 4 pages
- Inventory tracking & portfolio analytics
- Watchlist with price alerts
- Automated daily collection

## Quick Setup (5 Steps)

### 1. Setup Database
```bash
# Create database
sudo -u postgres psql -c "CREATE DATABASE trading_cards;"

# Apply schema
psql -U postgres -d trading_cards -f backend/models/schema.sql

# Apply migration
psql -U postgres -d trading_cards -f backend/models/migration_001.sql
```

### 2. Configure Environment
```bash
cp backend/.env.example backend/.env
nano backend/.env  # Add your eBay API credentials
```

### 3. Install Dependencies
```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend (optional, requires Node.js 16+)
cd ../frontend
npm install
```

### 4. Start API Server
```bash
cd backend
python3 -m api.run
```

Visit: http://localhost:8000/docs

### 5. Start Frontend (Optional)
```bash
cd frontend
npm run dev
```

Visit: http://localhost:3000

## Test Without eBay API

```bash
# Test with mock data
python backend/test_pipeline.py
```

## Test With Real Data

```bash
# Import cards
python -m backend.run_pipeline --query "Wembanyama rookie" --days 7

# Start automated collection
python -m backend.run_scheduler --now
```

## API Endpoints (18 Total)

### Trending & Stats
```bash
# Get trending cards
curl http://localhost:8000/api/trending

# Filter by price and hotness
curl "http://localhost:8000/api/trending?max_price=100&min_hotness=50"

# Market statistics
curl http://localhost:8000/api/stats
```

### Cards
```bash
# Get card details
curl http://localhost:8000/api/cards/1

# Search cards
curl "http://localhost:8000/api/cards?player=Wembanyama"
```

### Inventory
```bash
# Add to inventory
curl -X POST http://localhost:8000/api/inventory \
  -H "Content-Type: application/json" \
  -d '{"card_id": 1, "purchase_date": "2024-01-15", "purchase_price": 45.00}'

# Get portfolio stats
curl http://localhost:8000/api/inventory/stats

# Record sale
curl -X POST http://localhost:8000/api/inventory/sales \
  -H "Content-Type: application/json" \
  -d '{"inventory_id": 1, "sale_date": "2024-02-01", "sale_price": 65.00, "fees": 8.45}'
```

### Watchlist
```bash
# Add to watchlist
curl -X POST http://localhost:8000/api/watchlist \
  -H "Content-Type: application/json" \
  -d '{"card_id": 5, "target_price": 50.00}'

# Get alerts
curl http://localhost:8000/api/watchlist/alerts
```

## Frontend Pages

1. **Trending** (`/`) - Browse trending cards with filtering
2. **Card Detail** (`/card/:id`) - Price charts, profit calculator
3. **Inventory** (`/inventory`) - Portfolio dashboard with P&L
4. **Watchlist** (`/watchlist`) - Price monitoring with alerts

## Common Commands

```bash
# Test pipeline
python backend/test_pipeline.py

# Import specific player
python -m backend.run_pipeline --query "Player Name rookie" --days 7

# Run automated collection now
python -m backend.run_scheduler --now

# Start daily scheduler (2 AM)
python -m backend.run_scheduler

# Run tests
./run_tests.sh all

# Apply migration
./migrate.sh  # or migrate.bat on Windows
```

## Use in Python

```python
from backend.services.data_pipeline import DataPipeline

pipeline = DataPipeline()

# Import data
pipeline.import_sales("Wembanyama rookie", days_back=7)
pipeline.calculate_trends()

# Get trending
trending = pipeline.get_trending_cards(limit=10)
```

## What's Next

### Immediate
1. Get eBay API credentials
2. Test with real data
3. Update Node.js to 16+ for frontend

### Short Term
4. Add PSA population scraper
5. Enhanced profit calculator
6. More visualizations

### Medium Term
7. Deploy to production
8. Add user authentication
9. Mobile app

## Troubleshooting

**Database connection refused:**
```bash
sudo service postgresql status
sudo service postgresql start
```

**eBay API error:**
- Verify credentials in backend/.env
- Check token hasn't expired

**Frontend won't start:**
```bash
# Update Node.js to 16+
node --version  # Check version
```

**Module not found:**
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

## Documentation

- [API Documentation](./docs/API-ENHANCEMENTS.md)
- [New Features Guide](./docs/QUICKSTART-NEW-FEATURES.md)
- [Installation Guide](./docs/setup/installation.md)
- [Project Status](./docs/PROJECT-STATUS.md)
- [Testing Guide](./docs/TESTING.md)

## Features

### 🔥 Trend Detection
- Hotness score algorithm
- Price velocity tracking
- Advanced filtering & sorting

### 💼 Portfolio Management
- Inventory tracking
- Profit/loss calculations
- ROI analytics
- Sales recording

### 👀 Watchlist
- Price monitoring
- Target price alerts
- Trend tracking

### 📊 Analytics
- Market statistics
- Price history charts
- Volume analysis
- Portfolio stats

### 🤖 Automation
- Daily collection at 2 AM
- Target list configuration
- Daily reports (CSV + text)

---

**Status:** ✅ Ready to use!  
**API:** http://localhost:8000/docs  
**Frontend:** http://localhost:3000  
**Version:** 2.0.0
