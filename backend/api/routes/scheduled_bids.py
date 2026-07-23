"""
Scheduled Bids (Snipe Queue) endpoints
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from backend.utils.database import get_db
from backend.utils.auth import require_auth, require_operator
from backend.models import ScheduledBid

router = APIRouter(dependencies=[Depends(require_operator)])


class ScheduleBidRequest(BaseModel):
    player_name: str
    card_year: Optional[int] = None
    card_set: Optional[str] = None
    card_number: Optional[str] = None
    parallel: Optional[str] = None
    max_bid: float
    snipe_seconds: int = 10
    ebay_item_id: Optional[str] = None
    ebay_url: Optional[str] = None
    image_url: Optional[str] = None
    scp_price: Optional[float] = None
    end_time: Optional[str] = None
    notes: Optional[str] = None


@router.post("/scheduled-bids")
def create_scheduled_bid(req: ScheduleBidRequest, db: Session = Depends(get_db)):
    end_dt = None
    if req.end_time:
        try:
            end_dt = datetime.fromisoformat(req.end_time.replace('Z', '+00:00')).replace(tzinfo=None)
        except Exception:
            pass

    bid = ScheduledBid(
        player_name=req.player_name,
        card_year=req.card_year,
        card_set=req.card_set,
        card_number=req.card_number,
        parallel=req.parallel,
        max_bid=req.max_bid,
        snipe_seconds=req.snipe_seconds,
        ebay_item_id=req.ebay_item_id,
        ebay_url=req.ebay_url,
        image_url=req.image_url,
        scp_price=req.scp_price,
        end_time=end_dt,
        notes=req.notes,
    )
    db.add(bid)
    db.commit()
    db.refresh(bid)
    return {"success": True, "id": bid.id}


@router.get("/scheduled-bids")
def get_scheduled_bids(
    status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    query = db.query(ScheduledBid).order_by(ScheduledBid.end_time.asc())
    if status:
        query = query.filter(ScheduledBid.status == status)
    else:
        query = query.filter(ScheduledBid.status.in_(['scheduled', 'ready']))

    bids = query.all()
    return {
        "success": True,
        "count": len(bids),
        "bids": [_bid_to_dict(b) for b in bids],
    }


@router.delete("/scheduled-bids/{bid_id}")
def cancel_scheduled_bid(bid_id: int, db: Session = Depends(get_db)):
    bid = db.query(ScheduledBid).get(bid_id)
    if not bid:
        return {"success": False, "error": "Not found"}
    bid.status = 'cancelled'
    db.commit()
    return {"success": True}


def _bid_to_dict(b: ScheduledBid) -> dict:
    hours_left = 0
    if b.end_time:
        delta = b.end_time - datetime.now()
        hours_left = max(0, round(delta.total_seconds() / 3600, 1))

    return {
        "id": b.id,
        "player_name": b.player_name,
        "card_year": b.card_year,
        "card_set": b.card_set,
        "card_number": b.card_number,
        "parallel": b.parallel,
        "max_bid": float(b.max_bid),
        "snipe_seconds": b.snipe_seconds,
        "ebay_item_id": b.ebay_item_id,
        "ebay_url": b.ebay_url,
        "image_url": b.image_url,
        "scp_price": float(b.scp_price) if b.scp_price else None,
        "end_time": b.end_time.isoformat() if b.end_time else None,
        "hours_left": hours_left,
        "status": b.status,
        "notes": b.notes,
        "created_at": b.created_at.isoformat() if b.created_at else None,
    }
