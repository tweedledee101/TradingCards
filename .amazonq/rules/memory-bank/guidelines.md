# Trading Card Platform - Development Guidelines

## Code Quality Standards

### Documentation Style
**Pattern**: Module-level docstrings with purpose, usage examples, and key concepts
```python
"""
Trend Detection Engine

Calculates velocity, momentum, and hotness scores for trading cards.

Scoring System:
- Velocity Score: Sales volume / Active listings (demand vs supply)
- Momentum Score: Price change velocity (week-over-week)
- Hotness Score: Weighted combination of velocity + momentum + social signals

Usage:
    calculator = TrendCalculator()
    hotness = calculator.calculate_hotness_score(card_id, date)
"""
```

**Frequency**: 100% of service modules, 80% of utility modules

### Function Documentation
**Pattern**: Comprehensive docstrings with Args, Returns, and Examples
```python
def calculate_velocity_score(self, sales_count: int, active_listings: int) -> float:
    """
    Calculate velocity score (sales / listings ratio)
    
    High velocity = high demand relative to supply
    
    Args:
        sales_count: Number of sales in period (e.g., 7 days)
        active_listings: Current active listings count
        
    Returns:
        Velocity score (0-100)
        
    Example:
        >>> calc = TrendCalculator()
        >>> calc.calculate_velocity_score(50, 100)
        50.0
    """
```

**Frequency**: 90% of public methods, 60% of private methods

### Type Hints
**Pattern**: Full type annotations for function signatures
```python
from typing import Dict, List, Optional
from datetime import datetime, date

def analyze_card(self, db: Session, card_id: int) -> Optional[Dict]:
    """Analyze a single card for opportunity"""
    
def find_opportunities(
    self,
    db: Session,
    min_budget: Optional[float] = None,
    max_budget: Optional[float] = None,
    limit: int = 20
) -> List[Dict]:
    """Find all opportunities matching filters"""
```

**Frequency**: 95% of functions have type hints

### Naming Conventions
**Pattern**: Descriptive snake_case for Python, camelCase for JavaScript
```python
# Python
calculate_hotness_score()
get_trend_category()
MIN_PRICE_CONSISTENCY = 0.80
FEE_RATE = 0.13

# JavaScript/React
const CardDetail = () => {}
const fetchCardData = async () => {}
```

**Frequency**: 100% adherence

## Architectural Patterns

### Service Layer Pattern
**Pattern**: Business logic separated into focused service classes
```python
# backend/services/trend_calculator.py
class TrendCalculator:
    """Calculate trend metrics for trading cards"""
    
    def calculate_velocity_score(self, sales_count, active_listings):
        """Velocity calculation logic"""
    
    def calculate_momentum_score(self, current_price, price_7d_ago):
        """Momentum calculation logic"""
    
    def calculate_all_metrics(self, **kwargs):
        """Orchestrate all calculations"""
```

**Usage**: All business logic in `backend/services/` directory
- `trend_calculator.py` - Analytics algorithms
- `opportunity_analyzer.py` - Arbitrage detection
- `data_pipeline.py` - Data orchestration
- `report_generator.py` - Output formatting

**Frequency**: 100% of business logic uses service layer

### Repository Pattern (SQLAlchemy ORM)
**Pattern**: Database access through ORM models with relationships
```python
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

class Card(Base):
    __tablename__ = 'cards'
    
    id = Column(Integer, primary_key=True)
    player_name = Column(String(255), nullable=False)
    
    sales = relationship("Sale", back_populates="card")
    inventory = relationship("Inventory", back_populates="card")

# Usage in services
card = db.query(Card).get(card_id)
recent_sales = db.query(Sale).filter(
    Sale.card_id == card_id,
    Sale.sale_date >= thirty_days_ago
).all()
```

**Frequency**: 100% of database access uses ORM

### Dependency Injection Pattern
**Pattern**: FastAPI dependency injection for database sessions
```python
from fastapi import Depends
from backend.utils.database import get_db

@router.get("/api/cards")
def get_cards(db: Session = Depends(get_db)):
    """Database session injected automatically"""
    cards = db.query(Card).all()
    return cards
```

**Frequency**: 100% of API endpoints use dependency injection

### Caching Pattern
**Pattern**: Multi-source pricing data cached in DB with TTL
```python
# scp_cache table: player_name + card_year + card_number -> JSONB variants
# 24-hour TTL -- after that, re-scrapes via Selenium
cached = db.query(SCPCache).filter(
    SCPCache.player_name.ilike(player_name),
    SCPCache.card_year == card_year,
    SCPCache.card_number.ilike(card_number),
    SCPCache.created_at > cache_cutoff
).first()

# sold_comps table: 130point eBay sold data (populated by background worm)
# 48-hour TTL -- worm re-crawls cards with stale/missing comps
comps = db.query(SoldComp).filter(
    func.lower(SoldComp.player_name) == player_name.lower(),
    SoldComp.card_year == card_year,
    func.lower(SoldComp.card_number) == card_number.lower(),
    SoldComp.created_at > cache_cutoff
).all()
```

**Frequency**: Used in auction pipeline SCP validation + fallback pricing

### Multi-Pass Matching Pattern
**Pattern**: Progressively looser matching with confidence tracking and diagnostics
```python
# Pass 1: exact parallel name match (match_type='exact')
# Pass 2A: strict text match -- ALL words of SCP parallel in eBay title (match_type='text_match')
# Pass 2B: fuzzy word-overlap scoring -- 50%+ word overlap, best unambiguous match (match_type='text_match')
# Pass 3: narrow by signals - RC/Auto/Relic/print_run (match_type='signal_match', flagged=True)
# No match: skip with diagnostic output (variants found, pass attempts, failure reason)
# BIN sanity check: if hybrid listing BIN < 50% of SCP price, reject (seller disagrees)
```

**Frequency**: Used in auction pipeline SCP matching

## Code Idioms and Patterns

### Constants as Class Attributes
**Pattern**: Define constants at class level for configurability
```python
class OpportunityAnalyzer:
    # eBay + PayPal fees (13% total)
    FEE_RATE = 0.13
    
    # Minimum data requirements
    MIN_SALES = 3
    MIN_PRICE_CONSISTENCY = 0.80

class TrendCalculator:
    # Scoring weights
    VELOCITY_WEIGHT = 0.40
    MOMENTUM_WEIGHT = 0.35
    SOCIAL_WEIGHT = 0.25
```

**Frequency**: 90% of service classes use this pattern

### Early Return Pattern
**Pattern**: Return early for invalid states to reduce nesting
```python
def analyze_card(self, db: Session, card_id: int) -> Optional[Dict]:
    card = db.query(Card).get(card_id)
    if not card:
        return None  # Early return
    
    recent_sales = db.query(Sale).filter(...).all()
    if len(recent_sales) < self.MIN_SALES:
        return None  # Not enough data
    
    # Main logic continues without deep nesting
    market_data = self._calculate_market_data(recent_sales)
```

**Frequency**: 85% of validation logic uses early returns

### Private Helper Methods
**Pattern**: Prefix internal methods with underscore
```python
class OpportunityAnalyzer:
    def analyze_card(self, db, card_id):
        """Public API"""
        market_data = self._calculate_market_data(sales)
        arbitrage = self._calculate_arbitrage(market_rate, listings)
        momentum = self._calculate_momentum(db, card_id, sales)
    
    def _calculate_market_data(self, sales):
        """Private helper"""
    
    def _calculate_arbitrage(self, market_rate, listings):
        """Private helper"""
```

**Frequency**: 80% of service classes use private helpers

### Configuration via Environment Variables
**Pattern**: Centralized config class with dotenv
```python
from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    EBAY_APP_ID = os.getenv('EBAY_APP_ID')
    
    @property
    def database_url(self):
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}..."

config = Config()
```

**Frequency**: 100% of configuration uses this pattern

### Database Session Management
**Pattern**: Context manager pattern for session lifecycle
```python
def get_db():
    """FastAPI dependency for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Frequency**: 100% of database access uses this pattern

## Frontend Patterns

### Component Structure
**Pattern**: Functional components with hooks
```javascript
import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';

function CardDetail() {
  const { id } = useParams();
  const [card, setCard] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchCardData();
  }, [id]);
  
  const fetchCardData = async () => {
    // API call
  };
  
  return (
    <div className="container">
      {/* JSX */}
    </div>
  );
}
```

**Frequency**: 100% of components use functional style

### API Client Pattern
**Pattern**: Centralized API functions with axios
```javascript
// src/api/cards.js
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

export const fetchCards = async (filters) => {
  const response = await axios.get(`${API_BASE}/cards`, { params: filters });
  return response.data;
};
```

**Frequency**: 100% of API calls use centralized client

### Tailwind CSS Utility Classes
**Pattern**: Utility-first styling with Tailwind
```javascript
<div className="max-w-7xl mx-auto px-6 py-4">
  <h1 className="text-2xl font-bold text-blue-600">
    Trading Cards
  </h1>
  <button className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded">
    Filter
  </button>
</div>
```

**Frequency**: 100% of styling uses Tailwind utilities

## Testing Standards

### Test Organization
**Pattern**: Separate unit and integration tests
```
tests/
├── unit/
│   ├── test_trend_calculator.py
│   └── test_ebay_scraper.py
├── integration/
│   └── test_database.py
└── fixtures/
    └── sample_data.py
```

**Frequency**: 100% of tests follow this structure

### Pytest Conventions
**Pattern**: Test functions prefixed with `test_`, use fixtures
```python
import pytest
from backend.services.trend_calculator import TrendCalculator

def test_calculate_velocity_score():
    calc = TrendCalculator()
    score = calc.calculate_velocity_score(50, 100)
    assert score == 50.0

@pytest.fixture
def sample_card():
    return Card(player_name="Test Player", card_year=2023)
```

**Frequency**: 100% of tests use pytest conventions

## Error Handling

### Graceful Degradation
**Pattern**: Return None or empty results instead of raising exceptions
```python
def analyze_card(self, db: Session, card_id: int) -> Optional[Dict]:
    card = db.query(Card).get(card_id)
    if not card:
        return None  # Graceful failure
    
    if len(recent_sales) < self.MIN_SALES:
        return None  # Not enough data
```

**Frequency**: 90% of service methods use graceful degradation

### Validation at API Layer
**Pattern**: Pydantic models for request validation
```python
from pydantic import BaseModel

class PSAWebhookData(BaseModel):
    player_name: str
    card_year: int
    psa_10_count: int
    total_graded: int

@router.post("/api/webhooks/novaact/psa")
def receive_psa_data(data: PSAWebhookData, db: Session = Depends(get_db)):
    """Pydantic validates automatically"""
```

**Frequency**: 100% of API endpoints use Pydantic validation

## Performance Patterns

### Query Optimization
**Pattern**: Use SQLAlchemy query filters and joins efficiently
```python
# Good: Filter at database level
recent_sales = db.query(Sale).filter(
    Sale.card_id == card_id,
    Sale.sale_date >= thirty_days_ago
).order_by(Sale.sale_date.desc()).all()

# Avoid: Fetching all then filtering in Python
```

**Frequency**: 100% of queries use database-level filtering

### Pagination
**Pattern**: Limit results with default limits
```python
def find_opportunities(self, db: Session, limit: int = 20) -> List[Dict]:
    """Default limit prevents unbounded queries"""
    opportunities.sort(key=lambda x: x['opportunity_score'], reverse=True)
    return opportunities[:limit]
```

**Frequency**: 80% of list endpoints use pagination

## Security Practices

### SQL Injection Prevention
**Pattern**: Always use ORM parameterized queries
```python
# Good: ORM handles parameterization
db.query(Card).filter(Card.id == card_id).first()

# Avoid: Raw SQL with string interpolation
```

**Frequency**: 100% of queries use ORM

### CORS Configuration
**Pattern**: Explicit CORS middleware in FastAPI
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Frequency**: 100% of API apps configure CORS

## Development Workflow

### Module Imports
**Pattern**: Absolute imports from project root
```python
from backend.models import Card, Sale
from backend.services.trend_calculator import TrendCalculator
from backend.utils.database import get_db
```

**Frequency**: 100% of imports use absolute paths

### Entry Points
**Pattern**: Use `if __name__ == '__main__'` for runnable scripts
```python
if __name__ == '__main__':
    # Script execution logic
    main()
```

**Frequency**: 100% of standalone scripts use this pattern

### Environment Management
**Pattern**: `.env.example` for documentation, `.env` for secrets
```bash
# .env.example (committed)
DB_HOST=localhost
EBAY_APP_ID=your_app_id_here

# .env (gitignored)
DB_HOST=localhost
EBAY_APP_ID=actual_secret_key
```

**Frequency**: 100% of projects follow this pattern
