"""
NovaAct Webhook Endpoints
Receives scraped data from NovaAct agents
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date
from backend.utils.database import SessionLocal
from backend.models import Card, GradingPopulation, Sale, ActiveListing
from sqlalchemy import and_

router = APIRouter()

class PSADataPayload(BaseModel):
    """Expected JSON payload from NovaAct PSA scraper"""
    player_name: str
    card_year: int
    card_set: str
    card_number: Optional[str] = None
    psa_10_count: int
    psa_9_count: int = 0
    psa_8_count: int = 0
    total_graded: int
    scrape_date: Optional[str] = None  # YYYY-MM-DD format

@router.post("/webhooks/novaact/psa")
def receive_psa_data(payload: PSADataPayload):
    """
    Webhook endpoint for NovaAct PSA scraper
    
    NovaAct sends JSON like:
    {
        "player_name": "Paul Skenes",
        "card_year": 2024,
        "card_set": "Bowman Chrome",
        "card_number": "1",
        "psa_10_count": 45,
        "psa_9_count": 120,
        "psa_8_count": 85,
        "total_graded": 250,
        "scrape_date": "2025-02-15"
    }
    """
    db = SessionLocal()
    try:
        # Find or create card
        card = db.query(Card).filter(
            and_(
                Card.player_name == payload.player_name,
                Card.card_year == payload.card_year,
                Card.card_set == payload.card_set
            )
        ).first()
        
        if not card:
            # Create new card if doesn't exist
            card = Card(
                player_name=payload.player_name,
                card_year=payload.card_year,
                card_set=payload.card_set,
                card_number=payload.card_number,
                is_rookie=(payload.card_year >= 2020)  # Simple heuristic
            )
            db.add(card)
            db.flush()
        
        # Calculate PSA 10 rate
        psa_10_rate = payload.psa_10_count / payload.total_graded if payload.total_graded > 0 else 0
        
        # Parse scrape date
        scrape_date = date.fromisoformat(payload.scrape_date) if payload.scrape_date else date.today()
        
        # Check if data already exists for this date
        existing = db.query(GradingPopulation).filter(
            and_(
                GradingPopulation.card_id == card.id,
                GradingPopulation.date_recorded == scrape_date
            )
        ).first()
        
        if existing:
            # Update existing record
            existing.psa_10_count = payload.psa_10_count
            existing.psa_9_count = payload.psa_9_count
            existing.psa_8_count = payload.psa_8_count
            existing.total_graded = payload.total_graded
            existing.psa_10_rate = psa_10_rate
        else:
            # Create new record
            grading = GradingPopulation(
                card_id=card.id,
                grade_company='PSA',
                psa_10_count=payload.psa_10_count,
                psa_9_count=payload.psa_9_count,
                psa_8_count=payload.psa_8_count,
                total_graded=payload.total_graded,
                psa_10_rate=psa_10_rate,
                date_recorded=scrape_date
            )
            db.add(grading)
        
        db.commit()
        
        return {
            "status": "success",
            "card_id": card.id,
            "player_name": card.player_name,
            "psa_10_rate": float(psa_10_rate),
            "message": f"PSA data recorded for {card.player_name} {card.card_year} {card.card_set}"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/webhooks/novaact/psa/test")
def test_psa_webhook():
    """Test endpoint to verify webhook is working"""
    return {
        "status": "ok",
        "message": "PSA webhook endpoint is active",
        "endpoint": "/api/webhooks/novaact/psa",
        "method": "POST",
        "expected_payload": {
            "player_name": "string",
            "card_year": "integer",
            "card_set": "string",
            "card_number": "string (optional)",
            "psa_10_count": "integer",
            "psa_9_count": "integer",
            "psa_8_count": "integer",
            "total_graded": "integer",
            "scrape_date": "string (YYYY-MM-DD, optional)"
        }
    }

class PriceBenchmarkPayload(BaseModel):
    """Expected JSON payload from NovaAct Card Ladder/130point scraper"""
    player_name: str
    card_year: int
    card_set: str
    card_number: Optional[str] = None
    source: str  # 'cardladder' or '130point'
    current_price: float
    price_7d_ago: Optional[float] = None
    price_30d_ago: Optional[float] = None
    velocity_rating: Optional[str] = None  # 'Hot', 'Warm', 'Cold', 'Stable'
    market_cap: Optional[float] = None
    scrape_date: Optional[str] = None

class PWCCSalePayload(BaseModel):
    """Expected JSON payload from NovaAct PWCC scraper"""
    player_name: str
    sport: str
    card_year: int
    card_set: str
    sale_price: float
    sale_date: str  # YYYY-MM-DD
    is_rookie: bool = False
    graded: bool = False
    title: str

class EbaySalePayload(BaseModel):
    """Expected JSON payload from NovaAct eBay scraper"""
    player_name: str
    title: str
    sale_price: float
    sale_date: str  # YYYY-MM-DD
    ebay_item_id: str
    condition: str
    card_year: int
    card_set: str
    is_rookie: bool = False
    graded: bool = False
    grade_company: Optional[str] = None
    grade_value: Optional[float] = None

class ActiveListingPayload(BaseModel):
    """Expected JSON payload from NovaAct active listings scraper"""
    player_name: str
    title: str
    price: float
    ebay_item_id: str
    listing_type: str  # 'buy_it_now' or 'auction'
    card_year: int
    card_set: str
    snapshot_date: str  # YYYY-MM-DD

@router.post("/webhooks/novaact/active-listing")
def receive_active_listing(payload: ActiveListingPayload):
    """
    Webhook endpoint for NovaAct active listings scraper
    
    Receives current eBay "Buy It Now" listings.
    Enables OpportunityAnalyzer to calculate arbitrage.
    """
    db = SessionLocal()
    try:
        # Find or create card
        card = db.query(Card).filter(
            and_(
                Card.player_name == payload.player_name,
                Card.card_year == payload.card_year,
                Card.card_set == payload.card_set
            )
        ).first()
        
        if not card:
            card = Card(
                player_name=payload.player_name,
                card_year=payload.card_year,
                card_set=payload.card_set,
                is_rookie=True  # Assume rookie for now
            )
            db.add(card)
            db.flush()
        
        # Check if listing already exists
        existing = db.query(ActiveListing).filter(
            ActiveListing.ebay_item_id == payload.ebay_item_id
        ).first()
        
        if existing:
            return {
                "status": "duplicate",
                "message": f"Listing already exists: {payload.ebay_item_id}"
            }
        
        # Create active listing record
        listing = ActiveListing(
            card_id=card.id,
            listing_price=payload.price,
            listing_type=payload.listing_type,
            ebay_item_id=payload.ebay_item_id,
            snapshot_date=date.fromisoformat(payload.snapshot_date)
        )
        db.add(listing)
        db.commit()
        
        return {
            "status": "success",
            "card_id": card.id,
            "player_name": card.player_name,
            "listing_price": float(payload.price),
            "message": f"Active listing recorded for {card.player_name}"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/webhooks/novaact/ebay")
def receive_ebay_sale(payload: EbaySalePayload):
    """
    Webhook endpoint for NovaAct eBay website scraper
    
    Receives eBay sales scraped from website (not API).
    Bypasses API rate limits.
    """
    db = SessionLocal()
    try:
        # Find or create card
        card = db.query(Card).filter(
            and_(
                Card.player_name == payload.player_name,
                Card.card_year == payload.card_year,
                Card.card_set == payload.card_set
            )
        ).first()
        
        if not card:
            card = Card(
                player_name=payload.player_name,
                card_year=payload.card_year,
                card_set=payload.card_set,
                is_rookie=payload.is_rookie
            )
            db.add(card)
            db.flush()
        
        # Check if sale already exists
        existing = db.query(Sale).filter(
            Sale.ebay_item_id == payload.ebay_item_id
        ).first()
        
        if existing:
            return {
                "status": "duplicate",
                "message": f"Sale already exists: {payload.ebay_item_id}"
            }
        
        # Create sale record
        sale = Sale(
            card_id=card.id,
            sale_price=payload.sale_price,
            sale_date=date.fromisoformat(payload.sale_date),
            ebay_item_id=payload.ebay_item_id,
            condition=payload.condition,
            graded=payload.graded,
            grade_company=payload.grade_company,
            grade_value=payload.grade_value,
            listing_title=payload.title,
            source='ebay'
        )
        db.add(sale)
        db.commit()
        
        return {
            "status": "success",
            "card_id": card.id,
            "player_name": card.player_name,
            "sale_price": float(payload.sale_price),
            "message": f"eBay sale recorded for {card.player_name}"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/webhooks/novaact/pwcc")
def receive_pwcc_sale(payload: PWCCSalePayload):
    """
    Webhook endpoint for NovaAct PWCC scraper
    
    Receives PWCC auction results for discovery.
    Stores sales data to identify trending players.
    """
    db = SessionLocal()
    try:
        from backend.models import Sale
        
        # Find or create card
        card = db.query(Card).filter(
            and_(
                Card.player_name == payload.player_name,
                Card.card_year == payload.card_year,
                Card.card_set == payload.card_set
            )
        ).first()
        
        if not card:
            card = Card(
                player_name=payload.player_name,
                card_year=payload.card_year,
                card_set=payload.card_set,
                is_rookie=payload.is_rookie,
                sport=payload.sport
            )
            db.add(card)
            db.flush()
        
        # Create sale record
        sale = Sale(
            card_id=card.id,
            sale_price=payload.sale_price,
            sale_date=date.fromisoformat(payload.sale_date),
            graded=payload.graded,
            listing_title=payload.title,
            source='pwcc'
        )
        db.add(sale)
        db.commit()
        
        return {
            "status": "success",
            "card_id": card.id,
            "player_name": card.player_name,
            "sale_price": float(payload.sale_price),
            "message": f"PWCC sale recorded for {card.player_name}"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/webhooks/novaact/price-benchmark")
def receive_price_benchmark(payload: PriceBenchmarkPayload):
    """
    Webhook endpoint for NovaAct Card Ladder/130point scraper
    
    NovaAct sends JSON like:
    {
        "player_name": "Paul Skenes",
        "card_year": 2024,
        "card_set": "Bowman Chrome",
        "source": "cardladder",
        "current_price": 45.00,
        "price_7d_ago": 38.00,
        "price_30d_ago": 32.00,
        "velocity_rating": "Hot",
        "market_cap": 11250.00
    }
    """
    db = SessionLocal()
    try:
        from backend.models import PriceBenchmark
        
        # Find or create card
        card = db.query(Card).filter(
            and_(
                Card.player_name == payload.player_name,
                Card.card_year == payload.card_year,
                Card.card_set == payload.card_set
            )
        ).first()
        
        if not card:
            card = Card(
                player_name=payload.player_name,
                card_year=payload.card_year,
                card_set=payload.card_set,
                card_number=payload.card_number,
                is_rookie=(payload.card_year >= 2020)
            )
            db.add(card)
            db.flush()
        
        # Calculate percentage changes
        change_7d = None
        change_30d = None
        if payload.price_7d_ago and payload.price_7d_ago > 0:
            change_7d = ((payload.current_price - payload.price_7d_ago) / payload.price_7d_ago) * 100
        if payload.price_30d_ago and payload.price_30d_ago > 0:
            change_30d = ((payload.current_price - payload.price_30d_ago) / payload.price_30d_ago) * 100
        
        scrape_date = date.fromisoformat(payload.scrape_date) if payload.scrape_date else date.today()
        
        # Check if data exists
        existing = db.query(PriceBenchmark).filter(
            and_(
                PriceBenchmark.card_id == card.id,
                PriceBenchmark.source == payload.source,
                PriceBenchmark.date_recorded == scrape_date
            )
        ).first()
        
        if existing:
            existing.current_price = payload.current_price
            existing.price_7d_ago = payload.price_7d_ago
            existing.price_30d_ago = payload.price_30d_ago
            existing.change_7d = change_7d
            existing.change_30d = change_30d
            existing.velocity_rating = payload.velocity_rating
            existing.market_cap = payload.market_cap
        else:
            benchmark = PriceBenchmark(
                card_id=card.id,
                source=payload.source,
                current_price=payload.current_price,
                price_7d_ago=payload.price_7d_ago,
                price_30d_ago=payload.price_30d_ago,
                change_7d=change_7d,
                change_30d=change_30d,
                velocity_rating=payload.velocity_rating,
                market_cap=payload.market_cap,
                date_recorded=scrape_date
            )
            db.add(benchmark)
        
        db.commit()
        
        return {
            "status": "success",
            "card_id": card.id,
            "player_name": card.player_name,
            "source": payload.source,
            "change_7d": float(change_7d) if change_7d else None,
            "change_30d": float(change_30d) if change_30d else None,
            "velocity_rating": payload.velocity_rating,
            "message": f"Price benchmark recorded for {card.player_name} from {payload.source}"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/grading/{card_id}")
def get_grading_data(card_id: int):
    """Get PSA grading data for a specific card"""
    db = SessionLocal()
    try:
        grading = db.query(GradingPopulation).filter(
            GradingPopulation.card_id == card_id
        ).order_by(GradingPopulation.date_recorded.desc()).first()
        
        if not grading:
            raise HTTPException(status_code=404, detail="No grading data found for this card")
        
        return {
            "card_id": grading.card_id,
            "psa_10_count": grading.psa_10_count,
            "psa_9_count": grading.psa_9_count,
            "psa_8_count": grading.psa_8_count,
            "total_graded": grading.total_graded,
            "psa_10_rate": float(grading.psa_10_rate) if grading.psa_10_rate else 0,
            "date_recorded": grading.date_recorded.isoformat()
        }
    finally:
        db.close()

@router.get("/benchmarks/{card_id}")
def get_price_benchmarks(card_id: int, source: Optional[str] = None):
    """Get price benchmark data for a specific card"""
    db = SessionLocal()
    try:
        from backend.models import PriceBenchmark
        
        query = db.query(PriceBenchmark).filter(PriceBenchmark.card_id == card_id)
        
        if source:
            query = query.filter(PriceBenchmark.source == source)
        
        benchmarks = query.order_by(PriceBenchmark.date_recorded.desc()).all()
        
        if not benchmarks:
            raise HTTPException(status_code=404, detail="No benchmark data found")
        
        return {
            "card_id": card_id,
            "benchmarks": [
                {
                    "source": b.source,
                    "current_price": float(b.current_price) if b.current_price else None,
                    "price_7d_ago": float(b.price_7d_ago) if b.price_7d_ago else None,
                    "price_30d_ago": float(b.price_30d_ago) if b.price_30d_ago else None,
                    "change_7d": float(b.change_7d) if b.change_7d else None,
                    "change_30d": float(b.change_30d) if b.change_30d else None,
                    "velocity_rating": b.velocity_rating,
                    "market_cap": float(b.market_cap) if b.market_cap else None,
                    "date_recorded": b.date_recorded.isoformat()
                }
                for b in benchmarks
            ]
        }
    finally:
        db.close()
