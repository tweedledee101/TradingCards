#!/bin/bash
# Test runner script for Trading Card Platform

set -e

echo "🧪 Trading Card Platform Test Suite"
echo "===================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse arguments
TEST_TYPE=${1:-all}

case $TEST_TYPE in
    unit)
        echo -e "${YELLOW}Running unit tests only...${NC}"
        pytest tests/unit/ -v -m unit
        ;;
    integration)
        echo -e "${YELLOW}Running integration tests only...${NC}"
        echo "⚠️  Make sure test database is running!"
        pytest tests/integration/ -v -m integration
        ;;
    coverage)
        echo -e "${YELLOW}Running all tests with coverage...${NC}"
        pytest --cov=backend --cov-report=html --cov-report=term-missing
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    quick)
        echo -e "${YELLOW}Running quick tests (unit only, no coverage)...${NC}"
        pytest tests/unit/ -v -m unit --tb=short
        ;;
    all)
        echo -e "${YELLOW}Running all tests...${NC}"
        pytest -v
        ;;
    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo "Usage: ./run_tests.sh [unit|integration|coverage|quick|all]"
        exit 1
        ;;
esac

# Check exit code
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
else
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi
