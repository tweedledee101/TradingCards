"""
Opportunities endpoints - serves pipeline results from the database
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from typing import Optional
from backend.utils.database import get_db
from backend.models import Opportunity, JobRun

router = APIRouter()


@router.get("/opportunities")
def get_opportunities(
    min_budget: Optional[float] = Query(default=None),
    max_budget: Optional[float] = Query(default=None),
    min_profit: Optional[float] = Query(default=None),
    min_roi: Optional[float] = Query(default=None),
    listing_type: Optional[str] = Query(default=None),
    hide_flagged: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Returns stored opportunities from the latest pipeline scan.
    Defaults to BIN-only. Pass listing_type=auction or listing_type=all to change."""
    query = db.query(Opportunity)

    # Default to BIN-only so auctions don't duplicate with /api/auctions
    if listing_type == 'all':
        pass
    elif listing_type:
        query = query.filter(Opportunity.listing_type == listing_type)
    else:
        query = query.filter(
            (Opportunity.listing_type == 'buy_it_now') | (Opportunity.listing_type.is_(None))
        )

    if min_budget:
        query = query.filter(Opportunity.buy_price >= min_budget)
    if max_budget:
        query = query.filter(Opportunity.buy_price <= max_budget)
    if min_profit:
        query = query.filter(Opportunity.profit >= min_profit)
    if min_roi:
        query = query.filter(Opportunity.roi >= min_roi)
    if hide_flagged:
        query = query.filter(Opportunity.flagged == False)

    opps = query.order_by(Opportunity.profit.desc()).limit(limit).all()

    # Get scan metadata
    scan_time = None
    if opps and opps[0].scan_id:
        job = db.query(JobRun).get(opps[0].scan_id)
        if job:
            scan_time = job.completed_at.isoformat() if job.completed_at else None

    return {
        "success": True,
        "scanned_at": scan_time,
        "count": len(opps),
        "opportunities": [_opp_to_dict(o) for o in opps]
    }


@router.get("/opportunities-stats")
def get_opportunity_stats(db: Session = Depends(get_db)):
    """Quick stats from stored opportunities."""
    total = db.query(sqlfunc.count(Opportunity.id)).scalar() or 0
    if total == 0:
        return {"total_opportunities": 0, "avg_roi": 0, "avg_profit": 0, "flagged_count": 0}

    avg_roi = float(db.query(sqlfunc.avg(Opportunity.roi)).scalar() or 0)
    avg_profit = float(db.query(sqlfunc.avg(Opportunity.profit)).scalar() or 0)
    flagged = db.query(sqlfunc.count(Opportunity.id)).filter(Opportunity.flagged == True).scalar() or 0

    return {
        "total_opportunities": total,
        "avg_roi": round(avg_roi, 1),
        "avg_profit": round(avg_profit, 2),
        "flagged_count": flagged
    }


@router.get("/auctions")
def get_auctions(
    min_profit: Optional[float] = Query(default=None),
    max_budget: Optional[float] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Returns auction opportunities from the latest pipeline scan."""
    query = db.query(Opportunity).filter(Opportunity.listing_type == 'auction')
    if min_profit:
        query = query.filter(Opportunity.profit >= min_profit)
    if max_budget:
        query = query.filter(Opportunity.buy_price <= max_budget)
    opps = query.order_by(Opportunity.profit.desc()).limit(limit).all()
    return {"success": True, "count": len(opps), "auctions": [_auction_to_dict(o) for o in opps]}


def _auction_to_dict(o: Opportunity) -> dict:
    """Map DB row to the shape the frontend AuctionCard expects."""
    fees = float(o.scp_price) * 0.13
    net_profit = float(o.scp_price) - float(o.buy_price) - fees
    roi = (net_profit / float(o.buy_price) * 100) if float(o.buy_price) > 0 else 0
    return {
        "player_name": o.player_name,
        "card_year": o.card_year,
        "card_set": o.card_set,
        "card_number": o.card_number,
        "parallel": o.parallel,
        "is_rookie": False,
        "flagged": o.flagged,
        "listing_type": "auction",
        "image_url": o.image_url,
        "scp_url": o.scp_url,
        "title": o.ebay_title,
        "ebay_url": o.ebay_url,
        "ebay_item_id": o.ebay_item_id,
        "current_bid": float(o.buy_price),
        "bid_count": 0,
        "hours_left": 0,
        "shipping": 0,
        "total_cost": float(o.buy_price),
        "fees": round(fees, 2),
        "condition": "Unknown",
        "scp_sell_price": float(o.scp_price),
        "scp_price_tier": "Ungraded",
        "scp_ungraded": float(o.scp_price),
        "scp_grade_9": float(o.scp_grade_9) if o.scp_grade_9 else None,
        "scp_psa_10": float(o.scp_psa_10) if o.scp_psa_10 else None,
        "net_profit": round(net_profit, 2),
        "roi": round(roi, 1),
    }


def _opp_to_dict(o: Opportunity) -> dict:
    """Map DB row to the shape the frontend BinCard expects."""
    fees = float(o.buy_price) * 0.13
    return {
        "player_name": o.player_name,
        "card_year": o.card_year,
        "card_set": o.card_set,
        "card_number": o.card_number,
        "parallel": o.parallel,
        "is_rookie": False,
        "flagged": o.flagged,
        "listing_type": o.listing_type or 'buy_it_now',
        "scp_title": o.scp_title,
        "image_url": o.image_url,
        "scp_url": o.scp_url,
        "arbitrage": {
            "buy_price": float(o.buy_price),
            "sell_price": float(o.scp_price),
            "fees": round(fees, 2),
            "net_profit": float(o.profit),
            "roi": float(o.roi),
            "scp_ungraded": float(o.scp_price),
            "scp_grade_9": float(o.scp_grade_9) if o.scp_grade_9 else None,
            "scp_psa_10": float(o.scp_psa_10) if o.scp_psa_10 else None,
        },
        "buy_listings": [{
            "title": o.ebay_title,
            "price": float(o.buy_price),
            "net_profit": float(o.profit),
            "url": o.ebay_url
        }]
    }
