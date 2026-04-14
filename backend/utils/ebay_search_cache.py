"""eBay Browse API search result cache.

Stores search results in ``ebay_search_cache`` table with a configurable TTL.
Cache hit = 0 API calls. Cache miss = normal API call + store results.

Usage in BIN pipeline:
    from backend.utils.ebay_search_cache import cached_get_active_listings
    listings = cached_get_active_listings(scraper, query, db, ttl_hours=12)
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


def _query_hash(query: str) -> str:
    return hashlib.sha256(query.strip().lower().encode()).hexdigest()[:40]


def get_cached_results(db: Session, query: str, ttl_hours: int = 12) -> Optional[List[Dict]]:
    """Return cached listings if fresh, else None."""
    qh = _query_hash(query)
    cutoff = datetime.utcnow() - timedelta(hours=ttl_hours)
    row = db.execute(
        text(
            "SELECT results FROM ebay_search_cache "
            "WHERE query_hash = :qh AND created_at > :cutoff "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"qh": qh, "cutoff": cutoff},
    ).fetchone()
    if row is None:
        return None
    results = row[0]
    if isinstance(results, str):
        results = json.loads(results)
    return results


def store_cache(db: Session, query: str, results: List[Dict]) -> None:
    """Store search results in cache."""
    qh = _query_hash(query)
    serializable = []
    for r in results:
        item = {}
        for k, v in r.items():
            if k == "card_info":
                continue  # derived, not needed in cache
            item[k] = v
        serializable.append(item)
    db.execute(
        text(
            "INSERT INTO ebay_search_cache (search_query, query_hash, results, result_count, created_at) "
            "VALUES (:q, :qh, :results, :cnt, NOW())"
        ),
        {
            "q": query[:2000],
            "qh": qh,
            "results": json.dumps(serializable),
            "cnt": len(serializable),
        },
    )
    db.commit()


def cached_get_active_listings(
    scraper,
    query: str,
    db: Session,
    *,
    ttl_hours: int = 12,
    max_total: int = 1000,
) -> List[Dict]:
    """get_active_listings with DB cache. Returns listings (possibly from cache)."""
    cached = get_cached_results(db, query, ttl_hours=ttl_hours)
    if cached is not None:
        return cached

    listings = scraper.get_active_listings(query, max_total=max_total)
    try:
        store_cache(db, query, listings)
    except Exception:
        pass  # cache write failure is non-fatal
    return listings
