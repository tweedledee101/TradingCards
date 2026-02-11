"""
Inventory management endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import date
from backend.utils.database import SessionLocal
from backend.models import Inventory, InventorySale, Card, PriceTrend
from sqlalchemy import desc, func

router = APIRouter()

class InventoryCreate(BaseModel):
    card_id: int
    purchase_date: date
    purchase_price: float
    purchase_source: Optional[str] = None
    quantity: int = 1
    condition: Optional[str] = None
    graded: bool = False
    grade_company: Optional[str] = None
    grade_value: Optional[float] = None
    storage_location: Optional[str] = None
    notes: Optional[str] = None

class InventorySaleCreate(BaseModel):
    inventory_id: int
    sale_date: date
    sale_price: float
    sale_platform: Optional[str] = None
    fees: float = 0
    shipping_cost: float = 0
    notes: Optional[str] = None

@router.post("/inventory")
def add_to_inventory(item: InventoryCreate):
    """Add a card to inventory"""
    db = SessionLocal()
    try:
        # Verify card exists
        card = db.query(Card).filter(Card.id == item.card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        
        inventory_item = Inventory(
            card_id=item.card_id,
            purchase_date=item.purchase_date,
            purchase_price=item.purchase_price,
            purchase_source=item.purchase_source,
            quantity=item.quantity,
            condition=item.condition,
            graded=item.graded,
            grade_company=item.grade_company,
            grade_value=item.grade_value,
            storage_location=item.storage_location,
            notes=item.notes,
            status='owned'
        )
        db.add(inventory_item)
        db.commit()
        db.refresh(inventory_item)
        
        return {"id": inventory_item.id, "message": "Added to inventory"}
    finally:
        db.close()

@router.get("/inventory")
def get_inventory(
    status: Optional[str] = Query(default="owned", description="Filter by status"),
    limit: int = Query(default=50, le=200)
):
    """Get user's inventory"""
    db = SessionLocal()
    try:
        query = db.query(Inventory, Card, PriceTrend).join(Card).outerjoin(
            PriceTrend, 
            PriceTrend.card_id == Card.id
        ).filter(Inventory.status == status)
        
        # Get latest trend for each card
        subquery = db.query(
            PriceTrend.card_id,
            func.max(PriceTrend.trend_date).label('max_date')
        ).group_by(PriceTrend.card_id).subquery()
        
        query = query.filter(
            (PriceTrend.trend_date == subquery.c.max_date) | (PriceTrend.id == None)
        )
        
        results = query.order_by(desc(Inventory.purchase_date)).limit(limit).all()
        
        inventory = []
        for inv, card, trend in results:
            current_value = float(trend.avg_price) if trend else None
            purchase_price = float(inv.purchase_price)
            unrealized_profit = (current_value - purchase_price) if current_value else None
            roi = ((unrealized_profit / purchase_price) * 100) if unrealized_profit else None
            
            inventory.append({
                "id": inv.id,
                "card": {
                    "id": card.id,
                    "player_name": card.player_name,
                    "card_year": card.card_year,
                    "card_set": card.card_set,
                    "is_rookie": card.is_rookie
                },
                "purchase_date": inv.purchase_date.isoformat(),
                "purchase_price": purchase_price,
                "purchase_source": inv.purchase_source,
                "quantity": inv.quantity,
                "condition": inv.condition,
                "graded": inv.graded,
                "grade_company": inv.grade_company,
                "grade_value": float(inv.grade_value) if inv.grade_value else None,
                "storage_location": inv.storage_location,
                "status": inv.status,
                "current_value": current_value,
                "unrealized_profit": round(unrealized_profit, 2) if unrealized_profit else None,
                "roi_percentage": round(roi, 2) if roi else None
            })
        
        return {"count": len(inventory), "inventory": inventory}
    finally:
        db.close()

@router.post("/inventory/sales")
def record_sale(sale: InventorySaleCreate):
    """Record a sale from inventory"""
    db = SessionLocal()
    try:
        inventory_item = db.query(Inventory).filter(Inventory.id == sale.inventory_id).first()
        if not inventory_item:
            raise HTTPException(status_code=404, detail="Inventory item not found")
        
        # Calculate profit
        net_profit = sale.sale_price - sale.fees - sale.shipping_cost - float(inventory_item.purchase_price)
        roi = (net_profit / float(inventory_item.purchase_price)) * 100
        
        inventory_sale = InventorySale(
            inventory_id=sale.inventory_id,
            sale_date=sale.sale_date,
            sale_price=sale.sale_price,
            sale_platform=sale.sale_platform,
            fees=sale.fees,
            shipping_cost=sale.shipping_cost,
            net_profit=net_profit,
            roi_percentage=roi,
            notes=sale.notes
        )
        db.add(inventory_sale)
        
        # Update inventory status
        inventory_item.status = 'sold'
        
        db.commit()
        db.refresh(inventory_sale)
        
        return {
            "id": inventory_sale.id,
            "net_profit": round(float(net_profit), 2),
            "roi_percentage": round(float(roi), 2),
            "message": "Sale recorded"
        }
    finally:
        db.close()

@router.get("/inventory/stats")
def get_inventory_stats():
    """Get portfolio statistics"""
    db = SessionLocal()
    try:
        # Total invested
        total_invested = db.query(func.sum(Inventory.purchase_price * Inventory.quantity)).filter(
            Inventory.status == 'owned'
        ).scalar() or 0
        
        # Total cards owned
        total_cards = db.query(func.sum(Inventory.quantity)).filter(
            Inventory.status == 'owned'
        ).scalar() or 0
        
        # Realized profits from sales
        realized_profit = db.query(func.sum(InventorySale.net_profit)).scalar() or 0
        
        # Get current values for unrealized profit
        owned_items = db.query(Inventory, PriceTrend).join(
            Card, Inventory.card_id == Card.id
        ).outerjoin(
            PriceTrend, PriceTrend.card_id == Card.id
        ).filter(Inventory.status == 'owned').all()
        
        current_value = 0
        for inv, trend in owned_items:
            if trend:
                current_value += float(trend.avg_price) * inv.quantity
        
        unrealized_profit = current_value - float(total_invested)
        total_profit = float(realized_profit) + unrealized_profit
        
        return {
            "total_invested": round(float(total_invested), 2),
            "current_value": round(current_value, 2),
            "total_cards": int(total_cards),
            "realized_profit": round(float(realized_profit), 2),
            "unrealized_profit": round(unrealized_profit, 2),
            "total_profit": round(total_profit, 2),
            "roi_percentage": round((total_profit / float(total_invested) * 100), 2) if total_invested > 0 else 0
        }
    finally:
        db.close()

@router.get("/inventory/{inventory_id}")
def get_inventory_item(inventory_id: int):
    """Get detailed inventory item with sales history"""
    db = SessionLocal()
    try:
        item = db.query(Inventory, Card).join(Card).filter(Inventory.id == inventory_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Inventory item not found")
        
        inv, card = item
        
        # Get sales history
        sales = db.query(InventorySale).filter(InventorySale.inventory_id == inventory_id).all()
        
        return {
            "id": inv.id,
            "card": {
                "id": card.id,
                "player_name": card.player_name,
                "card_year": card.card_year,
                "card_set": card.card_set,
                "is_rookie": card.is_rookie
            },
            "purchase_date": inv.purchase_date.isoformat(),
            "purchase_price": float(inv.purchase_price),
            "purchase_source": inv.purchase_source,
            "quantity": inv.quantity,
            "condition": inv.condition,
            "graded": inv.graded,
            "grade_company": inv.grade_company,
            "grade_value": float(inv.grade_value) if inv.grade_value else None,
            "storage_location": inv.storage_location,
            "notes": inv.notes,
            "status": inv.status,
            "sales_history": [
                {
                    "sale_date": sale.sale_date.isoformat(),
                    "sale_price": float(sale.sale_price),
                    "sale_platform": sale.sale_platform,
                    "fees": float(sale.fees),
                    "shipping_cost": float(sale.shipping_cost),
                    "net_profit": float(sale.net_profit),
                    "roi_percentage": float(sale.roi_percentage)
                }
                for sale in sales
            ]
        }
    finally:
        db.close()
