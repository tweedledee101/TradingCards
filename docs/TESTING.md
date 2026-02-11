# Testing Guide

Comprehensive testing strategy for the Trading Card Platform.

## Test Structure

```
tests/
├── unit/                    # Unit tests (fast, no external dependencies)
│   └── test_ebay_scraper.py
├── integration/             # Integration tests (database, API)
│   └── test_database.py
├── fixtures/                # Test data and mocks
│   └── sample_data.py
└── __init__.py
```

## Test Types

### Unit Tests
- **Purpose:** Test individual functions and methods in isolation
- **Speed:** Fast (< 1 second per test)
- **Dependencies:** None (mocked)
- **Run:** `pytest tests/unit/ -m unit`

**What we test:**
- Title parsing logic
- Data extraction from API responses
- Edge cases and error handling
- Data type conversions

### Integration Tests
- **Purpose:** Test database operations and data flow
- **Speed:** Slower (requires database)
- **Dependencies:** PostgreSQL test database
- **Run:** `pytest tests/integration/ -m integration`

**What we test:**
- Database schema and constraints
- CRUD operations
- Foreign key relationships
- Complete data flow (scraper → database)
- Velocity and trend calculations

## Running Tests

### Quick Start

```bash
# Make test runner executable
chmod +x run_tests.sh

# Run all tests
./run_tests.sh all

# Run only unit tests (fast)
./run_tests.sh unit

# Run with coverage report
./run_tests.sh coverage
```

### Using pytest directly

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Specific test file
pytest tests/unit/test_ebay_scraper.py -v

# Specific test function
pytest tests/unit/test_ebay_scraper.py::TestTitleParsing::test_rookie_detection_rc -v

# With coverage
pytest --cov=backend --cov-report=html

# Stop on first failure
pytest -x

# Show print statements
pytest -s
```

## Test Database Setup

Integration tests require a separate test database:

```bash
# Create test database
sudo -u postgres psql -c "CREATE DATABASE trading_cards_test;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE trading_cards_test TO carduser;"

# Run schema
psql -U carduser -d trading_cards_test -f backend/models/schema.sql
```

**Important:** Test database is cleaned before each test to ensure isolation.

## Test Coverage Goals

| Component | Target Coverage | Current |
|-----------|----------------|---------|
| Scrapers | 90%+ | TBD |
| Database Utils | 85%+ | TBD |
| API Endpoints | 90%+ | TBD |
| Trend Calculations | 95%+ | TBD |
| Overall | 85%+ | TBD |

View coverage report:
```bash
pytest --cov=backend --cov-report=html
open htmlcov/index.html  # or xdg-open on Linux
```

## Writing Tests

### Unit Test Example

```python
import pytest
from backend.scrapers.ebay_scraper import EbayScraper

@pytest.fixture
def scraper():
    return EbayScraper()

@pytest.mark.unit
def test_rookie_detection(scraper):
    """Test RC abbreviation is detected"""
    result = scraper._extract_card_info("2023 Player RC")
    assert result['is_rookie'] is True
```

### Integration Test Example

```python
import pytest
from sqlalchemy import text

@pytest.mark.integration
def test_insert_card(clean_db):
    """Test inserting a card"""
    clean_db.execute(text("""
        INSERT INTO cards (player_name, card_year, is_rookie, sport)
        VALUES ('Test Player', 2023, true, 'Basketball')
    """))
    clean_db.commit()
    
    result = clean_db.execute(text("SELECT * FROM cards"))
    assert result.rowcount == 1
```

## Test Fixtures

Located in `tests/fixtures/sample_data.py`:

- `EBAY_SOLD_RESPONSE` - Mock eBay API response
- `EXPECTED_PARSED_SALES` - Expected parsed results
- `TITLE_PARSING_TESTS` - Test cases for title parsing
- `SAMPLE_CARDS` - Sample card records
- `SAMPLE_SALES` - Sample sales data

## Continuous Integration

### Pre-commit Checks

Before committing:
```bash
# Run quick tests
./run_tests.sh quick

# Check coverage
./run_tests.sh coverage
```

### GitHub Actions (Future)

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          pip install -r backend/requirements.txt
          pytest --cov=backend
```

## Test Data Management

### Sample Data
- Use fixtures for consistent test data
- Keep test data minimal but realistic
- Document edge cases in fixtures

### Database Cleanup
- Integration tests clean database before each test
- Use transactions and rollback for failed tests
- Never use production database for testing

## Debugging Tests

### Failed Test
```bash
# Show full traceback
pytest tests/unit/test_ebay_scraper.py -v --tb=long

# Drop into debugger on failure
pytest tests/unit/test_ebay_scraper.py --pdb

# Show print statements
pytest tests/unit/test_ebay_scraper.py -s
```

### Slow Tests
```bash
# Show slowest tests
pytest --durations=10

# Profile tests
pytest --profile
```

## Common Issues

### Issue: Import errors
**Solution:** Make sure you're in the project root and backend is in PYTHONPATH
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Issue: Database connection refused
**Solution:** Ensure PostgreSQL is running and test database exists
```bash
sudo service postgresql status
psql -U carduser -d trading_cards_test -c "SELECT 1;"
```

### Issue: Tests pass individually but fail together
**Solution:** Tests may have shared state. Check database cleanup in fixtures.

## Test Markers

We use pytest markers to categorize tests:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow running tests
- `@pytest.mark.scraper` - Tests that hit external APIs

Run specific markers:
```bash
pytest -m unit
pytest -m "not slow"
pytest -m "unit and not slow"
```

## Best Practices

1. **Test Naming:** Use descriptive names (`test_rookie_detection_rc` not `test1`)
2. **One Assert Per Test:** Focus on single behavior
3. **Arrange-Act-Assert:** Structure tests clearly
4. **Mock External Calls:** Don't hit real APIs in unit tests
5. **Clean Database:** Ensure test isolation
6. **Fast Tests:** Keep unit tests under 1 second
7. **Document Edge Cases:** Explain why test exists

## Test Metrics

Track these metrics:
- **Coverage:** % of code executed by tests
- **Pass Rate:** % of tests passing
- **Test Speed:** Average test execution time
- **Flakiness:** Tests that fail intermittently

## Next Steps

- [ ] Add tests for trend detection algorithms
- [ ] Add tests for PSA scraper
- [ ] Add API endpoint tests
- [ ] Set up CI/CD pipeline
- [ ] Add performance tests
- [ ] Add end-to-end tests

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)

---

**Last Updated:** 2025-02-11  
**Version:** 1.0.0
