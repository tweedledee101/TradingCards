"""
Notifications API - in-app messaging for sales, pipeline results, and system alerts.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import datetime

from backend.utils.database import get_db
from backend.utils.auth import require_auth
from backend.models import User

router = APIRouter(dependencies=[Depends(require_auth)])


@router.get("/notifications")
def get_notifications(
    unread_only: bool = Query(default=False),
    type: Optional[str] = Query(default=None, description="sale, opportunity, pipeline, system"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get notifications for the current user."""
    q = "SELECT id, type, title, message, data, read, created_at FROM notifications WHERE account_id = :aid"
    params = {"aid": user.account_id}

    if unread_only:
        q += " AND read = FALSE"
    if type:
        q += " AND type = :type"
        params["type"] = type

    q += " ORDER BY created_at DESC LIMIT :lim"
    params["lim"] = limit

    rows = db.execute(text(q), params).fetchall()
    return {
        "notifications": [
            {
                "id": r[0],
                "type": r[1],
                "title": r[2],
                "message": r[3],
                "data": r[4] or {},
                "read": r[5],
                "created_at": r[6].isoformat() if r[6] else None,
            }
            for r in rows
        ],
        "unread_count": sum(1 for r in rows if not r[5]),
    }


@router.get("/notifications/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Quick unread count for badge display."""
    count = db.execute(
        text("SELECT COUNT(*) FROM notifications WHERE account_id = :aid AND read = FALSE"),
        {"aid": user.account_id},
    ).scalar() or 0
    return {"unread_count": count}


@router.post("/notifications/{notification_id}/read")
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Mark a single notification as read."""
    db.execute(
        text("UPDATE notifications SET read = TRUE WHERE id = :id AND account_id = :aid"),
        {"id": notification_id, "aid": user.account_id},
    )
    db.commit()
    return {"success": True}


@router.post("/notifications/mark-all-read")
def mark_all_read(
    db: Session = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Mark all notifications as read."""
    db.execute(
        text("UPDATE notifications SET read = TRUE WHERE account_id = :aid AND read = FALSE"),
        {"aid": user.account_id},
    )
    db.commit()
    return {"success": True}


# --- Helper for other services to create notifications ---

def create_notification(
    db: Session,
    account_id: int,
    type: str,
    title: str,
    message: str = None,
    data: dict = None,
):
    """Create a notification. Called by pipeline, sale recording, etc."""
    db.execute(
        text(
            "INSERT INTO notifications (account_id, type, title, message, data) "
            "VALUES (:aid, :type, :title, :msg, :data)"
        ),
        {
            "aid": account_id,
            "type": type,
            "title": title,
            "msg": message,
            "data": __import__('json').dumps(data or {}),
        },
    )
    db.commit()
