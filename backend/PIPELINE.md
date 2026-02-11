# Data Pipeline

End-to-end data flow from eBay scraper to database to trend calculations.

## Components

### 1. ORM Models (`backend/models/__init__.py`)
SQLAlchemy models for all database tables:
- `Card` - Master card catalog
- `Sale` - Historical sales data
- `ActiveListing` - Current market supply
- `PriceTrend` - Computed daily metrics
- `PSAPopulation` - Grading data
- `SocialSignal` - Social media mentions

### 2. Data Pipeline (`backend/services/data_pipeline.py`)
Orchestrates data flow:
- `import_sales()` - Fetch and store eBay sold listings
- `import_active_listings()` - Fetch and store active listings
- `calculate_trends()` - Compute velocity, momentum, hotness scores
- `get_trending_cards()` - Query top trending cards

### 3. Pipeline Runner (`backend/run_pipeline.py`)
CLI tool to run the pipeline:
```bash
python -m backend.run_pipeline --query "Wembanyama rookie" --days 7
```

## Quick Start

### 1. Setup Database
```bash
# Create database
sudo -u postgres psql -c "CREATE DATABASE trading_cards;"
sudo -u postgres psql -c "CREATE USER carduser WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE trading_cards TO carduser;"

# Run schema
psql -U carduser -d trading_cards -f backend/models/schema.sql
```

### 2. Configure Environment
```bash
cp backend/.env.example backend/.env
# Edit .env with your database credentials and eBay API keys
```

### 3. Test Pipeline (Mock Data)
```bash
python backend/test_pipeline.py
```

### 4. Run Real Pipeline
```bash
# Import Wembanyama rookie cards from last 7 days
python -m backend.run_pipeline --query "Wembanyama rookie PSA 10" --days 7

# Import without calculating trends
python -m backend.run_pipeline --query "Henderson rookie" --days 7 --skip-trends

# Just calculate trends (no import)
python -m backend.run_pipeline --query "dummy" --skip-listings --days 1
```

## Data Flow

```
eBay API
   ↓
EbayScraper.search_sold_listings()
   ↓
DataPipeline.import_sales()
   ↓
Card + Sale records in database
   ↓
DataPipeline.calculate_trends()
   ↓
TrendCalculator (velocity, momentum, hotness)
   ↓
PriceTrend records in database
   ↓
DataPipeline.get_trending_cards()
   ↓
Top trending cards by hotness score
```

## Usage Examples

### Import Multiple Players
```python
from backend.services.data_pipeline import DataPipeline

pipeline = DataPipeline()

players = ["Wembanyama", "Henderson", "Holmgren"]
for player in players:
    pipeline.import_sales(f"{player} 2023 rookie", days_back=7)

pipeline.calculate_trends()
trending = pipeline.get_trending_cards(limit=10)
```

### Get Trending Cards
```python
from backend.services.data_pipeline import DataPipeline

pipeline = DataPipeline()
trending = pipeline.get_trending_cards(limit=10)

for card in trending:
    print(f"{card['player_name']} - Hotness: {card['hotness_score']}")
```

## Next Steps

- [ ] Add scheduler for nightly imports
- [ ] Add error handling and retry logic
- [ ] Add logging
- [ ] Add player name extraction from titles
- [ ] Add duplicate detection improvements
- [ ] Add data validation
