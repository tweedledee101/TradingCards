# Installation & Setup Guide

Complete guide to set up the Trading Card Platform development environment.

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
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

### macOS
```bash
brew install postgresql@14
brew services start postgresql@14
```

### Windows
Download from [postgresql.org](https://www.postgresql.org/download/windows/)

## Step 3: Create Database

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE trading_cards;
CREATE USER carduser WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE trading_cards TO carduser;
\q
```

## Step 4: Run Database Schema

```bash
# Apply base schema
psql -U carduser -d trading_cards -f backend/models/schema.sql

# Apply inventory migration
psql -U carduser -d trading_cards -f backend/models/migration_001.sql
```

Verify tables were created:
```bash
psql -U carduser -d trading_cards -c "\dt"
```

You should see 9 tables:
- cards
- sales
- active_listings
- price_trends
- inventory
- inventory_sales
- watchlist
- psa_population
- social_signals

## Step 5: Python Environment

### Create Virtual Environment
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

## Step 6: Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit with your credentials
nano .env  # or use your preferred editor
```

Required variables:
```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=trading_cards
DB_USER=carduser
DB_PASSWORD=your_secure_password

# eBay API (get from developer.ebay.com)
EBAY_APP_ID=your_app_id
EBAY_CERT_ID=your_cert_id
EBAY_DEV_ID=your_dev_id
EBAY_TOKEN=your_oauth_token
```

## Step 7: Get eBay API Credentials

1. Go to [eBay Developers Program](https://developer.ebay.com/)
2. Sign up for a developer account
3. Create a new application
4. Get your credentials:
   - App ID (Client ID)
   - Cert ID (Client Secret)
   - Dev ID
5. Generate OAuth token:
   ```bash
   # Use eBay's OAuth tool or:
   curl -X POST 'https://api.ebay.com/identity/v1/oauth2/token' \
     -H 'Content-Type: application/x-www-form-urlencoded' \
     -H 'Authorization: Basic <base64(AppID:CertID)>' \
     -d 'grant_type=client_credentials&scope=https://api.ebay.com/oauth/api_scope'
   ```

## Step 8: Test Database Connection

```python
# Test script
from backend.utils.database import get_db

db = next(get_db())
result = db.execute("SELECT version();")
print(result.fetchone())
db.close()
```

## Step 9: Test eBay Scraper

```python
from backend.scrapers.ebay_scraper import EbayScraper

scraper = EbayScraper()
results = scraper.search_sold_listings("Wembanyama rookie", days_back=7)
print(f"Found {len(results)} sales")
print(results[0] if results else "No results")
```

## Step 10: Run API Server

```bash
cd backend
python3 -m api.run
# Or with uvicorn directly:
uvicorn api.main:app --reload --port 8000
```

Visit: http://localhost:8000/docs for API documentation

## Step 11: Setup Frontend (Optional)

### Prerequisites
- Node.js 16+ and npm

### Install and Run
```bash
cd frontend
npm install
npm run dev
```

Visit: http://localhost:3000

**Note:** If Node.js version is < 16, update first:
```bash
# Ubuntu/WSL
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# macOS
brew install node@18

# Verify
node --version  # Should be 16+
```

## Project Structure

```
TradingCards/
├── backend/
│   ├── api/              # FastAPI endpoints
│   ├── config/           # Configuration
│   │   └── settings.py
│   ├── models/           # Database models
│   │   └── schema.sql
│   ├── scrapers/         # Data scrapers
│   │   └── ebay_scraper.py
│   ├── utils/            # Utilities
│   │   └── database.py
│   ├── .env              # Your credentials (not in git)
│   ├── .env.example      # Template
│   └── requirements.txt
├── docs/                 # Documentation
├── tests/                # Test suite
└── README.md
```

## Common Issues

### Issue: PostgreSQL connection refused
**Solution:** Make sure PostgreSQL is running
```bash
sudo service postgresql status
sudo service postgresql start
```

### Issue: eBay API returns 401 Unauthorized
**Solution:** 
- Check your OAuth token is valid (tokens expire)
- Verify App ID and Cert ID are correct
- Regenerate token if needed

### Issue: Import errors in Python
**Solution:**
- Make sure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`
- Check Python version: `python --version` (should be 3.11+)

### Issue: Database tables not created
**Solution:**
- Check you're connected to correct database
- Run schema.sql again
- Check for SQL errors in output

## Development Workflow

### Before Starting Work
```bash
git checkout main
git pull origin main
git checkout -b feature/CARD-XXX-description
```

### During Development
```bash
# Make changes
git add .
git commit -m "feat(scope): description"
```

### Before Submitting PR
```bash
# Rebase against main
git rebase main

# Run tests (when available)
pytest

# Push to remote
git push -u origin feature/CARD-XXX-description
```

See [Git Workflow Standards](../.amazonq/rules/git-workflow-standards.md) for details.

## Testing

### Run All Tests
```bash
pytest
```

### Run Specific Test
```bash
pytest tests/test_ebay_scraper.py
```

### Run with Coverage
```bash
pytest --cov=backend tests/
```

## Useful Commands

### Database
```bash
# Connect to database
psql -U carduser -d trading_cards

# List tables
\dt

# Describe table
\d cards

# Query data
SELECT * FROM cards LIMIT 10;

# Exit
\q
```

### Python
```bash
# Activate virtual environment
source venv/bin/activate

# Deactivate
deactivate

# Install new package
pip install package_name
pip freeze > requirements.txt
```

### Git
```bash
# Check status
git status

# View branches
git branch -a

# Switch branch
git checkout branch_name

# View commit history
git log --oneline
```

## Next Steps

1. ✅ Complete this setup
2. ✅ Run API server
3. ✅ Test API endpoints
4. ✅ Setup frontend (optional)
5. ⏳ Add more scrapers (PSA, social media)
6. ⏳ Deploy to production

## Resources

- [PostgreSQL Tutorial](https://www.postgresqltutorial.com/)
- [eBay API Documentation](https://developer.ebay.com/api-docs/buy/browse/overview.html)
- [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)

## Support

- Check [docs/](../docs/) for detailed documentation
- Review [PROJECT-STATUS.md](../docs/PROJECT-STATUS.md) for current progress
- See [CHANGELOG.md](../CHANGELOG.md) for recent changes

---

**Last Updated:** 2025-02-11  
**Version:** 2.0.0
