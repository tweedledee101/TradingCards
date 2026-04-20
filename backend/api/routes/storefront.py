"""
Public Storefront API - no authentication required.

Serves listed inventory cards to the public. This is the dealer's
public-facing card shop at ragnarokgamez.com/shop.

No auth on these endpoints -- anyone can browse the shop.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from typing import Optional

from backend.utils.database import get_db
from backend.models import Inventory, Card

router = APIRouter()


@router.get("/shop/cards")
def get_shop_cards(
    sport: Optional[str] = Query(default=None),
    player: Optional[str] = Query(default=None),
    min_price: Optional[float] = Query(default=None),
    max_price: Optional[float] = Query(default=None),
    year: Optional[int] = Query(default=None),
    search: Optional[str] = Query(default=None),
    sort: str = Query(default="newest", description="newest, price_asc, price_desc, player"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Public endpoint: browse cards for sale. No auth required."""
    query = (
        db.query(Inventory, Card)
        .join(Card, Inventory.card_id == Card.id)
        .filter(Inventory.status == 'listed')
        .filter(Inventory.listing_ask_price.isnot(None))
        .filter(Inventory.listing_ask_price > 0)
    )

    if sport:
        query = query.filter(Card.sport == sport.strip().title())
    if player:
        query = query.filter(Card.player_name.ilike(f'%{player.strip()}%'))
    if min_price:
        query = query.filter(Inventory.listing_ask_price >= min_price)
    if max_price:
        query = query.filter(Inventory.listing_ask_price <= max_price)
    if year:
        query = query.filter(Card.card_year == year)
    if search:
        term = f'%{search.strip()}%'
        query = query.filter(
            Card.player_name.ilike(term)
            | Card.card_set.ilike(term)
            | Card.parallel.ilike(term)
        )

    # Sorting
    if sort == 'price_asc':
        query = query.order_by(Inventory.listing_ask_price.asc())
    elif sort == 'price_desc':
        query = query.order_by(Inventory.listing_ask_price.desc())
    elif sort == 'player':
        query = query.order_by(Card.player_name.asc(), Inventory.listing_ask_price.asc())
    else:  # newest
        query = query.order_by(Inventory.listed_at.desc().nullslast(), Inventory.created_at.desc())

    total = query.count()
    items = query.offset(offset).limit(limit).all()

    return {
        'total': total,
        'offset': offset,
        'limit': limit,
        'cards': [_shop_card_to_dict(inv, card) for inv, card in items],
    }


@router.get("/shop/cards/{inventory_id}")
def get_shop_card_detail(
    inventory_id: int,
    db: Session = Depends(get_db),
):
    """Public endpoint: single card detail page."""
    result = (
        db.query(Inventory, Card)
        .join(Card, Inventory.card_id == Card.id)
        .filter(Inventory.id == inventory_id)
        .filter(Inventory.status == 'listed')
        .first()
    )
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Card not found or not listed")

    inv, card = result
    return _shop_card_to_dict(inv, card, full=True)


@router.get("/shop/stats")
def get_shop_stats(db: Session = Depends(get_db)):
    """Public endpoint: shop overview stats."""
    listed = (
        db.query(sqlfunc.count(Inventory.id))
        .filter(Inventory.status == 'listed')
        .filter(Inventory.listing_ask_price.isnot(None))
        .scalar() or 0
    )
    total_value = (
        db.query(sqlfunc.sum(Inventory.listing_ask_price))
        .filter(Inventory.status == 'listed')
        .filter(Inventory.listing_ask_price.isnot(None))
        .scalar() or 0
    )
    sports = (
        db.query(Card.sport, sqlfunc.count(Inventory.id))
        .join(Card, Inventory.card_id == Card.id)
        .filter(Inventory.status == 'listed')
        .group_by(Card.sport)
        .all()
    )
    players = (
        db.query(Card.player_name, sqlfunc.count(Inventory.id))
        .join(Card, Inventory.card_id == Card.id)
        .filter(Inventory.status == 'listed')
        .group_by(Card.player_name)
        .order_by(sqlfunc.count(Inventory.id).desc())
        .limit(10)
        .all()
    )

    return {
        'cards_listed': listed,
        'total_ask_value': round(float(total_value), 2),
        'by_sport': {s: c for s, c in sports if s},
        'top_players': [{'name': p, 'count': c} for p, c in players],
    }


def _shop_card_to_dict(inv: Inventory, card: Card, full: bool = False) -> dict:
    """Convert inventory + card to public shop listing dict."""
    d = {
        'id': inv.id,
        'player_name': card.player_name,
        'card_year': card.card_year,
        'card_set': card.card_set,
        'card_number': card.card_number,
        'parallel': card.parallel,
        'sport': card.sport,
        'price': float(inv.listing_ask_price) if inv.listing_ask_price else None,
        'condition': inv.condition or 'Ungraded',
        'graded': inv.graded,
        'grade_company': inv.grade_company,
        'grade_value': float(inv.grade_value) if inv.grade_value else None,
        'image_url': card.image_url,
        'ebay_url': inv.ebay_listing_url,
        'listed_at': inv.listed_at.isoformat() if inv.listed_at else None,
    }
    if full:
        d['notes'] = inv.notes
        d['purchase_date'] = inv.purchase_date.isoformat() if inv.purchase_date else None
    return d
