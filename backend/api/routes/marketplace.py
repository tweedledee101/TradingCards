"""
Ragnarok Marketplace API - Stripe Connect + Checkout + Webhooks

Handles:
- Seller onboarding (Stripe Connect)
- Checkout session creation with $1 platform fee
- Payment webhook (mark sold, notify seller)
"""
import stripe
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from backend.config.settings import config
from backend.utils.database import get_db
from backend.models import User, MarketplaceListing, MarketplaceOrder

stripe.api_key = config.STRIPE_SECRET_KEY
router = APIRouter()


# --- Listings CRUD ---

class ListingCreate(BaseModel):
    title: str
    description: Optional[str] = None
    price_cents: int
    category: str
    condition: Optional[str] = None
    shipping_cents: int = 0
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
            "shipping_cents": l.shipping_cents, "image_urls": l.image_urls or [],
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
    return {
        "id": l.id, "seller_id": l.seller_id, "title": l.title,
        "description": l.description, "price_cents": l.price_cents,
        "category": l.category, "condition": l.condition,
        "shipping_cents": l.shipping_cents, "image_urls": l.image_urls or [],
        "status": l.status, "created_at": l.created_at.isoformat() if l.created_at else None,
        "seller_name": seller.display_name or seller.email if seller else "Unknown",
    }


@router.post("/marketplace/listings")
def create_listing(listing: ListingCreate, seller_id: int, db: Session = Depends(get_db)):
    """Seller: create a new listing."""
    user = db.query(User).filter(User.id == seller_id, User.is_seller == True).first()
    if not user:
        raise HTTPException(status_code=403, detail="Not a registered seller")
    if listing.price_cents < 200:
        raise HTTPException(status_code=400, detail="Minimum price is $2.00")
    item = MarketplaceListing(
        seller_id=seller_id, title=listing.title, description=listing.description,
        price_cents=listing.price_cents, category=listing.category,
        condition=listing.condition, shipping_cents=listing.shipping_cents,
        image_urls=listing.image_urls, status='active',
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "status": "active"}


@router.delete("/marketplace/listings/{listing_id}")
def delete_listing(listing_id: int, seller_id: int, db: Session = Depends(get_db)):
    """Seller: remove a listing."""
    l = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id, MarketplaceListing.seller_id == seller_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Listing not found")
    l.status = "removed"
    db.commit()
    return {"status": "removed"}


# --- Seller Orders ---

@router.get("/marketplace/orders")
def get_seller_orders(seller_id: int, db: Session = Depends(get_db)):
    """Seller: view their orders."""
    orders = db.query(MarketplaceOrder).filter(MarketplaceOrder.seller_id == seller_id).order_by(MarketplaceOrder.created_at.desc()).all()
    return {"orders": [{
        "id": o.id, "listing_id": o.listing_id, "price_cents": o.price_cents,
        "shipping_cents": o.shipping_cents, "status": o.status,
        "shipping_address": o.shipping_address, "tracking_number": o.tracking_number,
        "created_at": o.created_at.isoformat() if o.created_at else None,
    } for o in orders]}


class TrackingUpdate(BaseModel):
    tracking_number: str


@router.put("/marketplace/orders/{order_id}/tracking")
def update_tracking(order_id: int, body: TrackingUpdate, seller_id: int, db: Session = Depends(get_db)):
    """Seller: enter tracking number."""
    order = db.query(MarketplaceOrder).filter(MarketplaceOrder.id == order_id, MarketplaceOrder.seller_id == seller_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    from datetime import datetime
    order.tracking_number = body.tracking_number
    order.status = "shipped"
    order.shipped_at = datetime.utcnow()
    db.commit()
    return {"status": "shipped", "tracking_number": body.tracking_number}


# --- Seller Onboarding ---

@router.post("/marketplace/seller/onboard")
def create_seller_onboard_link(request: Request, user_id: int, db: Session = Depends(get_db)):
    """Create Stripe Connect onboarding link for a seller."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

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

    # Generate onboarding link
    link = stripe.AccountLink.create(
        account=user.stripe_connect_id,
        refresh_url=str(request.base_url) + "api/marketplace/seller/onboard/refresh",
        return_url=str(request.base_url) + "api/marketplace/seller/onboard/complete",
        type="account_onboarding",
    )
    return {"url": link.url}


@router.get("/marketplace/seller/onboard/complete")
def seller_onboard_complete():
    return {"message": "Stripe Connect onboarding complete. You can now sell on Ragnarok!"}


@router.get("/marketplace/seller/onboard/refresh")
def seller_onboard_refresh():
    return {"message": "Onboarding session expired. Please try again."}


# --- Checkout ---

class CheckoutRequest(BaseModel):
    listing_id: int
    buyer_id: int


@router.post("/marketplace/checkout")
def create_checkout_session(req: CheckoutRequest, request: Request, db: Session = Depends(get_db)):
    """Create Stripe Checkout session with $1 platform fee via Connect."""
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
    base_url = str(request.base_url).rstrip('/')

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
            "buyer_id": str(req.buyer_id),
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
            )
            db.add(order)
            db.commit()

    return {"status": "ok"}
