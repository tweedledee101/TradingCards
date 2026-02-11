# 🚀 Quick Start Guide - Data Pipeline

## What Just Got Built

✅ **Complete end-to-end data pipeline**
- eBay scraper → Database → Trend calculations → Results
- SQLAlchemy ORM models for all tables
- CLI tool to run everything
- Test script with mock data

## How to Test It Right Now

### Option 1: Test with Mock Data (No API Keys Needed)
```bash
cd /home/tweedledee101/TradingCards
python backend/test_pipeline.py
```

This will:
- Create a test card (Wembanyama)
- Add 5 sample sales
- Add 2 sample listings
- Calculate trends
- Show hotness score

### Option 2: Test with Real eBay Data (Requires API Keys)

1. **Get eBay API Credentials**
   - Go to https://developer.ebay.com/
   - Create an app
   - Get: App ID, Cert ID, Dev ID, Token

2. **Update .env file**
   ```bash
   nano backend/.env
   # Add your eBay credentials
   ```

3. **Setup Database**
   ```bash
   # Create database
   sudo -u postgres psql -c "CREATE DATABASE trading_cards;"
   
   # Run schema
   psql -U postgres -d trading_cards -f backend/models/schema.sql
   ```

4. **Run Pipeline**
   ```bash
   # Import Wembanyama rookie cards from last 7 days
   python -m backend.run_pipeline --query "Wembanyama 2023 rookie PSA 10" --days 7
   
   # Import more players
   python -m backend.run_pipeline --query "Scoot Henderson 2023 rookie" --days 7
   python -m backend.run_pipeline --query "Chet Holmgren 2022 rookie" --days 7
   ```

## What You'll See

```
🔍 Searching eBay for: Wembanyama 2023 rookie PSA 10
📅 Looking back: 7 days

📥 Importing sold listings...
✅ Imported 15 sales

📥 Importing active listings...
✅ Imported 8 listings

📊 Calculating trends...
✅ Calculated trends for 1 card(s)

🔥 TOP TRENDING CARDS:
================================================================================
1. Victor Wembanyama - 2023 Prizm
   🏆 ROOKIE
   💰 Avg Price: $450.00
   📈 Sales: 15 | Velocity: 187.5
   🔥 Hotness: 85.3 - 🔥 FIRE
```

## Files Created

```
backend/
├── models/__init__.py           # ORM models
├── services/data_pipeline.py    # Pipeline orchestration
├── run_pipeline.py              # CLI runner
├── test_pipeline.py             # Test script
├── PIPELINE.md                  # Documentation
└── .env                         # Your config

docs/
└── PIPELINE-IMPLEMENTATION.md   # Implementation details
```

## Common Commands

```bash
# Test with mock data
python backend/test_pipeline.py

# Import specific player
python -m backend.run_pipeline --query "Player Name rookie" --days 7

# Import without calculating trends
python -m backend.run_pipeline --query "Player Name" --days 7 --skip-trends

# Just recalculate trends (no import)
python -m backend.run_pipeline --query "dummy" --skip-listings --days 1

# Run tests
./run_tests.sh all
```

## Use in Python Code

```python
from backend.services.data_pipeline import DataPipeline

pipeline = DataPipeline()

# Import data
pipeline.import_sales("Wembanyama rookie", days_back=7)
pipeline.import_active_listings("Wembanyama rookie")

# Calculate trends
pipeline.calculate_trends()

# Get trending cards
trending = pipeline.get_trending_cards(limit=10)

for card in trending:
    print(f"{card['player_name']}: Hotness {card['hotness_score']}")
```

## What's Next

### Phase 2: REST API (Recommended Next)
- Create FastAPI app
- Build `/api/trending` endpoint
- Build `/api/cards/{id}` endpoint
- Add Swagger docs

### Phase 3: Automation
- APScheduler for nightly imports
- Error notifications
- Logging

### Phase 4: More Data Sources
- PSA population scraper
- Twitter/Reddit scrapers
- Card Ladder integration

## Troubleshooting

**"Module not found" error:**
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**"Database connection refused":**
```bash
# Check PostgreSQL is running
sudo service postgresql status

# Check credentials in backend/.env
```

**"eBay API error":**
- Verify API credentials in .env
- Check token hasn't expired
- Ensure you have API access enabled

## Documentation

- `backend/PIPELINE.md` - Pipeline documentation
- `docs/PIPELINE-IMPLEMENTATION.md` - Implementation details
- `docs/PROJECT-STATUS.md` - Project status
- `docs/TESTING.md` - Testing guide

---

**Status:** ✅ Ready to test!  
**Next:** Get eBay API keys and run with real data, or build REST API
