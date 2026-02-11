"""
Card detail endpoints
"""
from fastapi import APIRouter, HTTPException
from datetime import date, timedelta
from backend.utils.database import SessionLocal
from backend.models import Card, Sale, ActiveListing, PriceTrend
from sqlalchemy import func, desc

router = APIRouter()

@router.get("/cards/{card_id}")
def get_card_details(card_id: int):
    """
    Get detailed information about a specific card
    """
    db = SessionLocal()
    try:
        card = db.query(Card).filter(Card.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        
        # Get recent sales
        recent_sales = db.query(Sale).filter(
            Sale.card_id == card_id
        ).order_by(desc(Sale.sale_date)).limit(10).all()
        
        # Get latest trend
        latest_trend = db.query(PriceTrend).filter(
            PriceTrend.card_id == card_id
        ).order_by(desc(PriceTrend.trend_date)).first()
        
        # Get active listings count
        today = date.today()
        listings_count = db.query(ActiveListing).filter(
            ActiveListing.card_id == card_id,
            ActiveListing.snapshot_date == today
        ).count()
        
        return {
            "id": card.id,
            "player_name": card.player_name,
            "card_year": card.card_year,
            "card_set": card.card_set,
            "card_number": card.card_number,
            "is_rookie": card.is_rookie,
            "sport": card.sport,
            "recent_sales": [
                {
                    "price": float(sale.sale_price),
                    "date": sale.sale_date.isoformat(),
                    "graded": sale.graded,
                    "grade_company": sale.grade_company,
                    "grade_value": float(sale.grade_value) if sale.grade_value else None
                }
                for sale in recent_sales
            ],
            "trend": {
                "avg_price": float(latest_trend.avg_price) if latest_trend else None,
                "sales_count": latest_trend.sales_count if latest_trend else 0,
                "velocity_score": float(latest_trend.velocity_score) if latest_trend else None,
                "hotness_score": float(latest_trend.hotness_score) if latest_trend else None,
                "trend_date": latest_trend.trend_date.isoformat() if latest_trend else None
            },
            "active_listings_count": listings_count
        }
    finally:
        db.close()

@router.get("/cards")
def search_cards(
    player: str = None,
    year: int = None,
    rookie_only: bool = False,
    limit: int = 20
):
    """
    Search for cards by player name, year, or rookie status
    """
    db = SessionLocal()
    try:
        query = db.query(Card)
        
        if player:
            query = query.filter(Card.player_name.ilike(f"%{player}%"))
        if year:
            query = query.filter(Card.card_year == year)
        if rookie_only:
            query = query.filter(Card.is_rookie == True)
        
        cards = query.limit(limit).all()
        
        return {
            "count": len(cards),
            "cards": [
                {
                    "id": card.id,
                    "player_name": card.player_name,
                    "card_year": card.card_year,
                    "card_set": card.card_set,
                    "is_rookie": card.is_rookie,
                    "sport": card.sport
                }
                for card in cards
            ]
        }
    finally:
        db.close()
