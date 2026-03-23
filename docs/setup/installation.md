# Installation & Setup Guide

Complete guide to set up the Ragnarok Gaming Trading Card Platform development environment.

## Prerequisites

- Python 3.9+
- PostgreSQL 13+
- Node.js 16+
- Firefox + geckodriver (for SCP Selenium scraper)
- Git
- eBay Developer Account (for API access)

## Step 1: Clone Repository

```bash
git clone https://github.com/tweedledee101/TradingCards.git
cd TradingCards
```

## Step 2: Install PostgreSQL

### Ubuntu/WSL
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo service postgresql start
```

## Step 3: Create Database

```bash
sudo -u postgres psql

CREATE DATABASE trading_cards;
\q
```

## Step 4: Apply Schema and Migrations

```bash
# Base schema
sudo -u postgres psql -d trading_cards -f backend/models/schema.sql

# Apply all migrations (001-012)
for f in backend/models/migration_*.sql; do
  sudo -u postgres psql -d trading_cards -f "$f"
done
```

Verify tables:
```bash
sudo -u postgres psql -d trading_cards -c "\dt"
```

Core tables: cards, sales, active_listings, price_trends, market_rates, opportunities, inventory, watchlist, job_runs, error_log

## Step 5: Install Firefox + geckodriver

SCP scraper requires Firefox (not Chrome).

```bash
# Firefox
sudo apt install firefox

# geckodriver
wget https://github.com/mozilla/geckodriver/releases/download/v0.36.0/geckodriver-v0.36.0-linux64.tar.gz
tar xzf geckodriver-v0.36.0-linux64.tar.gz
sudo mv geckodriver /usr/local/bin/
```

## Step 6: Python Environment

```bash
cd backend
pip install -r requirements.txt
```

## Step 7: Configure Environment Variables

```bash
cp .env.example .env
nano .env
```

Required:
```env
DATABASE_URL=postgresql://postgres:@localhost:5432/trading_cards
EBAY_APP_ID=<your_app_id>
EBAY_CERT_ID=<your_cert_id>
```

## Step 8: Frontend Setup

```bash
cd frontend
npm install
```

## Step 9: Start Services

```bash
sudo service postgresql start

# API (port 8000)
cd /home/tweedledee101/TradingCards
nohup /usr/bin/python3 -m backend.api.run > /tmp/api.log 2>&1 &

# Frontend (port 3000)
cd frontend
nohup npm run dev > /tmp/frontend.log 2>&1 &
```

## Step 10: Run Pipeline

```bash
# Full BIN + Auction pipeline
python3 find_opportunities.py --max-budget 200 --min-profit 5 --min-roi 20 --top-players 40
```

See [PIPELINE-OPS.md](../../PIPELINE-OPS.md) for all options.

## Common Issues

### PostgreSQL connection refused
```bash
sudo service postgresql start
```

### eBay API 401 Unauthorized
- Token auto-refreshes every 2 hours
- Check backend/.env credentials

### SCP scraper fails
- Firefox must run as your user (not root)
- geckodriver at `/usr/local/bin/geckodriver`
- Page load timeout (30s) is expected -- data still loads

### Import errors
```bash
pip install -r backend/requirements.txt
```

## Useful Commands

```bash
# Database
sudo -u postgres psql -d trading_cards -c "SELECT COUNT(*) FROM cards;"

# API docs
open http://localhost:8000/docs

# Run tests
pytest tests/qa/ -v

# Check job status
curl http://localhost:8000/api/status
```

---

**Last Updated:** 2026-03-22
