"""
Opportunities endpoints - serves pipeline results from the database
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc, or_
from typing import Optional
from datetime import datetime, timedelta, date
import unicodedata
from backend.utils.database import get_db
from backend.utils.auth import require_auth, require_operator
from backend.models import Opportunity, JobRun, Card, Sale, ActiveListing, MarketRate, User
from backend.services.business_planner import BusinessPlanner

router = APIRouter(dependencies=[Depends(require_operator)])


@router.get("/opportunities")
def get_opportunities(
    min_budget: Optional[float] = Query(default=None),
    max_budget: Optional[float] = Query(default=None),
    min_profit: Optional[float] = Query(default=None),
    min_roi: Optional[float] = Query(default=None),
    listing_type: Optional[str] = Query(default=None),
    sport: Optional[str] = Query(default=None, description="Baseball, Basketball, Football; omit or 'all' for any"),
    hide_flagged: bool = Query(default=False),
    hide_ce_rejected: bool = Query(default=True, description="Hide opportunities where CE verification found identity mismatch"),
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
    if hide_ce_rejected:
        ce_reject = ['ce_player_mismatch', 'ce_year_mismatch', 'ce_price_divergence', 'ce_not_profitable']
        query = query.filter(
            ~Opportunity.verification_status.in_(ce_reject)
        )
    if sport and str(sport).strip().lower() not in ("all", "", "any"):
        query = query.filter(Opportunity.sport == str(sport).strip().title())

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


@router.get("/opportunities/context-strip")
def get_opportunities_context_strip(
    db: Session = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Lightweight payload for Opportunities page: business goal pace + market listing pulse vs SCP."""
    planner = BusinessPlanner()
    dash = planner.get_dashboard(db, account_id=user.account_id)

    recent_cutoff = date.today() - timedelta(days=5)
    latest_al = (
        db.query(
            ActiveListing.ebay_item_id,
            sqlfunc.max(ActiveListing.snapshot_date).label("mx"),
        )
        .filter(ActiveListing.snapshot_date >= recent_cutoff)
        .group_by(ActiveListing.ebay_item_id)
        .subquery()
    )
    tracked = db.query(sqlfunc.count()).select_from(latest_al).scalar() or 0

    mr_sub = (
        db.query(
            MarketRate.card_id,
            sqlfunc.max(MarketRate.date_recorded).label("mxd"),
        )
        .group_by(MarketRate.card_id)
        .subquery()
    )
    rate_rows = (
        db.query(MarketRate)
        .join(
            mr_sub,
            (MarketRate.card_id == mr_sub.c.card_id)
            & (MarketRate.date_recorded == mr_sub.c.mxd),
        )
        .all()
    )
    rate_by_card = {
        r.card_id: float(r.ungraded_price)
        for r in rate_rows
        if r.ungraded_price and float(r.ungraded_price) > 0
    }

    rows = (
        db.query(ActiveListing, Card)
        .join(
            latest_al,
            (ActiveListing.ebay_item_id == latest_al.c.ebay_item_id)
            & (ActiveListing.snapshot_date == latest_al.c.mx),
        )
        .join(Card, ActiveListing.card_id == Card.id)
        .order_by(ActiveListing.listing_price.desc())
        .limit(40)
        .all()
    )

    fee = 0.13
    listing_pulse = []
    for al, card in rows:
        scp = rate_by_card.get(card.id)
        lp = float(al.listing_price)
        net_at_scp = round(scp * (1 - fee), 2) if scp else None
        est_vs_ask = round(net_at_scp - lp, 2) if net_at_scp is not None else None
        cn = card.card_number or ""
        listing_pulse.append({
            "ebay_item_id": al.ebay_item_id,
            "listing_title": (al.listing_title or "")[:140],
            "listing_url": al.listing_url,
            "listing_price": lp,
            "scp_ungraded": round(scp, 2) if scp else None,
            "est_net_if_sold_at_scp": net_at_scp,
            "est_profit_vs_current_ask": est_vs_ask,
            "player_name": card.player_name,
            "card_label": f"{card.card_year} {card.card_set} #{cn}".strip(),
        })

    return {
        "business": dash,
        "market_listings": {
            "tracked_distinct_items": int(tracked),
            "window_days": 5,
            "rows": listing_pulse,
            "note": (
                "Catalog-matched eBay asks from the latest DB snapshot (pipeline / worm), "
                "not your seller account until seller OAuth sync exists."
            ),
        },
    }


@router.get("/auctions")
def get_auctions(
    min_profit: Optional[float] = Query(default=None),
    max_budget: Optional[float] = Query(default=None),
    include_ended: bool = Query(default=False),
    hide_ce_rejected: bool = Query(default=True),
    sport: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Returns auction opportunities from the latest pipeline scan.
    By default, excludes auctions that have already ended."""
    from datetime import datetime
    query = db.query(Opportunity).filter(Opportunity.listing_type == 'auction')
    if not include_ended:
        query = query.filter(
            (Opportunity.end_time > datetime.now()) | (Opportunity.end_time.is_(None))
        )
    if min_profit:
        query = query.filter(Opportunity.profit >= min_profit)
    if max_budget:
        query = query.filter(Opportunity.buy_price <= max_budget)
    if hide_ce_rejected:
        ce_reject = ['ce_player_mismatch', 'ce_year_mismatch', 'ce_price_divergence', 'ce_not_profitable']
        query = query.filter(
            ~Opportunity.verification_status.in_(ce_reject)
        )
    if sport and str(sport).strip().lower() not in ("all", "", "any"):
        query = query.filter(Opportunity.sport == str(sport).strip().title())
    opps = query.order_by(Opportunity.profit.desc()).limit(limit).all()

    ended_fallback = False

    return {
        "success": True,
        "count": len(opps),
        "auctions": [_auction_to_dict(o) for o in opps],
        "ended_fallback": ended_fallback,
    }


@router.get("/players/{player_name}/stats")
def get_player_stats(player_name: str, db: Session = Depends(get_db)):
    """Player-level analytics for the opportunity drill-in modal."""
    name_lower = player_name.lower()
    # Strip accents: Acuña -> Acuna, so we match both DB spellings
    name_normalized = unicodedata.normalize('NFD', name_lower)
    name_ascii = ''.join(c for c in name_normalized if unicodedata.category(c) != 'Mn')
    # Also strip trailing periods: "Jr." -> "Jr"
    name_ascii = name_ascii.rstrip('.')

    thirty_days_ago = datetime.now() - timedelta(days=30)

    # Match cards by either exact or accent-stripped name
    card_filter = or_(
        sqlfunc.lower(Card.player_name) == name_lower,
        sqlfunc.lower(Card.player_name) == name_ascii,
        sqlfunc.lower(Card.player_name) == name_ascii.rstrip(' jr').rstrip(' ') + ' jr',
    )

    card_count = db.query(sqlfunc.count(Card.id)).filter(card_filter).scalar() or 0

    card_ids = db.query(Card.id).filter(card_filter).subquery()
    total_sales = db.query(sqlfunc.count(Sale.id)).filter(Sale.card_id.in_(card_ids)).scalar() or 0
    recent_sales = db.query(sqlfunc.count(Sale.id)).filter(
        Sale.card_id.in_(card_ids), Sale.sale_date >= thirty_days_ago
    ).scalar() or 0
    avg_sale = db.query(sqlfunc.avg(Sale.sale_price)).filter(
        Sale.card_id.in_(card_ids), Sale.sale_date >= thirty_days_ago
    ).scalar()

    active_count = db.query(sqlfunc.count(ActiveListing.id)).filter(
        ActiveListing.card_id.in_(card_ids)
    ).scalar() or 0

    velocity = round(recent_sales / active_count, 2) if active_count > 0 else 0

    rates_count = db.query(sqlfunc.count(MarketRate.id)).filter(
        MarketRate.card_id.in_(card_ids)
    ).scalar() or 0

    opp_count = db.query(sqlfunc.count(Opportunity.id)).filter(
        sqlfunc.lower(Opportunity.player_name) == name_lower
    ).scalar() or 0

    # Sell-through data: sales grouped by price bucket relative to SCP
    # For cards with market rates, compute how fast they sell at various price points
    sell_through = []
    rated_cards = db.query(Card.id, MarketRate.ungraded_price).join(
        MarketRate, Card.id == MarketRate.card_id
    ).filter(card_filter, MarketRate.ungraded_price > 0).all()

    if rated_cards:
        rate_map = {c_id: float(price) for c_id, price in rated_cards}
        rated_ids = list(rate_map.keys())

        sales_with_rate = db.query(Sale.card_id, Sale.sale_price, Sale.sale_date).filter(
            Sale.card_id.in_(rated_ids),
            Sale.sale_date >= datetime.now() - timedelta(days=90),
        ).all()

        # Bucket sales by % of SCP: <80%, 80-90%, 90-100%, 100-110%, >110%
        buckets = {
            'below_80': {'sales': 0, 'total_days': 0, 'label': '<80% of SCP'},
            '80_to_90': {'sales': 0, 'total_days': 0, 'label': '80-90%'},
            '90_to_100': {'sales': 0, 'total_days': 0, 'label': '90-100%'},
            'at_market': {'sales': 0, 'total_days': 0, 'label': '100-110%'},
            'above_110': {'sales': 0, 'total_days': 0, 'label': '>110%'},
        }

        for sale in sales_with_rate:
            scp = rate_map.get(sale.card_id, 0)
            if scp <= 0:
                continue
            ratio = float(sale.sale_price) / scp
            if ratio < 0.80:
                buckets['below_80']['sales'] += 1
            elif ratio < 0.90:
                buckets['80_to_90']['sales'] += 1
            elif ratio < 1.00:
                buckets['90_to_100']['sales'] += 1
            elif ratio < 1.10:
                buckets['at_market']['sales'] += 1
            else:
                buckets['above_110']['sales'] += 1

        total_rated_sales = sum(b['sales'] for b in buckets.values())
        days_in_window = 90

        for key, bucket in buckets.items():
            if bucket['sales'] > 0:
                # avg days between sales at this price point
                avg_days_to_sell = round(days_in_window / bucket['sales'], 1)
            else:
                avg_days_to_sell = None
            sell_through.append({
                'bucket': bucket['label'],
                'sales': bucket['sales'],
                'pct_of_total': round(bucket['sales'] / total_rated_sales * 100, 1) if total_rated_sales > 0 else 0,
                'avg_days_to_sell': avg_days_to_sell,
            })

    return {
        "player_name": player_name,
        "cards": card_count,
        "total_sales": total_sales,
        "recent_sales_30d": recent_sales,
        "avg_sale_price_30d": round(float(avg_sale), 2) if avg_sale else None,
        "active_listings": active_count,
        "velocity": velocity,
        "market_rates": rates_count,
        "opportunities": opp_count,
        "sell_through": sell_through,
    }


@router.get("/players/{player_name}/price-history")
def get_player_price_history(player_name: str, days: int = Query(default=90), db: Session = Depends(get_db)):
    """Daily avg sale price for sparkline chart."""
    name_lower = player_name.lower()
    name_normalized = unicodedata.normalize('NFD', name_lower)
    name_ascii = ''.join(c for c in name_normalized if unicodedata.category(c) != 'Mn').rstrip('.')

    card_filter = or_(
        sqlfunc.lower(Card.player_name) == name_lower,
        sqlfunc.lower(Card.player_name) == name_ascii,
        sqlfunc.lower(Card.player_name) == name_ascii.rstrip(' jr').rstrip(' ') + ' jr',
    )
    card_ids = db.query(Card.id).filter(card_filter).subquery()
    cutoff = datetime.now() - timedelta(days=days)

    rows = db.query(
        sqlfunc.cast(Sale.sale_date, sqlfunc.DATE).label('day'),
        sqlfunc.count(Sale.id).label('sales'),
        sqlfunc.avg(Sale.sale_price).label('avg_price'),
        sqlfunc.min(Sale.sale_price).label('min_price'),
        sqlfunc.max(Sale.sale_price).label('max_price'),
    ).filter(
        Sale.card_id.in_(card_ids),
        Sale.sale_date >= cutoff,
    ).group_by('day').order_by('day').all()

    # Get SCP avg for reference line
    avg_scp = db.query(sqlfunc.avg(MarketRate.ungraded_price)).filter(
        MarketRate.card_id.in_(card_ids),
        MarketRate.ungraded_price > 0,
    ).scalar()

    return {
        "player_name": player_name,
        "days": days,
        "scp_avg": round(float(avg_scp), 2) if avg_scp else None,
        "history": [{
            "date": row.day.isoformat(),
            "sales": row.sales,
            "avg_price": round(float(row.avg_price), 2),
            "min_price": round(float(row.min_price), 2),
            "max_price": round(float(row.max_price), 2),
        } for row in rows]
    }


@router.get("/players/{player_name}/timing")
def get_player_timing(player_name: str, db: Session = Depends(get_db)):
    """Day-of-week and hour-of-day sale patterns for timing analysis."""
    name_lower = player_name.lower()
    name_normalized = unicodedata.normalize('NFD', name_lower)
    name_ascii = ''.join(c for c in name_normalized if unicodedata.category(c) != 'Mn').rstrip('.')

    card_filter = or_(
        sqlfunc.lower(Card.player_name) == name_lower,
        sqlfunc.lower(Card.player_name) == name_ascii,
        sqlfunc.lower(Card.player_name) == name_ascii.rstrip(' jr').rstrip(' ') + ' jr',
    )
    card_ids = db.query(Card.id).filter(card_filter).subquery()
    cutoff = datetime.now() - timedelta(days=90)

    # Day of week: 0=Sun, 6=Sat
    dow_rows = db.query(
        sqlfunc.extract('dow', Sale.sale_date).label('dow'),
        sqlfunc.count(Sale.id).label('sales'),
        sqlfunc.avg(Sale.sale_price).label('avg_price'),
    ).filter(
        Sale.card_id.in_(card_ids),
        Sale.sale_date >= cutoff,
    ).group_by('dow').order_by('dow').all()

    day_names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

    # Hour of day
    hour_rows = db.query(
        sqlfunc.extract('hour', Sale.sale_date).label('hour'),
        sqlfunc.count(Sale.id).label('sales'),
        sqlfunc.avg(Sale.sale_price).label('avg_price'),
    ).filter(
        Sale.card_id.in_(card_ids),
        Sale.sale_date >= cutoff,
    ).group_by('hour').order_by('hour').all()

    return {
        "player_name": player_name,
        "by_day": [{
            "day": day_names[int(r.dow)],
            "dow": int(r.dow),
            "sales": r.sales,
            "avg_price": round(float(r.avg_price), 2),
        } for r in dow_rows],
        "by_hour": [{
            "hour": int(r.hour),
            "sales": r.sales,
            "avg_price": round(float(r.avg_price), 2),
        } for r in hour_rows],
    }


def _auction_to_dict(o: Opportunity) -> dict:
    """Map DB row to the shape the frontend AuctionCard expects."""
    shipping = float(o.shipping) if o.shipping else 0
    total_cost = float(o.buy_price) + shipping
    fees = float(o.scp_price) * 0.13
    net_profit = float(o.scp_price) - total_cost - fees
    roi = (net_profit / total_cost * 100) if total_cost > 0 else 0

    hours_left = 0
    if o.end_time:
        from datetime import datetime
        delta = o.end_time - datetime.now()
        hours_left = max(0, round(delta.total_seconds() / 3600, 1))

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
        "listing_image_urls": o.listing_image_urls if o.listing_image_urls else None,
        "scp_url": o.scp_url,
        "title": o.ebay_title,
        "ebay_url": o.ebay_url,
        "ebay_item_id": o.ebay_item_id,
        "current_bid": float(o.buy_price),
        "bid_count": o.bid_count or 0,
        "hours_left": hours_left,
        "end_time": o.end_time.isoformat() if o.end_time else None,
        "shipping": shipping,
        "total_cost": round(total_cost, 2),
        "fees": round(fees, 2),
        "condition": "Unknown",
        "scp_sell_price": float(o.scp_price),
        "scp_price_tier": "Ungraded",
        "scp_ungraded": float(o.scp_price),
        "scp_grade_9": float(o.scp_grade_9) if o.scp_grade_9 else None,
        "scp_psa_10": float(o.scp_psa_10) if o.scp_psa_10 else None,
        "scp_volume": o.scp_volume,
        "net_profit": round(net_profit, 2),
        "roi": round(roi, 1),
        "price_source": o.price_source or 'scp',
        "qa_status": o.qa_status or 'pending',
        "qa_flags": o.qa_flags or [],
        "verification_status": (o.verification_status or "pending"),
        "verification_detail": o.verification_detail,
        "sport": getattr(o, "sport", None) or "Baseball",
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
        "listing_image_urls": o.listing_image_urls if o.listing_image_urls else None,
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
        }],
        "price_source": o.price_source or 'scp',
        "qa_status": o.qa_status or 'pending',
        "qa_flags": o.qa_flags or [],
        "verification_status": (o.verification_status or "pending"),
        "verification_detail": o.verification_detail,
        "sport": getattr(o, "sport", None) or "Baseball",
    }
