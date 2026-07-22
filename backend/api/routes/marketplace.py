"""
Ragnarok Marketplace API - Stripe Connect + Checkout + Webhooks

Handles:
- Seller onboarding (Stripe Connect)
- Checkout session creation with $1 platform fee
- Payment webhook (mark sold, notify seller)
- Shipping: method selection, 3-day ship-by SLA, photo-verified shipment
  confirmation, buyer-facing order status
"""
import uuid
from datetime import date, timedelta, datetime

import boto3
import stripe
from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from backend.config.settings import config
from backend.utils.database import get_db
from backend.utils.auth import require_auth
from backend.utils.player_extractor import player_extractor
from backend.models import User, MarketplaceListing, MarketplaceOrder

stripe.api_key = config.STRIPE_SECRET_KEY
router = APIRouter()

SHIP_BY_DAYS = 3  # seller SLA: ship within 3 days of sale

# Shipping methods a seller picks per listing - covers single card vs. lots,
# not one flat fee for everything. Prices are sensible starting points and
# stay editable per listing since real postage costs shift.
SHIPPING_METHODS = {
    'single_card': {
        'label': 'Single Card (top-loader + bubble mailer)',
        'default_cents': 450,
        'estimate': '3-5 business days',
    },
    'small_lot': {
        'label': 'Small Lot (up to 10 cards, bubble mailer)',
        'default_cents': 550,
        'estimate': '3-5 business days',
    },
    'large_lot': {
        'label': 'Large Lot / Box (11+ cards)',
        'default_cents': 900,
        'estimate': '3-6 business days',
    },
}

# Carrier tracking URL patterns - we don't have live carrier status, but a
# tracking number is enough to deep-link the buyer straight to it.
CARRIER_TRACKING_URLS = {
    'USPS': 'https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking}',
    'UPS': 'https://www.ups.com/track?tracknum={tracking}',
    'FedEx': 'https://www.fedex.com/fedextrack/?trknbr={tracking}',
}


@router.get("/marketplace/shipping-methods")
def get_shipping_methods():
    """Public: shipping method catalog, so the listing form isn't guessing at prices alone."""
    return {"methods": [{"code": k, **v} for k, v in SHIPPING_METHODS.items()]}


# --- Listings CRUD ---

class ListingCreate(BaseModel):
    title: str
    description: Optional[str] = None
    price_cents: int
    category: str
    condition: Optional[str] = None
    shipping_cents: int = 0
    shipping_method: str = 'single_card'
    image_urls: list = []


@router.get("/marketplace/listings")
def get_listings(category: Optional[str] = None, seller_id: Optional[int] = None, limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    """Public: browse all active marketplace listings."""
    q = db.query(MarketplaceListing).filter(MarketplaceListing.status == 'active')
    if category:
        q = q.filter(MarketplaceListing.category == category)
    if seller_id:
        q = q.filter(MarketplaceListing.seller_id == seller_id)
    total = q.count()
    items = q.order_by(MarketplaceListing.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "listings": [{
            "id": l.id, "seller_id": l.seller_id, "title": l.title,
            "description": l.description, "price_cents": l.price_cents,
            "category": l.category, "condition": l.condition,
            "shipping_cents": l.shipping_cents, "shipping_method": l.shipping_method,
            "image_urls": l.image_urls or [],
            "status": l.status, "created_at": l.created_at.isoformat() if l.created_at else None,
        } for l in items]
    }


@router.get("/marketplace/listings/{listing_id}")
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    """Public: single listing detail."""
    l = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Listing not found")
    seller = db.query(User).filter(User.id == l.seller_id).first()
    match = player_extractor.extract_player(f"{l.title} {l.description or ''}")
    method = SHIPPING_METHODS.get(l.shipping_method, {})
    return {
        "id": l.id, "seller_id": l.seller_id, "title": l.title,
        "description": l.description, "price_cents": l.price_cents,
        "category": l.category, "condition": l.condition,
        "shipping_cents": l.shipping_cents, "shipping_method": l.shipping_method,
        "shipping_method_label": method.get('label'), "shipping_estimate": method.get('estimate'),
        "image_urls": l.image_urls or [],
        "status": l.status, "created_at": l.created_at.isoformat() if l.created_at else None,
        "seller_name": seller.display_name or seller.email if seller else "Unknown",
        "guessed_player_name": match[0] if match else None,
    }


@router.post("/marketplace/listings")
def create_listing(listing: ListingCreate, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """Seller: create a new listing. Requires authentication."""
    if not user.is_seller:
        raise HTTPException(status_code=403, detail="Not a registered seller")
    if listing.price_cents < 200:
        raise HTTPException(status_code=400, detail="Minimum price is $2.00")
    if listing.shipping_method not in SHIPPING_METHODS:
        raise HTTPException(status_code=400, detail=f"shipping_method must be one of {list(SHIPPING_METHODS)}")
    item = MarketplaceListing(
        seller_id=user.id, title=listing.title, description=listing.description,
        price_cents=listing.price_cents, category=listing.category,
        condition=listing.condition, shipping_cents=listing.shipping_cents,
        shipping_method=listing.shipping_method,
        image_urls=listing.image_urls, status='active',
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "status": "active"}


@router.delete("/marketplace/listings/{listing_id}")
def delete_listing(listing_id: int, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """Seller: remove a listing. Requires authentication."""
    l = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id, MarketplaceListing.seller_id == user.id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Listing not found")
    l.status = "removed"
    db.commit()
    return {"status": "removed"}


# --- Seller Orders ---

def _order_dict(o, db, include_listing=True):
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == o.listing_id).first() if include_listing else None
    tracking_url = None
    if o.tracking_number and o.carrier and o.carrier in CARRIER_TRACKING_URLS:
        tracking_url = CARRIER_TRACKING_URLS[o.carrier].format(tracking=o.tracking_number)
    return {
        "id": o.id, "listing_id": o.listing_id,
        "listing_title": listing.title if listing else None,
        "price_cents": o.price_cents,
        "shipping_cents": o.shipping_cents, "status": o.status,
        "shipping_address": o.shipping_address,
        "tracking_number": o.tracking_number, "carrier": o.carrier, "tracking_url": tracking_url,
        "shipment_photo_url": o.shipment_photo_url,
        "ship_by_date": o.ship_by_date.isoformat() if o.ship_by_date else None,
        "is_overdue": bool(o.ship_by_date and o.status == 'paid' and date.today() > o.ship_by_date),
        "shipped_at": o.shipped_at.isoformat() if o.shipped_at else None,
        "delivered_at": o.delivered_at.isoformat() if o.delivered_at else None,
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }


@router.get("/marketplace/orders")
def get_seller_orders(user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """Seller: view their orders. Requires authentication."""
    orders = db.query(MarketplaceOrder).filter(MarketplaceOrder.seller_id == user.id).order_by(MarketplaceOrder.created_at.desc()).all()
    return {"orders": [_order_dict(o, db) for o in orders]}


@router.get("/marketplace/my-orders")
def get_my_orders(user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """Buyer: view their own purchases and shipment status. Requires authentication."""
    orders = db.query(MarketplaceOrder).filter(MarketplaceOrder.buyer_id == user.id).order_by(MarketplaceOrder.created_at.desc()).all()
    return {"orders": [_order_dict(o, db) for o in orders]}


class TrackingUpdate(BaseModel):
    tracking_number: str


@router.put("/marketplace/orders/{order_id}/tracking")
def update_tracking(order_id: int, body: TrackingUpdate, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """Seller: correct the tracking number after the fact. Does not re-trigger the
    shipped photo requirement - use POST .../ship for the actual shipment confirmation."""
    order = db.query(MarketplaceOrder).filter(MarketplaceOrder.id == order_id, MarketplaceOrder.seller_id == user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.tracking_number = body.tracking_number
    db.commit()
    return {"status": order.status, "tracking_number": body.tracking_number}


@router.post("/marketplace/orders/{order_id}/ship")
def confirm_shipment(
    order_id: int,
    photo: UploadFile = File(...),
    tracking_number: Optional[str] = Form(default=None),
    carrier: Optional[str] = Form(default=None),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Seller: confirm shipment with a required proof-of-shipment photo (the
    QR code on the order deep-links straight here so it can be done phone-in-hand
    while packing). Requires authentication as the order's seller."""
    order = db.query(MarketplaceOrder).filter(MarketplaceOrder.id == order_id, MarketplaceOrder.seller_id == user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if carrier and carrier not in CARRIER_TRACKING_URLS:
        raise HTTPException(status_code=400, detail=f"carrier must be one of {list(CARRIER_TRACKING_URLS)}")

    ext = (photo.filename or '').rsplit('.', 1)[-1].lower() if '.' in (photo.filename or '') else 'jpg'
    if ext not in ('jpg', 'jpeg', 'png', 'webp', 'heic'):
        ext = 'jpg'
    key = f"shipment-photos/order-{order_id}-{uuid.uuid4().hex[:10]}.{ext}"

    s3 = boto3.client('s3')
    s3.upload_fileobj(photo.file, config.UPLOADS_BUCKET, key, ExtraArgs={'ContentType': photo.content_type or 'image/jpeg'})
    photo_url = f"https://{config.UPLOADS_BUCKET}.s3.amazonaws.com/{key}"

    order.shipment_photo_url = photo_url
    order.tracking_number = tracking_number or order.tracking_number
    order.carrier = carrier or order.carrier
    order.status = "shipped"
    order.shipped_at = datetime.utcnow()
    db.commit()

    return {
        "status": "shipped",
        "shipment_photo_url": photo_url,
        "tracking_number": order.tracking_number,
        "carrier": order.carrier,
    }


@router.post("/marketplace/orders/{order_id}/delivered")
def confirm_delivered(order_id: int, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """Buyer: self-confirm receipt. Requires authentication as the order's buyer."""
    order = db.query(MarketplaceOrder).filter(MarketplaceOrder.id == order_id, MarketplaceOrder.buyer_id == user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.delivered_at = datetime.utcnow()
    db.commit()
    return {"status": "delivered"}


# --- Seller Onboarding ---

@router.post("/marketplace/seller/onboard")
def create_seller_onboard_link(request: Request, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """Create Stripe Connect onboarding link for a seller. Requires authentication."""
    # Create Connect account if not exists
    if not user.stripe_connect_id:
        account = stripe.Account.create(
            type="express",
            email=user.email,
            capabilities={"card_payments": {"requested": True}, "transfers": {"requested": True}},
        )
        user.stripe_connect_id = account.id
        user.is_seller = True
        db.commit()

    # Generate onboarding link - sends the seller back to the actual site, not the API host
    frontend = config.FRONTEND_URL.rstrip('/')
    link = stripe.AccountLink.create(
        account=user.stripe_connect_id,
        refresh_url=f"{frontend}/sell?onboarding=refresh",
        return_url=f"{frontend}/sell?onboarding=complete",
        type="account_onboarding",
    )
    return {"url": link.url}


# --- Checkout ---

class CheckoutRequest(BaseModel):
    listing_id: int


@router.post("/marketplace/checkout")
def create_checkout_session(req: CheckoutRequest, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """Create Stripe Checkout session. Requires authentication."""
    listing = db.query(MarketplaceListing).filter(
        MarketplaceListing.id == req.listing_id,
        MarketplaceListing.status == 'active'
    ).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found or already sold")

    seller = db.query(User).filter(User.id == listing.seller_id).first()
    if not seller or not seller.stripe_connect_id:
        raise HTTPException(status_code=400, detail="Seller not configured for payments")

    total_cents = listing.price_cents + listing.shipping_cents + config.STRIPE_PLATFORM_FEE_CENTS
    base_url = config.FRONTEND_URL.rstrip('/')

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": listing.title},
                "unit_amount": total_cents,
            },
            "quantity": 1,
        }],
        payment_intent_data={
            "application_fee_amount": config.STRIPE_PLATFORM_FEE_CENTS,
            "transfer_data": {"destination": seller.stripe_connect_id},
        },
        shipping_address_collection={"allowed_countries": ["US"]},
        metadata={
            "listing_id": str(listing.id),
            "buyer_id": str(user.id),
            "seller_id": str(listing.seller_id),
        },
        success_url=f"{base_url}/shop?purchased=true",
        cancel_url=f"{base_url}/shop",
    )

    return {"checkout_url": session.url, "session_id": session.id}


# --- Webhook ---

@router.post("/marketplace/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe payment events."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature")

    if config.STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(payload, sig, config.STRIPE_WEBHOOK_SECRET)
        except (ValueError, stripe.error.SignatureVerificationError):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
    else:
        import json
        event = json.loads(payload)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        meta = session.get("metadata", {})
        listing_id = int(meta.get("listing_id", 0))
        buyer_id = int(meta.get("buyer_id", 0))
        seller_id = int(meta.get("seller_id", 0))

        if listing_id:
            # Mark listing as sold
            listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
            if listing:
                listing.status = "sold"

            # Create order record
            shipping = session.get("shipping_details", {}).get("address")
            order = MarketplaceOrder(
                listing_id=listing_id,
                buyer_id=buyer_id,
                seller_id=seller_id,
                price_cents=listing.price_cents if listing else 0,
                shipping_cents=listing.shipping_cents if listing else 0,
                platform_fee_cents=config.STRIPE_PLATFORM_FEE_CENTS,
                stripe_checkout_session_id=session.get("id"),
                stripe_payment_intent_id=session.get("payment_intent"),
                status="paid",
                shipping_address=shipping,
                ship_by_date=date.today() + timedelta(days=SHIP_BY_DAYS),
            )
            db.add(order)
            db.commit()

    return {"status": "ok"}
