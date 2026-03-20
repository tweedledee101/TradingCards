"""
Data Retention - Self-pruning database maintenance

Calls the PostgreSQL run_retention_cleanup() function to remove stale data.
Tracks when it last ran so callers can decide whether to trigger it.

Not a cron. Called by:
- find_opportunities.py after each scan completes
- /health endpoint if it hasn't run in 24 hours

Retention windows (defined in migration_008_retention.sql):
- error_log: 30 days
- job_runs: 30 days
- active_listings: 14 days (expired listings)
- price_trends: 90 days

Usage:
    from backend.utils.retention import run_if_stale
    run_if_stale()  # Only runs if last cleanup was >24h ago
"""
from datetime import datetime, timedelta
from sqlalchemy import text
from backend.utils.database import SessionLocal
from backend.utils.logger import get_logger

log = get_logger('retention')

# In-memory timestamp -- resets on process restart, which is fine.
# Worst case: cleanup runs once per process start, which is harmless.
_last_run: datetime = None


def run_cleanup() -> dict:
    """Execute retention cleanup and return deletion counts."""
    global _last_run
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT run_retention_cleanup()")).scalar()
        db.commit()
        _last_run = datetime.now()
        if result:
            total = sum(v for k, v in result.items() if k != 'ran_at')
            if total > 0:
                log.info('Retention cleanup completed', context=result)
        return result or {}
    except Exception as e:
        log.error(f'Retention cleanup failed: {e}', category='retention_error')
        return {}
    finally:
        db.close()


def run_if_stale(max_age_hours: int = 24) -> dict:
    """Run cleanup only if it hasn't run within max_age_hours."""
    global _last_run
    if _last_run and (datetime.now() - _last_run) < timedelta(hours=max_age_hours):
        return {}
    return run_cleanup()
