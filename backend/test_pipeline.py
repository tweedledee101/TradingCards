"""
Quick test of data pipeline with mock data
Tests without hitting real eBay API
"""
from datetime import datetime, date
from backend.utils.database import SessionLocal, init_db
from backend.models import Card, Sale, ActiveListing
from backend.services.data_pipeline import DataPipeline


def test_pipeline():
    """Test pipeline with sample data"""
    print("🧪 Testing Data Pipeline\n")
    
    # Initialize database
    print("📦 Initializing database...")
    try:
        init_db()
        print("✅ Database initialized\n")
    except Exception as e:
        print(f"⚠️  Database already exists or error: {e}\n")
    
    db = SessionLocal()
    
    try:
        # Create test card
        print("📝 Creating test card...")
        card = Card(
            player_name="Victor Wembanyama",
            card_year=2023,
            card_set="Prizm",
            is_rookie=True,
            sport="Basketball"
        )
        db.add(card)
        db.flush()
        print(f"✅ Created card ID: {card.id}\n")
        
        # Add test sales
        print("💰 Adding test sales...")
        for i, price in enumerate([450, 425, 475, 440, 460], 1):
            sale = Sale(
                card_id=card.id,
                sale_price=price,
                sale_date=datetime.now(),
                ebay_item_id=f"test_{i}",
                graded=True,
                grade_company="PSA",
                grade_value=10.0
            )
            db.add(sale)
        db.commit()
        print("✅ Added 5 test sales\n")
        
        # Add test listings
        print("📋 Adding test listings...")
        for i, price in enumerate([480, 490], 1):
            listing = ActiveListing(
                card_id=card.id,
                listing_price=price,
                listing_type="buy_it_now",
                ebay_item_id=f"listing_{i}",
                snapshot_date=date.today()
            )
            db.add(listing)
        db.commit()
        print("✅ Added 2 test listings\n")
        
        # Calculate trends
        print("📊 Calculating trends...")
        pipeline = DataPipeline()
        calculated = pipeline.calculate_trends(card_id=card.id)
        print(f"✅ Calculated trends for {calculated} card(s)\n")
        
        # Get trending cards
        print("🔥 TOP TRENDING CARDS:")
        print("=" * 60)
        trending = pipeline.get_trending_cards(limit=5)
        
        for i, card_data in enumerate(trending, 1):
            print(f"{i}. {card_data['player_name']} - {card_data['card_year']} {card_data['card_set']}")
            print(f"   💰 Avg Price: ${card_data['avg_price']:.2f}")
            print(f"   📈 Sales: {card_data['sales_count']} | Velocity: {card_data['velocity_score']:.1f}")
            print(f"   🔥 Hotness: {card_data['hotness_score']:.1f} - {card_data['category']}")
            print()
        
        print("✅ Pipeline test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == '__main__':
    test_pipeline()
