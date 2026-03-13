"""
Multi-Platform Sourcing API Endpoints

Provides sourcing options from multiple platforms for arbitrage.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.utils.database import get_db
from backend.models import Card
from backend.services.multi_platform_sourcing import MultiPlatformSourcingService

router = APIRouter()
sourcing_service = MultiPlatformSourcingService()

@router.get("/sourcing/{card_id}")
def get_sourcing_options(card_id: int, db: Session = Depends(get_db)):
    """
    Get sourcing options from all platforms for a card with dealer decision metrics
    
    Returns:
    - Platform URLs (eBay, Facebook, COMC, Whatnot, Mercari)
    - Dealer metrics (liquidity, margin, risk buffer, turnaround, deal quality score)
    """
    from backend.models import Sale
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    card = db.query(Card).get(card_id)
    if not card:
        return {"error": "Card not found"}
    
    # Get sales data for dealer metrics
    thirty_days_ago = datetime.now() - timedelta(days=30)
    sales = db.query(Sale).filter(
        Sale.card_id == card_id,
        Sale.sale_date >= thirty_days_ago
    ).all()
    
    sales_count_30d = len(sales)
    avg_price = float(sum(s.sale_price for s in sales) / len(sales)) if sales else None
    
    # Calculate avg days to sell (mock for now - would need listing date)
    avg_days_to_sell = 14 if sales_count_30d >= 10 else 30 if sales_count_30d >= 3 else None
    
    # Calculate buy zone (93% of market for velocity-adjusted)
    target_buy_price = float(avg_price * 0.93) if avg_price else None
    
    result = sourcing_service.get_sourcing_options(
        player=card.player_name,
        year=card.card_year,
        card_set=card.card_set,
        card_number=card.card_number,
        parallel=card.parallel,
        grade_company=card.grade_company,
        grade_value=float(card.grade_value) if card.grade_value else None,
        target_buy_price=target_buy_price,
        market_price=avg_price,
        sales_count_30d=sales_count_30d,
        avg_days_to_sell=avg_days_to_sell
    )
    
    return {
        "card_id": card_id,
        "player": card.player_name,
        "year": card.card_year,
        "set": card.card_set,
        "card_number": card.card_number,
        "parallel": card.parallel,
        "grade": f"{card.grade_company} {card.grade_value}" if card.grade_company else "Raw",
        "market_price": round(avg_price, 2) if avg_price else None,
        "target_buy_price": round(target_buy_price, 2) if target_buy_price else None,
        "sourcing_urls": result["urls"],
        "dealer_metrics": result["decision_metrics"]
    }
