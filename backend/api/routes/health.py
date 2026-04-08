"""
Health check, system status, and observability endpoints
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc, text
from datetime import datetime, timedelta
from typing import Optional
from backend.utils.database import get_db
from backend.utils.auth import require_auth
from backend.models import User
from backend.utils.job_tracker import JobTracker
from backend.utils.retention import run_if_stale
from backend.models import ErrorLog

router = APIRouter()


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check with DB connectivity test and background retention"""
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    # Trigger retention if stale (non-blocking, fails silently)
    retention_result = {}
    postgres_db_name = None
    if db_status == "connected":
        try:
            retention_result = run_if_stale()
        except Exception:
            pass
        try:
            postgres_db_name = db.execute(text("SELECT current_database()")).scalar_one_or_none()
        except Exception:
            postgres_db_name = None

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "service": "trading-card-api",
        "database": db_status,
        "postgres_db_name": postgres_db_name,
        "retention": retention_result if retention_result else "skipped"
    }


@router.get("/api/status")
def system_status(_user: User = Depends(require_auth)):
    """Get status of all background jobs"""
    jobs = JobTracker.get_status()
    return {
        "timestamp": datetime.now().isoformat(),
        "jobs": jobs
    }


@router.get("/api/status/{job_name}")
def job_status(job_name: str, _user: User = Depends(require_auth)):
    """Get status of a specific job"""
    status = JobTracker.get_status(job_name)
    if not status:
        return {"job_name": job_name, "status": "never_run"}
    return status


@router.get("/api/errors")
def get_errors(
    hours: int = Query(default=24, ge=1, le=168),
    level: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_auth),
):
    """Get recent errors with optional filtering"""
    since = datetime.now() - timedelta(hours=hours)
    query = db.query(ErrorLog).filter(ErrorLog.timestamp >= since)

    if level:
        query = query.filter(ErrorLog.level == level.upper())
    if category:
        query = query.filter(ErrorLog.category == category)

    entries = query.order_by(ErrorLog.timestamp.desc()).limit(limit).all()

    return {
        "count": len(entries),
        "hours": hours,
        "entries": [{
            "id": e.id,
            "timestamp": e.timestamp.isoformat(),
            "level": e.level,
            "category": e.category,
            "source": e.source,
            "message": e.message,
            "context": e.context,
            "request_id": e.request_id
        } for e in entries]
    }


@router.get("/api/errors/summary")
def error_summary(
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db),
    _user: User = Depends(require_auth),
):
    """Error rate summary -- category counts, severity breakdown, top sources"""
    since = datetime.now() - timedelta(hours=hours)

    # Count by level
    level_counts = db.query(
        ErrorLog.level, sqlfunc.count(ErrorLog.id)
    ).filter(
        ErrorLog.timestamp >= since
    ).group_by(ErrorLog.level).all()

    # Count by category
    category_counts = db.query(
        ErrorLog.category, sqlfunc.count(ErrorLog.id)
    ).filter(
        ErrorLog.timestamp >= since
    ).group_by(ErrorLog.category).order_by(
        sqlfunc.count(ErrorLog.id).desc()
    ).limit(10).all()

    # Count by source
    source_counts = db.query(
        ErrorLog.source, sqlfunc.count(ErrorLog.id)
    ).filter(
        ErrorLog.timestamp >= since
    ).group_by(ErrorLog.source).order_by(
        sqlfunc.count(ErrorLog.id).desc()
    ).limit(10).all()

    total = sum(c for _, c in level_counts)

    return {
        "hours": hours,
        "total_entries": total,
        "by_level": {level: count for level, count in level_counts},
        "by_category": {cat or "uncategorized": count for cat, count in category_counts},
        "by_source": {src or "unknown": count for src, count in source_counts}
    }
