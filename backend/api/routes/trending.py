"""
Trending cards endpoints
"""
from fastapi import APIRouter, Query
from typing import Optional
from backend.services.data_pipeline import DataPipeline
from backend.utils.database import SessionLocal
from backend.models import Card, PriceTrend
from sqlalchemy import desc, and_
from datetime import date, timedelta

router = APIRouter()
pipeline = DataPipeline()

@router.get("/trending")
def get_trending_cards(
    limit: int = Query(default=10, ge=1, le=100),
    min_hotness: Optional[float] = Query(default=None, description="Minimum hotness score"),
    min_price: Optional[float] = Query(default=None, description="Minimum average price"),
    max_price: Optional[float] = Query(default=None, description="Maximum average price"),
    sport: Optional[str] = Query(default=None, description="Filter by sport"),
    sort_by: str = Query(default="hotness", description="Sort by: hotness, velocity, price, volume")
):
    """
    Get trending cards with filtering and sorting
    """
    db = SessionLocal()
    try:
        # Get latest trends with joins
        query = db.query(PriceTrend, Card).join(Card).filter(
            PriceTrend.trend_date >= date.today() - timedelta(days=7)
        )
        
        # Apply filters
        if min_hotness:
            query = query.filter(PriceTrend.hotness_score >= min_hotness)
        if min_price:
            query = query.filter(PriceTrend.avg_price >= min_price)
        if max_price:
            query = query.filter(PriceTrend.avg_price <= max_price)
        if sport:
            query = query.filter(Card.sport.ilike(f"%{sport}%"))
        
        # Apply sorting
        if sort_by == "velocity":
            query = query.order_by(desc(PriceTrend.velocity_score))
        elif sort_by == "price":
            query = query.order_by(desc(PriceTrend.avg_price))
        elif sort_by == "volume":
            query = query.order_by(desc(PriceTrend.sales_count))
        else:
            query = query.order_by(desc(PriceTrend.hotness_score))
        
        results = query.limit(limit).all()
        
        cards = []
        for trend, card in results:
            cards.append({
                "card_id": card.id,
                "player_name": card.player_name,
                "card_year": card.card_year,
                "card_set": card.card_set,
                "is_rookie": card.is_rookie,
                "sport": card.sport,
                "avg_price": float(trend.avg_price),
                "sales_count": trend.sales_count,
                "velocity_score": float(trend.velocity_score),
                "hotness_score": float(trend.hotness_score),
                "trend_date": trend.trend_date.isoformat()
            })
        
        return {"count": len(cards), "cards": cards}
    finally:
        db.close()

@router.get("/trending/rookies")
def get_trending_rookies(
    limit: int = Query(default=10, ge=1, le=100),
    min_hotness: Optional[float] = Query(default=None),
    sort_by: str = Query(default="hotness")
):
    """
    Get trending rookie cards only
    """
    db = SessionLocal()
    try:
        query = db.query(PriceTrend, Card).join(Card).filter(
            and_(
                Card.is_rookie == True,
                PriceTrend.trend_date >= date.today() - timedelta(days=7)
            )
        )
        
        if min_hotness:
            query = query.filter(PriceTrend.hotness_score >= min_hotness)
        
        if sort_by == "velocity":
            query = query.order_by(desc(PriceTrend.velocity_score))
        elif sort_by == "price":
            query = query.order_by(desc(PriceTrend.avg_price))
        else:
            query = query.order_by(desc(PriceTrend.hotness_score))
        
        results = query.limit(limit).all()
        
        cards = []
        for trend, card in results:
            cards.append({
                "card_id": card.id,
                "player_name": card.player_name,
                "card_year": card.card_year,
                "card_set": card.card_set,
                "sport": card.sport,
                "avg_price": float(trend.avg_price),
                "sales_count": trend.sales_count,
                "velocity_score": float(trend.velocity_score),
                "hotness_score": float(trend.hotness_score)
            })
        
        return {"count": len(cards), "cards": cards}
    finally:
        db.close()

@router.get("/stats")
def get_market_stats():
    """
    Get overall market statistics
    """
    db = SessionLocal()
    try:
        recent_date = date.today() - timedelta(days=7)
        trends = db.query(PriceTrend).filter(PriceTrend.trend_date >= recent_date).all()
        
        if not trends:
            return {"total_cards": 0, "avg_hotness": 0, "avg_price": 0, "total_volume": 0}
        
        total_volume = sum(t.sales_count for t in trends)
        avg_hotness = sum(float(t.hotness_score) for t in trends) / len(trends)
        avg_price = sum(float(t.avg_price) for t in trends) / len(trends)
        
        return {
            "total_cards": len(trends),
            "avg_hotness": round(avg_hotness, 2),
            "avg_price": round(avg_price, 2),
            "total_volume": total_volume,
            "hot_cards": len([t for t in trends if float(t.hotness_score) >= 50])
        }
    finally:
        db.close()
