"""
Inventory management endpoints
"""
import csv
import io
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, Depends, File, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, func
from backend.utils.auth import require_auth
from backend.utils.database import SessionLocal
from backend.models import Inventory, InventorySale, Card, PriceTrend, User

router = APIRouter(dependencies=[Depends(require_auth)])

MAX_CSV_ROWS = 500


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
    status: Optional[str] = Field(default=None, description="owned | listed | sold (default owned; listed if eBay fields set)")
    ebay_item_id: Optional[str] = None
    ebay_listing_url: Optional[str] = None
    listing_ask_price: Optional[float] = None
    listed_at: Optional[date] = None


class InventoryListingPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ebay_item_id: Optional[str] = None
    ebay_listing_url: Optional[str] = None
    listing_ask_price: Optional[float] = None
    listed_at: Optional[date] = None
    status: Optional[str] = None


class InventorySaleCreate(BaseModel):
    inventory_id: int
    sale_date: date
    sale_price: float
    sale_platform: Optional[str] = None
    fees: float = 0
    shipping_cost: float = 0
    notes: Optional[str] = None


def _resolve_card_id_from_row(db, row: dict) -> Optional[int]:
    """Match CSV row to cards.id via card_id or player/year/set/#."""
    raw_id = row.get("card_id") or row.get("Card ID") or row.get("card id")
    if raw_id is not None and str(raw_id).strip().isdigit():
        c = db.query(Card).filter(Card.id == int(str(raw_id).strip())).first()
        return c.id if c else None

    pn = row.get("player_name") or row.get("Player Name") or row.get("player") or ""
    pn = str(pn).strip()
    if not pn:
        return None

    cy_raw = row.get("card_year") or row.get("Year") or row.get("year")
    if cy_raw is None or str(cy_raw).strip() == "":
        return None
    try:
        cy_int = int(float(str(cy_raw).strip()))
    except ValueError:
        return None

    cs = str(row.get("card_set") or row.get("Set") or "").strip()
    cn = str(row.get("card_number") or row.get("Card Number") or row.get("card number") or "").strip()

    q = db.query(Card).filter(
        func.lower(Card.player_name) == pn.lower(),
        Card.card_year == cy_int,
    )
    if cn:
        q = q.filter(func.lower(Card.card_number) == cn.lower())
    if cs:
        q = q.filter(Card.card_set.ilike(f"%{cs}%"))
    c = q.first()
    return c.id if c else None


def _normalize_inv_status(raw: Optional[str], has_ebay: bool) -> str:
    st = (raw or "").strip().lower()
    if st in ("owned", "listed", "sold"):
        return st
    if has_ebay:
        return "listed"
    return "owned"


@router.post("/inventory")
def add_to_inventory(item: InventoryCreate, user: User = Depends(require_auth)):
    """Add a card to inventory"""
    db = SessionLocal()
    try:
        card = db.query(Card).filter(Card.id == item.card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")

        has_ebay = bool((item.ebay_item_id or "").strip() or (item.ebay_listing_url or "").strip())
        st = _normalize_inv_status(item.status, has_ebay)

        inventory_item = Inventory(
            account_id=user.account_id,
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
            status=st,
            ebay_item_id=(item.ebay_item_id or "").strip() or None,
            ebay_listing_url=(item.ebay_listing_url or "").strip() or None,
            listing_ask_price=item.listing_ask_price,
            listed_at=item.listed_at,
        )
        db.add(inventory_item)
        db.commit()
        db.refresh(inventory_item)

        return {"id": inventory_item.id, "message": "Added to inventory"}
    finally:
        db.close()


@router.patch("/inventory/{inventory_id}")
def patch_inventory_item(
    inventory_id: int,
    body: InventoryListingPatch,
    user: User = Depends(require_auth),
):
    """Update eBay listing fields and/or status (e.g. after listing desk inventory)."""
    db = SessionLocal()
    try:
        inv = db.query(Inventory).filter(
            Inventory.id == inventory_id,
            Inventory.account_id == user.account_id,
        ).first()
        if not inv:
            raise HTTPException(status_code=404, detail="Inventory item not found")

        data = body.model_dump(exclude_unset=True)
        if "status" in data and data["status"] is not None:
            st = str(data["status"]).strip().lower()
            if st not in ("owned", "listed", "sold"):
                raise HTTPException(status_code=400, detail="status must be owned, listed, or sold")
            inv.status = st
        if "ebay_item_id" in data:
            v = data["ebay_item_id"]
            inv.ebay_item_id = (v or "").strip() or None
        if "ebay_listing_url" in data:
            v = data["ebay_listing_url"]
            inv.ebay_listing_url = (v or "").strip() or None
        if "listing_ask_price" in data:
            inv.listing_ask_price = data["listing_ask_price"]
        if "listed_at" in data:
            inv.listed_at = data["listed_at"]

        db.commit()
        db.refresh(inv)
        return {"id": inv.id, "message": "Updated"}
    finally:
        db.close()


@router.post("/inventory/bulk-import")
async def bulk_import_inventory(
    file: UploadFile = File(...),
    user: User = Depends(require_auth),
):
    """
    CSV import for owned inventory. Headers (flexible casing):

    Required: purchase_date, purchase_price
    Identity: card_id **or** player_name + card_year [+ card_set + card_number]

    Optional: quantity, condition, notes, status (owned|listed), purchase_source,
    ebay_item_id, ebay_listing_url, listing_ask_price, listed_at (YYYY-MM-DD)
    """
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 CSV")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV has no header row")

    db = SessionLocal()
    created = 0
    errors: List[dict] = []

    try:
        for i, raw_row in enumerate(reader, start=2):
            if i - 2 >= MAX_CSV_ROWS:
                errors.append({"row": i, "error": f"Stopped at {MAX_CSV_ROWS} rows"})
                break

            merged = {}
            for k, v in raw_row.items():
                if not k:
                    continue
                key = k.strip().lower().replace(" ", "_")
                merged[key] = v.strip() if isinstance(v, str) and v is not None else v

            pdate_s = merged.get("purchase_date")
            pprice_s = merged.get("purchase_price")

            if not pdate_s or str(pdate_s).strip() == "":
                errors.append({"row": i, "error": "missing purchase_date"})
                continue
            if pprice_s is None or str(pprice_s).strip() == "":
                errors.append({"row": i, "error": "missing purchase_price"})
                continue

            try:
                pdate = date.fromisoformat(str(pdate_s).strip()[:10])
            except ValueError:
                errors.append({"row": i, "error": f"bad purchase_date: {pdate_s}"})
                continue

            try:
                pprice = float(str(pprice_s).replace("$", "").replace(",", "").strip())
            except ValueError:
                errors.append({"row": i, "error": f"bad purchase_price: {pprice_s}"})
                continue

            cid = _resolve_card_id_from_row(db, merged)
            if not cid:
                errors.append({"row": i, "error": "could not resolve card (card_id or player+year+…)"})
                continue

            qty_s = merged.get("quantity") or "1"
            try:
                qty = max(1, int(float(qty_s)))
            except ValueError:
                qty = 1

            eid = (merged.get("ebay_item_id") or merged.get("ebay_item") or "").strip() or None
            eurl = (merged.get("ebay_listing_url") or merged.get("listing_url") or "").strip() or None
            has_ebay = bool(eid or eurl)

            lap = None
            if merged.get("listing_ask_price") not in (None, ""):
                try:
                    lap = float(str(merged.get("listing_ask_price")).replace("$", "").replace(",", "").strip())
                except ValueError:
                    lap = None

            lat = None
            if merged.get("listed_at") not in (None, ""):
                try:
                    lat = date.fromisoformat(str(merged.get("listed_at")).strip()[:10])
                except ValueError:
                    lat = None

            st = _normalize_inv_status(merged.get("status"), has_ebay)

            inv = Inventory(
                account_id=user.account_id,
                card_id=cid,
                purchase_date=pdate,
                purchase_price=pprice,
                purchase_source=(merged.get("purchase_source") or merged.get("source") or None),
                quantity=qty,
                condition=merged.get("condition"),
                notes=merged.get("notes"),
                status=st,
                ebay_item_id=eid,
                ebay_listing_url=eurl,
                listing_ask_price=lap,
                listed_at=lat,
            )
            db.add(inv)
            created += 1

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

    return {"created": created, "errors": errors[:50], "error_count": len(errors)}


@router.get("/inventory")
def get_inventory(
    status: str = Query(
        default="owned",
        description="owned | listed | sold | active (owned+listed, working capital)",
    ),
    limit: int = Query(default=50, le=200),
    user: User = Depends(require_auth),
):
    """Get user's inventory"""
    db = SessionLocal()
    try:
        st = (status or "owned").strip().lower()
        if st == "active":
            status_filter = Inventory.status.in_(("owned", "listed"))
        elif st in ("owned", "listed", "sold"):
            status_filter = Inventory.status == st
        else:
            raise HTTPException(status_code=400, detail="status must be owned, listed, sold, or active")

        latest_trends = db.query(
            PriceTrend.card_id,
            func.max(PriceTrend.trend_date).label('max_date')
        ).group_by(PriceTrend.card_id).subquery()

        results = db.query(Inventory, Card, PriceTrend).select_from(Inventory).join(
            Card, Inventory.card_id == Card.id
        ).outerjoin(
            latest_trends, Card.id == latest_trends.c.card_id
        ).outerjoin(
            PriceTrend,
            (PriceTrend.card_id == Card.id) & (PriceTrend.trend_date == latest_trends.c.max_date)
        ).filter(
            status_filter,
            Inventory.account_id == user.account_id,
        ).order_by(desc(Inventory.purchase_date)).limit(limit).all()

        inventory = []
        for inv, card, trend in results:
            current_value = float(trend.avg_price) if trend and trend.avg_price else None
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
                "ebay_item_id": inv.ebay_item_id,
                "ebay_listing_url": inv.ebay_listing_url,
                "listing_ask_price": float(inv.listing_ask_price) if inv.listing_ask_price is not None else None,
                "listed_at": inv.listed_at.isoformat() if inv.listed_at else None,
                "current_value": current_value,
                "unrealized_profit": round(unrealized_profit, 2) if unrealized_profit else None,
                "roi_percentage": round(roi, 2) if roi else None
            })

        return {"count": len(inventory), "inventory": inventory}
    finally:
        db.close()


@router.post("/inventory/sales")
def record_sale(sale: InventorySaleCreate, user: User = Depends(require_auth)):
    """Record a sale from inventory"""
    db = SessionLocal()
    try:
        inventory_item = db.query(Inventory).filter(
            Inventory.id == sale.inventory_id,
            Inventory.account_id == user.account_id,
        ).first()
        if not inventory_item:
            raise HTTPException(status_code=404, detail="Inventory item not found")

        net_profit = sale.sale_price - sale.fees - sale.shipping_cost - float(inventory_item.purchase_price)
        roi = (net_profit / float(inventory_item.purchase_price)) * 100
        days_held = (sale.sale_date - inventory_item.purchase_date).days

        inventory_sale = InventorySale(
            account_id=user.account_id,
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

        inventory_item.status = 'sold'

        db.commit()
        db.refresh(inventory_sale)

        return {
            "id": inventory_sale.id,
            "net_profit": round(float(net_profit), 2),
            "roi_percentage": round(float(roi), 2),
            "days_held": days_held,
            "message": "Sale recorded",
        }
    finally:
        db.close()


@router.get("/inventory/stats")
def get_inventory_stats(user: User = Depends(require_auth)):
    """Get portfolio statistics"""
    db = SessionLocal()
    try:
        _active_inv = (
            Inventory.status.in_(("owned", "listed")),
            Inventory.account_id == user.account_id,
        )
        total_invested = db.query(func.sum(Inventory.purchase_price * Inventory.quantity)).filter(
            *_active_inv,
        ).scalar() or 0

        total_cards = db.query(func.sum(Inventory.quantity)).filter(
            *_active_inv,
        ).scalar() or 0

        realized_profit = db.query(func.sum(InventorySale.net_profit)).filter(
            InventorySale.account_id == user.account_id,
        ).scalar() or 0

        latest_trends = db.query(
            PriceTrend.card_id,
            func.max(PriceTrend.trend_date).label('max_date')
        ).group_by(PriceTrend.card_id).subquery()

        owned_items = db.query(Inventory, PriceTrend).select_from(Inventory).join(
            Card, Inventory.card_id == Card.id
        ).outerjoin(
            latest_trends, Card.id == latest_trends.c.card_id
        ).outerjoin(
            PriceTrend,
            (PriceTrend.card_id == Card.id) & (PriceTrend.trend_date == latest_trends.c.max_date)
        ).filter(
            Inventory.status.in_(("owned", "listed")),
            Inventory.account_id == user.account_id,
        ).all()

        current_value = 0
        for inv, trend in owned_items:
            if trend and trend.avg_price:
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
def get_inventory_item(inventory_id: int, user: User = Depends(require_auth)):
    """Get detailed inventory item with sales history"""
    db = SessionLocal()
    try:
        item = db.query(Inventory, Card).join(Card).filter(
            Inventory.id == inventory_id,
            Inventory.account_id == user.account_id,
        ).first()
        if not item:
            raise HTTPException(status_code=404, detail="Inventory item not found")

        inv, card = item

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
            "ebay_item_id": inv.ebay_item_id,
            "ebay_listing_url": inv.ebay_listing_url,
            "listing_ask_price": float(inv.listing_ask_price) if inv.listing_ask_price is not None else None,
            "listed_at": inv.listed_at.isoformat() if inv.listed_at else None,
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
