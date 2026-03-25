"""
Watchlist endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from backend.utils.auth import require_auth
from pydantic import BaseModel
from typing import Optional
from backend.utils.database import SessionLocal
from backend.models import Watchlist, Card, PriceTrend
from sqlalchemy import desc, func
from datetime import date, timedelta

router = APIRouter(dependencies=[Depends(require_auth)])

class WatchlistCreate(BaseModel):
    card_id: int
    target_price: Optional[float] = None
    alert_threshold: Optional[float] = 5.0  # 5% default
    notes: Optional[str] = None

@router.post("/watchlist")
def add_to_watchlist(item: WatchlistCreate):
    """Add a card to watchlist"""
    db = SessionLocal()
    try:
        # Verify card exists
        card = db.query(Card).filter(Card.id == item.card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        
        # Check if already in watchlist
        existing = db.query(Watchlist).filter(Watchlist.card_id == item.card_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Card already in watchlist")
        
        watchlist_item = Watchlist(
            card_id=item.card_id,
            target_price=item.target_price,
            alert_threshold=item.alert_threshold,
            notes=item.notes
        )
        db.add(watchlist_item)
        db.commit()
        db.refresh(watchlist_item)
        
        return {"id": watchlist_item.id, "message": "Added to watchlist"}
    finally:
        db.close()

@router.get("/watchlist")
def get_watchlist():
    """Get user's watchlist with current prices"""
    db = SessionLocal()
    try:
        # Get watchlist items with latest trends
        items = db.query(Watchlist, Card, PriceTrend).select_from(Watchlist).join(
            Card, Watchlist.card_id == Card.id
        ).outerjoin(
            PriceTrend, PriceTrend.card_id == Card.id
        ).filter(
            PriceTrend.trend_date >= date.today() - timedelta(days=7)
        ).order_by(desc(Watchlist.added_at)).all()
        
        watchlist = []
        for watch, card, trend in items:
            current_price = float(trend.avg_price) if trend else None
            target_price = float(watch.target_price) if watch.target_price else None
            
            # Check if alert should trigger
            alert = False
            if current_price and target_price:
                price_diff_pct = abs((current_price - target_price) / target_price * 100)
                if price_diff_pct <= float(watch.alert_threshold):
                    alert = True
            
            watchlist.append({
                "id": watch.id,
                "card": {
                    "id": card.id,
                    "player_name": card.player_name,
                    "card_year": card.card_year,
                    "card_set": card.card_set,
                    "is_rookie": card.is_rookie
                },
                "target_price": target_price,
                "current_price": current_price,
                "alert_threshold": float(watch.alert_threshold),
                "alert": alert,
                "notes": watch.notes,
                "added_at": watch.added_at.isoformat(),
                "trend": {
                    "velocity_score": float(trend.velocity_score) if trend else None,
                    "hotness_score": float(trend.hotness_score) if trend else None
                } if trend else None
            })
        
        return {"count": len(watchlist), "watchlist": watchlist}
    finally:
        db.close()

@router.delete("/watchlist/{watchlist_id}")
def remove_from_watchlist(watchlist_id: int):
    """Remove a card from watchlist"""
    db = SessionLocal()
    try:
        item = db.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Watchlist item not found")
        
        db.delete(item)
        db.commit()
        
        return {"message": "Removed from watchlist"}
    finally:
        db.close()

@router.get("/watchlist/alerts")
def get_watchlist_alerts():
    """Get cards that have hit target prices"""
    db = SessionLocal()
    try:
        items = db.query(Watchlist, Card, PriceTrend).select_from(Watchlist).join(
            Card, Watchlist.card_id == Card.id
        ).join(
            PriceTrend, PriceTrend.card_id == Card.id
        ).filter(
            PriceTrend.trend_date >= date.today() - timedelta(days=7)
        ).all()
        
        alerts = []
        for watch, card, trend in items:
            current_price = float(trend.avg_price)
            target_price = float(watch.target_price) if watch.target_price else None
            
            if target_price:
                price_diff_pct = abs((current_price - target_price) / target_price * 100)
                if price_diff_pct <= float(watch.alert_threshold):
                    alerts.append({
                        "card": {
                            "id": card.id,
                            "player_name": card.player_name,
                            "card_year": card.card_year,
                            "card_set": card.card_set
                        },
                        "target_price": target_price,
                        "current_price": current_price,
                        "difference": round(current_price - target_price, 2),
                        "difference_pct": round(price_diff_pct, 2)
                    })
        
        return {"count": len(alerts), "alerts": alerts}
    finally:
        db.close()
