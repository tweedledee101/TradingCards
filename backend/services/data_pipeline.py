"""
Data Pipeline Service
Connects eBay scraper to database and calculates trends
"""
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.models import Card, Sale, ActiveListing, PriceTrend
from backend.scrapers.ebay_scraper import EbayScraper
from backend.services.trend_calculator import TrendCalculator
from backend.utils.database import SessionLocal
from backend.utils.player_extractor import player_extractor


class DataPipeline:
    """Orchestrates data flow from scrapers to database"""
    
    def __init__(self):
        self.scraper = EbayScraper()
        self.calculator = TrendCalculator()
    
    def find_or_create_card(self, db: Session, sale_data: Dict) -> Card:
        """Find existing card or create new one, matching on variant columns including card_number"""
        parallel = sale_data.get('parallel') or 'Base'
        grade_company = sale_data.get('grade_company') or None
        grade_value = sale_data.get('grade_value') or None
        card_number = sale_data.get('card_number') or None
        
        card = db.query(Card).filter(
            Card.player_name == sale_data.get('player_name', 'Unknown'),
            Card.card_year == sale_data['card_year'],
            Card.card_set == sale_data['card_set'],
            Card.card_number == card_number,
            Card.parallel == parallel,
            Card.grade_company == grade_company,
            Card.grade_value == grade_value
        ).first()
        
        if not card:
            card = Card(
                player_name=sale_data.get('player_name', 'Unknown'),
                card_year=sale_data['card_year'],
                card_set=sale_data['card_set'],
                card_number=card_number,
                parallel=parallel,
                grade_company=grade_company,
                grade_value=grade_value,
                is_rookie=sale_data.get('is_rookie', False),
                sport=sale_data.get('sport', 'Unknown')
            )
            db.add(card)
            db.flush()
        
        return card
    
    def import_sales(self, query: str, days_back: int = 7, player_name: str = None, sport: str = None) -> int:
        """Import sales from eBay and store in database"""
        db = SessionLocal()
        try:
            sales_data = self.scraper.search_sold_listings(query, days_back, player_name, sport)
            imported = 0
            skipped_no_player = 0
            
            for sale in sales_data:
                # Skip if missing sale_date
                if not sale.get('sale_date'):
                    continue
                
                # Skip if no validated player_name
                if not sale.get('player_name'):
                    skipped_no_player += 1
                    continue
                
                # Skip if already exists
                existing = db.query(Sale).filter(Sale.ebay_item_id == sale['ebay_item_id']).first()
                if existing:
                    continue
                
                # Find or create card
                card = self.find_or_create_card(db, sale)
                
                # Create sale record
                new_sale = Sale(
                    card_id=card.id,
                    sale_price=sale['price'],
                    sale_date=datetime.fromisoformat(sale['sale_date'].replace('Z', '+00:00')),
                    listing_title=sale['title'],
                    ebay_item_id=sale['ebay_item_id'],
                    condition=sale.get('condition'),
                    graded=sale['graded'],
                    grade_company=sale['grade_company'],
                    grade_value=sale['grade_value']
                )
                db.add(new_sale)
                imported += 1
            
            db.commit()
            if skipped_no_player > 0:
                print(f"⚠️  Skipped {skipped_no_player} sales (no validated player name)")
            return imported
        except Exception as e:
            db.rollback()
            print(f"Error importing sales: {e}")
            return 0
        finally:
            db.close()
    
    def import_active_listings(self, query: str) -> int:
        """Import active listings from eBay"""
        db = SessionLocal()
        try:
            today = date.today()
            
            # Delete ALL old listings (not just today) to avoid duplicates
            deleted = db.query(ActiveListing).delete()
            db.commit()
            print(f"🗑️  Cleared {deleted} old listings")
            
            listings = self.scraper.get_active_listings(query)
            imported = 0
            
            for listing in listings:
                # Extract card info from title
                card_info = listing.get('card_info', {})
                
                # Skip if missing required fields
                if not card_info.get('card_year') or not card_info.get('card_set'):
                    continue
                
                # Extract player name from title
                title = listing.get('title', '')
                player_info = player_extractor.extract_player(title)
                
                if player_info:
                    card_info['player_name'], card_info['sport'] = player_info
                else:
                    card_info['player_name'] = 'Unknown'
                    card_info['sport'] = 'Unknown'
                
                card = self.find_or_create_card(db, card_info)
                
                new_listing = ActiveListing(
                    card_id=card.id,
                    listing_price=listing['price'],
                    listing_type=listing['listing_type'],
                    ebay_item_id=listing['ebay_item_id'],
                    snapshot_date=today
                )
                db.add(new_listing)
                imported += 1
            
            db.commit()
            return imported
        except Exception as e:
            db.rollback()
            print(f"Error importing listings: {e}")
            return 0
        finally:
            db.close()
    
    def calculate_trends(self, card_id: Optional[int] = None) -> int:
        """Calculate price trends for cards"""
        db = SessionLocal()
        try:
            today = date.today()
            date_7d_ago = today - timedelta(days=7)
            date_30d_ago = today - timedelta(days=30)
            
            # Get cards to process
            if card_id:
                cards = [db.query(Card).get(card_id)]
            else:
                cards = db.query(Card).all()
            
            calculated = 0
            for card in cards:
                # Get sales data
                recent_sales = db.query(Sale).filter(
                    Sale.card_id == card.id,
                    Sale.sale_date >= date_7d_ago
                ).all()
                
                if not recent_sales:
                    continue
                
                # Calculate metrics
                avg_price = sum(float(s.sale_price) for s in recent_sales) / len(recent_sales)
                sales_count = len(recent_sales)
                
                # Get active listings count
                listings_count = db.query(ActiveListing).filter(
                    ActiveListing.card_id == card.id,
                    ActiveListing.snapshot_date == today
                ).count()
                
                # Get 7-day old price
                old_sales = db.query(func.avg(Sale.sale_price)).filter(
                    Sale.card_id == card.id,
                    Sale.sale_date < date_7d_ago,
                    Sale.sale_date >= date_30d_ago
                ).scalar()
                price_7d_ago = float(old_sales) if old_sales else avg_price
                
                # Calculate scores
                metrics = self.calculator.calculate_all_metrics(
                    sales_count=sales_count,
                    active_listings=listings_count,
                    current_price=avg_price,
                    price_7d_ago=price_7d_ago
                )
                
                # Check if trend exists for today
                existing = db.query(PriceTrend).filter(
                    PriceTrend.card_id == card.id,
                    PriceTrend.trend_date == today
                ).first()
                
                if existing:
                    # Update existing
                    existing.avg_price = avg_price
                    existing.sales_count = sales_count
                    existing.active_listings_count = listings_count
                    existing.velocity_score = metrics['velocity_score']
                    existing.hotness_score = metrics['hotness_score']
                else:
                    # Create new
                    trend = PriceTrend(
                        card_id=card.id,
                        trend_date=today,
                        avg_price=avg_price,
                        sales_count=sales_count,
                        active_listings_count=listings_count,
                        velocity_score=metrics['velocity_score'],
                        hotness_score=metrics['hotness_score']
                    )
                    db.add(trend)
                
                calculated += 1
            
            db.commit()
            return calculated
        except Exception as e:
            db.rollback()
            print(f"Error calculating trends: {e}")
            return 0
        finally:
            db.close()
    
    def get_trending_cards(self, limit: int = 10) -> List[Dict]:
        """Get top trending cards by hotness score"""
        db = SessionLocal()
        try:
            today = date.today()
            results = db.query(PriceTrend, Card).join(Card).filter(
                PriceTrend.trend_date == today
            ).order_by(PriceTrend.hotness_score.desc()).limit(limit).all()
            
            trending = []
            for trend, card in results:
                trending.append({
                    'player_name': card.player_name,
                    'card_year': card.card_year,
                    'card_set': card.card_set,
                    'is_rookie': card.is_rookie,
                    'avg_price': float(trend.avg_price),
                    'sales_count': trend.sales_count,
                    'velocity_score': float(trend.velocity_score),
                    'hotness_score': float(trend.hotness_score),
                    'category': self.calculator.get_trend_category(float(trend.hotness_score))
                })
            
            return trending
        finally:
            db.close()
