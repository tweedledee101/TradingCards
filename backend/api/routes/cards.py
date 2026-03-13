"""
Card detail endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from datetime import date, timedelta
from typing import Optional
from backend.utils.database import SessionLocal
from backend.models import Card, Sale, ActiveListing, PriceTrend
from sqlalchemy import func, desc, and_

router = APIRouter()

@router.get("/cards/{card_id}")
def get_card_details(card_id: int, days: int = Query(default=30, description="Days of history")):
    """
    Get detailed information about a specific card with price history
    """
    db = SessionLocal()
    try:
        from datetime import datetime
        
        card = db.query(Card).filter(Card.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get recent sales
        recent_sales = db.query(Sale).filter(
            and_(Sale.card_id == card_id, Sale.sale_date >= cutoff_date)
        ).order_by(desc(Sale.sale_date)).limit(50).all()
        
        # Calculate current trend from sales
        if recent_sales:
            prices = [float(s.sale_price) for s in recent_sales]
            avg_price = sum(prices) / len(prices)
            sales_count = len(recent_sales)
            velocity_score = min((sales_count / 4.3) * 10, 100)  # 4.3 weeks in 30 days
            hotness_score = velocity_score  # Simplified
        else:
            avg_price = None
            sales_count = 0
            velocity_score = 0
            hotness_score = 0
        
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
                    "date": sale.sale_date.isoformat() if hasattr(sale.sale_date, 'isoformat') else str(sale.sale_date),
                    "graded": sale.graded,
                    "grade_company": sale.grade_company,
                    "grade_value": float(sale.grade_value) if sale.grade_value else None,
                    "title": sale.listing_title
                }
                for sale in recent_sales
            ],
            "price_history": [],  # Empty for now
            "current_trend": {
                "avg_price": avg_price,
                "median_price": None,
                "sales_count": sales_count,
                "velocity_score": velocity_score,
                "momentum_score": None,
                "hotness_score": hotness_score,
                "trend_date": date.today().isoformat()
            },
            "active_listings": [],  # Empty for now
            "active_listings_count": 0
        }
    finally:
        db.close()

@router.get("/cards")
def search_cards(
    player: Optional[str] = None,
    year: Optional[int] = None,
    card_set: Optional[str] = None,
    rookie_only: bool = False,
    sport: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0)
):
    """
    Search for cards with pagination
    """
    db = SessionLocal()
    try:
        query = db.query(Card)
        
        if player:
            query = query.filter(Card.player_name.ilike(f"%{player}%"))
        if year:
            query = query.filter(Card.card_year == year)
        if card_set:
            query = query.filter(Card.card_set.ilike(f"%{card_set}%"))
        if rookie_only:
            query = query.filter(Card.is_rookie == True)
        if sport:
            query = query.filter(Card.sport.ilike(f"%{sport}%"))
        
        total = query.count()
        cards = query.offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "count": len(cards),
            "offset": offset,
            "limit": limit,
            "cards": [
                {
                    "id": card.id,
                    "player_name": card.player_name,
                    "card_year": card.card_year,
                    "card_set": card.card_set,
                    "card_number": card.card_number,
                    "is_rookie": card.is_rookie,
                    "sport": card.sport
                }
                for card in cards
            ]
        }
    finally:
        db.close()

@router.get("/accuracy/stats")
def get_accuracy_stats():
    """Get overall accuracy statistics for predictions"""
    from sqlalchemy import text
    db = SessionLocal()
    try:
        stats = db.execute(text("SELECT * FROM accuracy_stats")).fetchone()
        
        if not stats or stats.total_predictions == 0:
            return {
                "total_predictions": 0,
                "correct_predictions": 0,
                "accuracy_pct": 0,
                "avg_price_accuracy": 0,
                "avg_velocity_accuracy": 0,
                "first_prediction": None,
                "last_prediction": None
            }
        
        return {
            "total_predictions": stats.total_predictions,
            "correct_predictions": stats.correct_predictions,
            "accuracy_pct": float(stats.accuracy_pct),
            "avg_price_accuracy": float(stats.avg_price_accuracy) if stats.avg_price_accuracy else 0,
            "avg_velocity_accuracy": float(stats.avg_velocity_accuracy) if stats.avg_velocity_accuracy else 0,
            "first_prediction": stats.first_prediction.isoformat() if stats.first_prediction else None,
            "last_prediction": stats.last_prediction.isoformat() if stats.last_prediction else None
        }
    finally:
        db.close()
