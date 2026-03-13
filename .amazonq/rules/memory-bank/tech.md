# Trading Card Platform - Technology Stack

## Programming Languages

### Backend
- **Python 3.9+** - Primary backend language
- **SQL** - PostgreSQL database queries and schema

### Frontend
- **JavaScript (ES6+)** - React application code
- **JSX** - React component syntax
- **CSS** - Tailwind utility classes

### Infrastructure
- **YAML** - Configuration files (targets.yaml, CloudFormation)
- **Bash/Batch** - Setup and deployment scripts

## Core Technologies

### Backend Stack
- **FastAPI 0.104.1** - Modern async web framework for REST API
- **SQLAlchemy 2.0.23** - ORM for database interactions
- **PostgreSQL 13+** - Primary database (psycopg2-binary 2.9.9)
- **Uvicorn 0.24.0** - ASGI server for FastAPI
- **Pydantic 2.5.0** - Data validation and settings management

### Frontend Stack
- **React 18.2.0** - UI component library
- **Vite 5.0.0** - Build tool and dev server
- **React Router DOM 6.20.0** - Client-side routing
- **Axios 1.6.2** - HTTP client for API calls
- **Recharts 2.10.3** - Data visualization charts
- **Tailwind CSS 3.3.6** - Utility-first CSS framework

### Data Collection
- **Selenium 4.15.2** - Browser automation for scraping
- **BeautifulSoup4 4.12.2** - HTML parsing
- **webdriver-manager 4.0.1** - WebDriver management
- **eBay SDK 2.2.0** - eBay Browse API client
- **Requests 2.31.0** - HTTP library

### Data Processing
- **Pandas 2.0.0+** - Data manipulation and analysis
- **NumPy 1.24.0+** - Numerical computing

### Automation & Scheduling
- **APScheduler 3.10.4** - Task scheduling (daily at 2 AM)
- **python-dateutil 2.8.2** - Date/time utilities

### Testing
- **pytest 7.4.3** - Test framework
- **pytest-cov 4.1.0** - Coverage reporting
- **pytest-mock 3.12.0** - Mocking utilities

### Configuration & Utilities
- **python-dotenv 1.0.0** - Environment variable management
- **PyYAML 6.0.1** - YAML parsing (targets.yaml)

## Development Commands

### Initial Setup
```bash
# Install all dependencies (Linux/Mac)
./setup.sh

# Install all dependencies (Windows)
setup.bat

# Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with API keys and database credentials
```

### Database Management
```bash
# Create database
psql -U postgres -c "CREATE DATABASE trading_cards;"

# Apply schema
psql -U postgres -d trading_cards -f backend/models/schema.sql

# Run migrations
./migrate.sh  # Linux/Mac
migrate.bat   # Windows
```

### Backend Development
```bash
# Install Python dependencies
cd backend
pip install -r requirements.txt

# Generate sample data (25 realistic cards)
/usr/bin/python3 -m backend.generate_sample_data

# Start API server (port 8000)
/usr/bin/python3 -m backend.api.run

# Test API endpoints
python3 backend/test_api.py

# Test opportunity finder
python3 -m backend.test_opportunities

# Run data pipeline
python3 -m backend.run_pipeline --query "Wembanyama rookie" --days 7

# Test pipeline with mock data
python3 backend/test_pipeline.py

# Start scheduler (daily at 2 AM)
python3 -m backend.run_scheduler

# Run scheduler immediately (test mode)
python3 -m backend.run_scheduler --now
```

### Frontend Development
```bash
# Install Node.js dependencies
cd frontend
npm install

# Start dev server (port 3000)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Testing
```bash
# Run all tests
./run_tests.sh all

# Run unit tests only
./run_tests.sh unit

# Run integration tests only
./run_tests.sh integration

# Run with coverage report
./run_tests.sh coverage

# Run specific test file
pytest tests/unit/test_trend_calculator.py -v
```

### Scraper Testing
```bash
# Test NovaAct scrapers (mock data)
/usr/bin/python3 -m backend.test_novaact_scrapers

# Test PSA scraper only
/usr/bin/python3 -m backend.novaact_psa_template

# Test Card Ladder scraper only
/usr/bin/python3 -m backend.novaact_cardladder_template

# Test real PSA scraping
python3 backend/test_psa_real.py
```

### Data Management
```bash
# Import target players
python3 backend/import_targets.py

# Generate mock listings
python3 backend/generate_mock_listings.py

# Calculate realistic profit margins
python3 backend/calculate_realistic_profit.py

# Track prediction accuracy
python3 backend/track_accuracy.py

# Discover watchlist opportunities
python3 backend/discover_watchlist.py
```

### AWS Deployment
```bash
# Deploy eBay compliance Lambda (Linux/Mac)
./aws/deploy-ebay-compliance.sh

# Deploy eBay compliance Lambda (Windows)
aws\deploy-ebay-compliance.bat

# Validate CloudFormation template
aws cloudformation validate-template \
  --template-body file://aws/cloudformation/ebay-compliance-lambda.yaml
```

## Build System

### Backend Build
- **Package Manager**: pip
- **Virtual Environment**: venv (recommended)
- **Dependency File**: `backend/requirements.txt`
- **Entry Points**: 
  - API: `backend/api/run.py`
  - Pipeline: `backend/run_pipeline.py`
  - Scheduler: `backend/run_scheduler.py`

### Frontend Build
- **Package Manager**: npm
- **Build Tool**: Vite
- **Dependency File**: `frontend/package.json`
- **Build Output**: `frontend/dist/`
- **Dev Server**: Hot module replacement (HMR)

## Environment Requirements

### Development
- **Python**: 3.9 or higher
- **Node.js**: 16 or higher
- **PostgreSQL**: 13 or higher
- **Chrome/Chromium**: For Selenium scrapers

### Production (AWS)
- **ECS**: Docker containers (Python 3.9 + Node 16)
- **RDS**: PostgreSQL 13+
- **Lambda**: Python 3.9 runtime
- **CloudFront**: Static asset delivery

## API Documentation
- **Interactive Docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## Port Configuration
- **Backend API**: 8000
- **Frontend Dev Server**: 3000
- **PostgreSQL**: 5432 (default)

## Version Control
- **Git**: Version control system
- **Platform**: GitHub (https://github.com/tweedledee101/TradingCards)
