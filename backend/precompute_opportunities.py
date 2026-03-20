"""
Pre-compute opportunities and cache as JSON.

Run after market rate collection to keep results fresh.
The API reads the cached file instead of recalculating on every request.

Usage:
    /usr/bin/python3 -m backend.precompute_opportunities
"""
import json
import os
import sys
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.utils.database import get_db
from backend.services.opportunity_analyzer import OpportunityAnalyzer

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)

CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'opportunities_cache.json')


def precompute():
    db = next(get_db())
    analyzer = OpportunityAnalyzer()

    try:
        logger.info("Computing opportunities...")
        opps = analyzer.find_opportunities(db, limit=200)
        logger.info(f"Found {len(opps)} opportunities")

        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)

        cache = {
            'computed_at': datetime.now().isoformat(),
            'count': len(opps),
            'opportunities': opps,
        }

        with open(CACHE_PATH, 'w') as f:
            json.dump(cache, f, default=str)

        logger.info(f"Cached to {CACHE_PATH}")
    finally:
        db.close()


if __name__ == '__main__':
    precompute()
