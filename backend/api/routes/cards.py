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
        card = db.query(Card).filter(Card.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        
        cutoff_date = date.today() - timedelta(days=days)
        
        # Get recent sales
        recent_sales = db.query(Sale).filter(
            and_(Sale.card_id == card_id, Sale.sale_date >= cutoff_date)
        ).order_by(desc(Sale.sale_date)).limit(50).all()
        
        # Get price history (trends over time)
        price_history = db.query(PriceTrend).filter(
            and_(PriceTrend.card_id == card_id, PriceTrend.trend_date >= cutoff_date)
        ).order_by(PriceTrend.trend_date).all()
        
        # Get latest trend
        latest_trend = db.query(PriceTrend).filter(
            PriceTrend.card_id == card_id
        ).order_by(desc(PriceTrend.trend_date)).first()
        
        # Get active listings
        today = date.today()
        active_listings = db.query(ActiveListing).filter(
            and_(ActiveListing.card_id == card_id, ActiveListing.snapshot_date == today)
        ).all()
        
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
                    "grade_value": float(sale.grade_value) if sale.grade_value else None,
                    "title": sale.listing_title
                }
                for sale in recent_sales
            ],
            "price_history": [
                {
                    "date": trend.trend_date.isoformat(),
                    "avg_price": float(trend.avg_price),
                    "median_price": float(trend.median_price) if trend.median_price else None,
                    "sales_count": trend.sales_count,
                    "velocity_score": float(trend.velocity_score),
                    "hotness_score": float(trend.hotness_score)
                }
                for trend in price_history
            ],
            "current_trend": {
                "avg_price": float(latest_trend.avg_price) if latest_trend else None,
                "median_price": float(latest_trend.median_price) if latest_trend and latest_trend.median_price else None,
                "sales_count": latest_trend.sales_count if latest_trend else 0,
                "velocity_score": float(latest_trend.velocity_score) if latest_trend else None,
                "momentum_score": float(latest_trend.momentum_score) if latest_trend and latest_trend.momentum_score else None,
                "hotness_score": float(latest_trend.hotness_score) if latest_trend else None,
                "trend_date": latest_trend.trend_date.isoformat() if latest_trend else None
            },
            "active_listings": [
                {
                    "price": float(listing.listing_price),
                    "title": listing.listing_title,
                    "url": listing.listing_url
                }
                for listing in active_listings[:10]
            ],
            "active_listings_count": len(active_listings)
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
