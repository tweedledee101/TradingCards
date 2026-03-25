"""
Trending cards endpoints
"""
from fastapi import APIRouter, Query, Depends
from typing import Optional
from backend.utils.auth import require_auth
from backend.services.data_pipeline import DataPipeline
from backend.utils.database import SessionLocal
from backend.models import Card, PriceTrend
from sqlalchemy import desc, and_
from datetime import date, timedelta

router = APIRouter(dependencies=[Depends(require_auth)])
pipeline = DataPipeline()

@router.get("/trending")
def get_trending_cards(
    limit: int = Query(default=100, ge=1, le=1000),
    min_hotness: Optional[float] = Query(default=None, description="Minimum hotness score"),
    min_price: Optional[float] = Query(default=5.0, description="Minimum average price"),
    max_price: Optional[float] = Query(default=None, description="Maximum average price"),
    sport: Optional[str] = Query(default=None, description="Filter by sport"),
    sort_by: str = Query(default="hotness", description="Sort by: hotness, velocity, price, volume")
):
    """
    Get trending cards - shows all cards with sales data
    """
    db = SessionLocal()
    try:
        from backend.models import Sale
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        # Get cards with recent sales, calculate metrics
        query = db.query(
            Card,
            func.count(Sale.id).label('sales_count'),
            func.avg(Sale.sale_price).label('avg_price'),
            func.min(Sale.sale_price).label('min_price'),
            func.max(Sale.sale_price).label('max_price')
        ).join(Sale).filter(
            Sale.sale_date >= thirty_days_ago
        ).group_by(Card.id)
        
        # Apply filters
        if sport:
            query = query.filter(Card.sport.ilike(f"%{sport}%"))
        
        # Sort by sales count (volume)
        query = query.order_by(func.count(Sale.id).desc())
        
        results = query.limit(limit).all()
        
        cards = []
        for card, sales_count, avg_price, min_price, max_price in results:
            if avg_price and avg_price >= min_price:
                if max_price is None or avg_price <= max_price:
                    # Calculate velocity: sales per week
                    velocity_score = min((sales_count / 4.3) * 10, 100)  # 4.3 weeks in 30 days
                    
                    # Calculate hotness based on volume and price range
                    price_range = (float(max_price) - float(min_price)) / float(avg_price) if avg_price > 0 else 0
                    consistency_score = max(0, 100 - (price_range * 100))  # Lower range = higher score
                    hotness_score = (velocity_score * 0.6) + (consistency_score * 0.4)
                    
                    cards.append({
                        "card_id": card.id,
                        "player_name": card.player_name,
                        "card_year": card.card_year,
                        "card_set": card.card_set,
                        "card_number": card.card_number,
                        "parallel": card.parallel,
                        "grade_company": card.grade_company,
                        "grade_value": float(card.grade_value) if card.grade_value else None,
                        "image_url": card.image_url,
                        "is_rookie": card.is_rookie,
                        "sport": card.sport,
                        "avg_price": float(avg_price),
                        "sales_count": sales_count,
                        "velocity_score": round(velocity_score, 1),
                        "hotness_score": round(hotness_score, 1),
                        "trend_date": date.today().isoformat()
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
