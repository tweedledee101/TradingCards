# ADR-003: Testing Strategy and Framework

**Date:** 2025-02-11  
**Status:** Accepted  
**Deciders:** Development Team

## Context

We need a comprehensive testing strategy to ensure:
- Data structures work as designed
- Scrapers parse data correctly
- Database operations maintain integrity
- Data flows correctly through the system
- Code quality and reliability

## Decision

We will implement a **multi-layered testing approach** using **pytest** as our testing framework.

## Testing Layers

### 1. Unit Tests
**Purpose:** Test individual functions in isolation

**Coverage:**
- Title parsing logic (rookie detection, year extraction, grading info)
- Data type conversions
- Edge cases and error handling
- API response parsing

**Characteristics:**
- Fast (< 1 second per test)
- No external dependencies (mocked)
- High coverage target (90%+)

### 2. Integration Tests
**Purpose:** Test database operations and data flow

**Coverage:**
- Database schema and constraints
- CRUD operations
- Foreign key relationships
- Complete data flow (scraper → database)
- Trend calculations with real data

**Characteristics:**
- Slower (requires database)
- Uses separate test database
- Ensures components work together

### 3. End-to-End Tests (Future)
**Purpose:** Test complete user workflows

**Coverage:**
- API endpoints
- Frontend interactions
- Complete data pipeline

## Framework Choice: pytest

### Why pytest?

**Pros:**
- Industry standard for Python testing
- Simple, readable syntax
- Powerful fixtures for setup/teardown
- Excellent plugin ecosystem (pytest-cov, pytest-mock)
- Parametrized tests for multiple test cases
- Clear assertion messages
- Great documentation

**Cons:**
- Learning curve for advanced features
- Can be slow if not organized properly

### Alternatives Considered

**unittest (Python standard library):**
- More verbose syntax
- Less flexible fixtures
- No parametrization without extra work
- Decision: pytest is more modern and productive

**nose2:**
- Less actively maintained
- Smaller community
- Decision: pytest has better ecosystem

## Test Organization

```
tests/
├── unit/              # Fast, isolated tests
├── integration/       # Database and data flow tests
├── fixtures/          # Shared test data
└── conftest.py        # Shared fixtures (future)
```

## Test Data Strategy

### Fixtures
- Store sample API responses in `fixtures/sample_data.py`
- Reusable across multiple tests
- Version controlled
- Documented edge cases

### Test Database
- Separate `trading_cards_test` database
- Cleaned before each test
- Never use production data
- Same schema as production

## Coverage Goals

| Component | Target | Rationale |
|-----------|--------|-----------|
| Scrapers | 90%+ | Critical for data quality |
| Database Utils | 85%+ | Core infrastructure |
| API Endpoints | 90%+ | User-facing |
| Trend Calculations | 95%+ | Business logic |
| Overall | 85%+ | Industry standard |

## Test Execution

### Local Development
```bash
# Quick feedback loop
./run_tests.sh unit

# Before commit
./run_tests.sh coverage
```

### CI/CD (Future)
- Run on every push
- Block merge if tests fail
- Generate coverage reports
- Track coverage trends

## Mocking Strategy

**Mock External APIs:**
- eBay API calls
- PSA website scraping
- Social media APIs

**Don't Mock:**
- Database operations (use test DB)
- Internal functions (test real behavior)
- Data structures

## Test Markers

Use pytest markers to categorize tests:
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow tests (skip in quick runs)
- `@pytest.mark.scraper` - Tests hitting external APIs

## Consequences

**Positive:**
- High confidence in code quality
- Catch bugs early
- Safe refactoring
- Documentation through tests
- Faster debugging

**Negative:**
- Initial time investment to write tests
- Test maintenance overhead
- Slower CI/CD pipeline (mitigated by test organization)

**Neutral:**
- Need to maintain test database
- Learning curve for team members new to pytest

## Implementation Notes

### Test Naming Convention
```python
def test_<what>_<condition>_<expected>():
    # Example: test_rookie_detection_rc_returns_true
```

### Test Structure (Arrange-Act-Assert)
```python
def test_example():
    # Arrange: Set up test data
    scraper = EbayScraper()
    
    # Act: Execute the function
    result = scraper._extract_card_info("2023 Player RC")
    
    # Assert: Verify the result
    assert result['is_rookie'] is True
```

### Fixture Usage
```python
@pytest.fixture
def scraper():
    return EbayScraper()

def test_with_fixture(scraper):
    result = scraper.search_sold_listings("test")
    assert isinstance(result, list)
```

## Success Metrics

Track these metrics:
1. **Test Coverage:** % of code covered by tests
2. **Pass Rate:** % of tests passing
3. **Test Speed:** Average execution time
4. **Flakiness:** Tests that fail intermittently

## Future Enhancements

- [ ] Add performance tests for slow queries
- [ ] Add load tests for API endpoints
- [ ] Add mutation testing (pytest-mutpy)
- [ ] Add property-based testing (hypothesis)
- [ ] Set up test coverage tracking (Codecov)
- [ ] Add visual regression tests for frontend

## Supplement (2026): Outcome-oriented testing

Correctness tests remain the default. **Product-fit** checks (pipeline funnel health, identity-trust sampling, coverage vs goals) are documented in [docs/testing/strategy.md](../../testing/strategy.md). Pytest marker **`outcome`** flags tests that encode those baselines.

## Related Decisions

- ADR-001: PostgreSQL database (affects integration tests)
- ADR-002: eBay as primary source (affects scraper tests)
- ADR-004: CI/CD pipeline (planned)

## References

- [pytest Documentation](https://docs.pytest.org/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [Test-Driven Development](https://martinfowler.com/bliki/TestDrivenDevelopment.html)

---

**Review Date:** 2025-05-11 (3 months)  
**Next Steps:** Implement tests for trend detection algorithms
