"""
Ragnarok Marketplace API - Stripe Connect + Checkout + Webhooks

Handles:
- Seller onboarding (Stripe Connect)
- Checkout session creation with $1 platform fee
- Payment webhook (mark sold, notify seller)
- Shipping: method selection, 3-day ship-by SLA, photo-verified shipment
  confirmation, buyer-facing order status
"""
import io
import uuid
from datetime import date, timedelta, datetime, timezone

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
from backend.models import User, MarketplaceListing, MarketplaceOrder, Card, Sale

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

# Shipment-photo upload limits. The bucket serves shipment-photos/* publicly, so
# we must never store attacker-controlled Content-Type: derive it from the file's
# actual magic bytes, not from the client-supplied filename or content_type.
MAX_PHOTO_BYTES = 10 * 1024 * 1024  # 10 MB


def _sniff_image(b: bytes) -> Optional[str]:
    """Return a normalized image extension from magic bytes, or None if not an
    image we accept. Ignores whatever the client claimed the file was."""
    if b[:3] == b'\xff\xd8\xff':
        return 'jpg'
    if b[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    if b[:4] == b'RIFF' and b[8:12] == b'WEBP':
        return 'webp'
    if b[4:8] == b'ftyp' and b[8:12] in (b'heic', b'heix', b'hevc', b'mif1', b'heim', b'heis', b'hevx'):
        return 'heic'
    return None


_IMAGE_CONTENT_TYPES = {
    'jpg': 'image/jpeg', 'png': 'image/png', 'webp': 'image/webp', 'heic': 'image/heic',
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


@router.get("/marketplace/fees")
def get_fees():
    """Public fee disclosure. The platform fee is a flat per-transaction charge
    paid by the BUYER on top of the item + shipping -- sellers keep 100% of their
    listed price. Surfaced in the UI for transparency (a wedge vs percentage fees)."""
    return {
        "platform_fee_cents": config.STRIPE_PLATFORM_FEE_CENTS,
        "fee_model": "flat_per_transaction",
        "paid_by": "buyer",
        "seller_keeps_full_price": True,
    }


@router.get("/marketplace/pricing-guidance")
def pricing_guidance(query: str, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """Seller-facing pricing guidance from recent sold comps. Exposes ONLY summary
    stats derived from public sale history -- never opportunity/edge internals --
    so a seller can price competitively. Matches cards by player name."""
    q = (query or "").strip()
    if len(q) < 3:
        return {"query": q, "sample_size": 0, "message": "Type at least 3 characters for a price check."}

    like = f"%{q}%"
    card_ids = db.query(Card.id).filter(Card.player_name.ilike(like)).subquery()
    d30 = datetime.now() - timedelta(days=30)
    d90 = datetime.now() - timedelta(days=90)

    prices_90 = [
        float(p) for (p,) in db.query(Sale.sale_price).filter(
            Sale.card_id.in_(card_ids), Sale.sale_date >= d90, Sale.sale_price.isnot(None)
        ).all()
    ]
    if not prices_90:
        return {"query": q, "sample_size": 0, "message": "No recent sold comps for a card like that yet."}

    prices_30 = [
        float(p) for (p,) in db.query(Sale.sale_price).filter(
            Sale.card_id.in_(card_ids), Sale.sale_date >= d30, Sale.sale_price.isnot(None)
        ).all()
    ]

    avg90 = round(sum(prices_90) / len(prices_90), 2)
    avg30 = round(sum(prices_30) / len(prices_30), 2) if prices_30 else None
    sample = len(prices_90)
    return {
        "query": q,
        "sample_size": sample,
        "sales_30d": len(prices_30),
        "avg_sale_price_30d": avg30,
        "avg_sale_price_90d": avg90,
        "recommended_price": avg30 or avg90,
        "low_90d": round(min(prices_90), 2),
        "high_90d": round(max(prices_90), 2),
        "typical_days_between_sales": round(90 / sample, 1) if sample else None,
        "disclaimer": "Based on recent sold comps for similar cards. Actual results depend on condition, grade, and timing.",
    }


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
    # Only a paid order can be shipped. Blocks shipping an unpaid/refunded order
    # and prevents replay (a second call finds status='shipped', not 'paid').
    if order.status != "paid":
        raise HTTPException(status_code=409, detail=f"Order cannot be shipped from status '{order.status}'")
    if carrier and carrier not in CARRIER_TRACKING_URLS:
        raise HTTPException(status_code=400, detail=f"carrier must be one of {list(CARRIER_TRACKING_URLS)}")

    # Read with a hard cap and validate the actual bytes are an image we accept.
    # The extension and Content-Type are derived from the magic bytes, never from
    # the client, so a text/html payload can't be stored and served as HTML.
    data = photo.file.read(MAX_PHOTO_BYTES + 1)
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Photo too large (max 10 MB)")
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    kind = _sniff_image(data)
    if kind is None:
        raise HTTPException(status_code=400, detail="File must be a JPEG, PNG, WEBP, or HEIC image")

    key = f"shipment-photos/order-{order_id}-{uuid.uuid4().hex[:10]}.{kind}"
    s3 = boto3.client('s3')
    s3.upload_fileobj(
        io.BytesIO(data), config.UPLOADS_BUCKET, key,
        ExtraArgs={'ContentType': _IMAGE_CONTENT_TYPES[kind]},
    )
    photo_url = f"https://{config.UPLOADS_BUCKET}.s3.amazonaws.com/{key}"

    order.shipment_photo_url = photo_url
    order.tracking_number = tracking_number or order.tracking_number
    order.carrier = carrier or order.carrier
    order.status = "shipped"
    order.shipped_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "status": "shipped",
        "shipment_photo_url": photo_url,
        "tracking_number": order.tracking_number,
        "carrier": order.carrier,
    }


@router.post("/marketplace/orders/{order_id}/delivered")
def confirm_delivered(order_id: int, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """Buyer: self-confirm receipt. Requires authentication as the order's buyer.
    Releases the escrowed funds to the seller (see checkout: funds are held on the
    platform until delivery, not transferred at payment time)."""
    order = db.query(MarketplaceOrder).filter(MarketplaceOrder.id == order_id, MarketplaceOrder.buyer_id == user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "shipped":
        raise HTTPException(status_code=409, detail="Order must be shipped before it can be marked delivered")

    order.status = "delivered"
    order.delivered_at = datetime.now(timezone.utc)

    # Release escrow: transfer the item + shipping to the seller; the platform
    # keeps the platform fee. Idempotent via funds_released_at. Don't fail the
    # buyer's confirmation if the transfer hiccups - leave it unreleased so a
    # retry/cron can settle it later.
    if order.funds_released_at is None:
        seller = db.query(User).filter(User.id == order.seller_id).first()
        if seller and seller.stripe_connect_id:
            try:
                stripe.Transfer.create(
                    amount=order.price_cents + order.shipping_cents,
                    currency="usd",
                    destination=seller.stripe_connect_id,
                    transfer_group=f"order-{order.id}",
                    metadata={"order_id": str(order.id)},
                )
                order.funds_released_at = datetime.now(timezone.utc)
            except Exception:
                pass

    db.commit()
    return {"status": "delivered", "funds_released": order.funds_released_at is not None}


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

    if listing.seller_id == user.id:
        raise HTTPException(status_code=400, detail="You can't buy your own listing")

    seller = db.query(User).filter(User.id == listing.seller_id).first()
    if not seller or not seller.stripe_connect_id:
        raise HTTPException(status_code=400, detail="Seller not configured for payments")

    total_cents = listing.price_cents + listing.shipping_cents + config.STRIPE_PLATFORM_FEE_CENTS
    base_url = config.FRONTEND_URL.rstrip('/')

    # Escrow model: charge the full amount to the PLATFORM account (no
    # transfer_data.destination). Funds are held until the buyer confirms
    # delivery, at which point confirm_delivered transfers the item+shipping to
    # the seller and the platform keeps the fee. This is what gives the ship-by
    # SLA and delivery confirmation actual financial teeth.
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

    # Fail closed. Without the signing secret we cannot prove the event came from
    # Stripe, and an unsigned handler lets anyone POST a forged
    # checkout.session.completed to mint a "paid" order for free. Refuse rather
    # than trust the body.
    if not config.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook signing secret not configured")
    try:
        event = stripe.Webhook.construct_event(payload, sig, config.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        meta = session.get("metadata", {})
        try:
            listing_id = int(meta.get("listing_id", 0))
            buyer_id = int(meta.get("buyer_id", 0))
            seller_id = int(meta.get("seller_id", 0))
        except (TypeError, ValueError):
            # Malformed metadata - ack so Stripe stops retrying, but do nothing.
            return {"status": "ok", "ignored": "bad_metadata"}

        session_id = session.get("id")
        payment_intent = session.get("payment_intent")

        if listing_id and session_id:
            # Idempotency: a redelivered webhook for the same session is a no-op.
            existing = db.query(MarketplaceOrder).filter(
                MarketplaceOrder.stripe_checkout_session_id == session_id
            ).first()
            if existing:
                return {"status": "ok", "duplicate": True}

            # Oversell guard for one-of-one inventory: if another buyer already
            # has a live order for this listing, this second payment lost the
            # race - refund it rather than create a duplicate claim on one card.
            already = db.query(MarketplaceOrder).filter(
                MarketplaceOrder.listing_id == listing_id,
                MarketplaceOrder.status.in_(("paid", "shipped", "delivered")),
            ).first()
            if already:
                if payment_intent:
                    try:
                        stripe.Refund.create(payment_intent=payment_intent)
                    except Exception:
                        pass
                return {"status": "ok", "oversold_refunded": True}

            listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
            if listing:
                listing.status = "sold"

            shipping = session.get("shipping_details", {}).get("address")
            order = MarketplaceOrder(
                listing_id=listing_id,
                buyer_id=buyer_id,
                seller_id=seller_id,
                price_cents=listing.price_cents if listing else 0,
                shipping_cents=listing.shipping_cents if listing else 0,
                platform_fee_cents=config.STRIPE_PLATFORM_FEE_CENTS,
                stripe_checkout_session_id=session_id,
                stripe_payment_intent_id=payment_intent,
                status="paid",
                shipping_address=shipping,
                ship_by_date=date.today() + timedelta(days=SHIP_BY_DAYS),
            )
            db.add(order)
            try:
                db.commit()
            except Exception:
                # Unique constraint tripped by a concurrent delivery of the same
                # session - treat as the duplicate it is.
                db.rollback()
                return {"status": "ok", "duplicate": True}

    return {"status": "ok"}
