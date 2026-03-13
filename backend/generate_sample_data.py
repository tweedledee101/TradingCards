"""
Generate realistic sample data for testing UI
Creates 25 diverse cards with different price points, velocities, and hotness scores
"""
from datetime import datetime, date, timedelta
import random
from backend.utils.database import SessionLocal, init_db
from backend.models import Card, Sale, ActiveListing, PriceTrend, Watchlist, Inventory, InventorySale, GradingPopulation, PriceBenchmark
from backend.services.data_pipeline import DataPipeline

SAMPLE_CARDS = [
    # GREEN ZONE - Buy Now (affordable, high margin, rising prices)
    {"player": "Paul Skenes", "year": 2024, "set": "Bowman Chrome", "card_number": "150", "parallel": "Base", "grade_company": "PSA", "grade_value": 10, "sport": "Baseball", "price": 45, "velocity": 85, "sales": 28, "price_trend": 1.25},
    {"player": "Caitlin Clark", "year": 2024, "set": "Prizm", "card_number": "1", "parallel": "Silver", "grade_company": "PSA", "grade_value": 9, "sport": "Basketball", "price": 32, "velocity": 78, "sales": 35, "price_trend": 1.30},
    {"player": "Caleb Williams", "year": 2024, "set": "Prizm", "card_number": "301", "parallel": "Base", "grade_company": "Raw", "grade_value": None, "sport": "Football", "price": 28, "velocity": 72, "sales": 42, "price_trend": 1.20},
    {"player": "Anthony Edwards", "year": 2020, "set": "Prizm", "card_number": "258", "parallel": "Silver", "grade_company": "PSA", "grade_value": 10, "sport": "Basketball", "price": 65, "velocity": 68, "sales": 18, "price_trend": 1.15},
    
    # YELLOW ZONE - Watch (moderate momentum)
    {"player": "Victor Wembanyama", "year": 2023, "set": "Prizm", "card_number": "1", "parallel": "Red Ice", "grade_company": "PSA", "grade_value": 9, "sport": "Basketball", "price": 450, "velocity": 55, "sales": 12, "price_trend": 1.10},
    {"player": "CJ Stroud", "year": 2023, "set": "Prizm", "card_number": "301", "parallel": "Base", "grade_company": "BGS", "grade_value": 9.5, "sport": "Football", "price": 85, "velocity": 48, "sales": 22, "price_trend": 1.08},
    {"player": "Gunnar Henderson", "year": 2023, "set": "Topps Chrome", "card_number": "75", "parallel": "Base", "grade_company": "PSA", "grade_value": 10, "sport": "Baseball", "price": 38, "velocity": 42, "sales": 15, "price_trend": 1.05},
    {"player": "Jahmyr Gibbs", "year": 2023, "set": "Optic", "card_number": "125", "parallel": "Purple", "grade_company": "Raw", "grade_value": None, "sport": "Football", "price": 22, "velocity": 45, "sales": 31, "price_trend": 1.12},
    
    # WHITE ZONE - Skip (flat or declining)
    {"player": "Michael Jordan", "year": 1986, "set": "Fleer", "card_number": "57", "parallel": "Base", "grade_company": "PSA", "grade_value": 8, "sport": "Basketball", "price": 8500, "velocity": 25, "sales": 3, "price_trend": 1.02},
    {"player": "LeBron James", "year": 2003, "set": "Topps Chrome", "card_number": "111", "parallel": "Base", "grade_company": "BGS", "grade_value": 9, "sport": "Basketball", "price": 3200, "velocity": 18, "sales": 5, "price_trend": 0.98},
    {"player": "Patrick Mahomes", "year": 2017, "set": "Prizm", "card_number": "252", "parallel": "Silver", "grade_company": "PSA", "grade_value": 10, "sport": "Football", "price": 1850, "velocity": 32, "sales": 7, "price_trend": 1.00},
    {"player": "Shohei Ohtani", "year": 2018, "set": "Topps Chrome", "card_number": "700", "parallel": "Base", "grade_company": "PSA", "grade_value": 9, "sport": "Baseball", "price": 425, "velocity": 28, "sales": 9, "price_trend": 0.95},
    
    # MID-RANGE - Mixed signals
    {"player": "Brock Purdy", "year": 2022, "set": "Prizm", "card_number": "362", "parallel": "Base", "grade_company": "Raw", "grade_value": None, "sport": "Football", "price": 48, "velocity": 62, "sales": 25, "price_trend": 1.18},
    {"player": "Paolo Banchero", "year": 2022, "set": "Prizm", "card_number": "1", "parallel": "Silver", "grade_company": "PSA", "grade_value": 9, "sport": "Basketball", "price": 95, "velocity": 38, "sales": 14, "price_trend": 1.06},
    {"player": "Julio Rodriguez", "year": 2022, "set": "Bowman Chrome", "card_number": "100", "parallel": "Base", "grade_company": "PSA", "grade_value": 10, "sport": "Baseball", "price": 72, "velocity": 44, "sales": 19, "price_trend": 1.04},
    {"player": "Jalen Hurts", "year": 2020, "set": "Prizm", "card_number": "345", "parallel": "Silver", "grade_company": "BGS", "grade_value": 9.5, "sport": "Football", "price": 125, "velocity": 51, "sales": 16, "price_trend": 1.09},
    
    # BUDGET FRIENDLY - Good for small bankroll
    {"player": "Marvin Harrison Jr", "year": 2024, "set": "Prizm", "card_number": "305", "parallel": "Base", "grade_company": "Raw", "grade_value": None, "sport": "Football", "price": 18, "velocity": 75, "sales": 38, "price_trend": 1.28},
    {"player": "Jayden Daniels", "year": 2024, "set": "Prizm", "card_number": "302", "parallel": "Base", "grade_company": "Raw", "grade_value": None, "sport": "Football", "price": 24, "velocity": 71, "sales": 33, "price_trend": 1.22},
    {"player": "Elly De La Cruz", "year": 2023, "set": "Topps Chrome", "card_number": "50", "parallel": "Orange", "grade_company": "PSA", "grade_value": 9, "sport": "Baseball", "price": 35, "velocity": 58, "sales": 21, "price_trend": 1.14},
    {"player": "Brandon Miller", "year": 2023, "set": "Prizm", "card_number": "2", "parallel": "Base", "grade_company": "PSA", "grade_value": 10, "sport": "Basketball", "price": 42, "velocity": 47, "sales": 17, "price_trend": 1.07},
    
    # HIGH VALUE - Need bigger budget
    {"player": "Connor Bedard", "year": 2023, "set": "Upper Deck", "card_number": "201", "parallel": "Base", "grade_company": "BGS", "grade_value": 10, "sport": "Hockey", "price": 380, "velocity": 65, "sales": 11, "price_trend": 1.16},
    {"player": "Bryce Young", "year": 2023, "set": "Prizm", "card_number": "301", "parallel": "Silver", "grade_company": "PSA", "grade_value": 9, "sport": "Football", "price": 68, "velocity": 41, "sales": 13, "price_trend": 0.92},
    {"player": "Scoot Henderson", "year": 2023, "set": "Prizm", "card_number": "3", "parallel": "Base", "grade_company": "Raw", "grade_value": None, "sport": "Basketball", "price": 52, "velocity": 36, "sales": 10, "price_trend": 0.96},
    {"player": "Corbin Carroll", "year": 2023, "set": "Topps Chrome", "card_number": "25", "parallel": "Base", "grade_company": "PSA", "grade_value": 9, "sport": "Baseball", "price": 45, "velocity": 39, "sales": 12, "price_trend": 1.03},
    {"player": "Jasson Dominguez", "year": 2023, "set": "Bowman Chrome", "card_number": "88", "parallel": "Purple", "grade_company": "PSA", "grade_value": 10, "sport": "Baseball", "price": 58, "velocity": 43, "sales": 15, "price_trend": 1.11},
]

def generate_sample_data():
    print("🎲 Generating 25 realistic sample cards...\n")
    
    init_db()
    db = SessionLocal()
    
    try:
        # Clear existing data in correct order (foreign keys)
        db.query(InventorySale).delete()
        db.query(Inventory).delete()
        db.query(Watchlist).delete()
        db.query(PriceTrend).delete()
        db.query(ActiveListing).delete()
        db.query(Sale).delete()
        db.query(GradingPopulation).delete()
        db.query(PriceBenchmark).delete()
        db.query(Card).delete()
        db.commit()
        print("✅ Cleared existing data\n")
        
        for idx, card_data in enumerate(SAMPLE_CARDS, 1):
            # Create card
            card = Card(
                player_name=card_data["player"],
                card_year=card_data["year"],
                card_set=card_data["set"],
                card_number=card_data["card_number"],
                parallel=card_data["parallel"],
                grade_company=card_data["grade_company"],
                grade_value=card_data["grade_value"],
                sport=card_data["sport"],
                is_rookie=(card_data["year"] >= 2020),
                image_url=f"https://i.ebayimg.com/images/g/placeholder/s-l500.jpg"  # Placeholder until real scraping
            )
            db.add(card)
            db.flush()
            
            # Generate sales with price variation AND historical data
            base_price = card_data["price"]
            price_trend = card_data["price_trend"]  # 1.25 = up 25%, 0.95 = down 5%
            sales_count = card_data["sales"]
            
            # Create sales over 14 days with price trend
            for i in range(sales_count):
                days_ago = random.randint(0, 14)
                
                # Price decreases as we go back in time (if trending up)
                # Price increases as we go back in time (if trending down)
                time_factor = 1 - (days_ago / 14 * (price_trend - 1))
                price_variation = random.uniform(0.90, 1.10)
                sale_price = base_price * time_factor * price_variation
                
                sale = Sale(
                    card_id=card.id,
                    sale_price=sale_price,
                    sale_date=datetime.now() - timedelta(days=days_ago),
                    ebay_item_id=f"sample_{card.id}_{i}",
                    graded=random.choice([True, False]),
                    grade_company="PSA" if random.random() > 0.5 else None,
                    grade_value=10.0 if random.random() > 0.7 else 9.0
                )
                db.add(sale)
            
            # Generate active listings (mix of above and below market)
            for i in range(random.randint(2, 5)):
                # 40% chance of below-market listing (arbitrage opportunity)
                if random.random() < 0.4:
                    listing_price = base_price * random.uniform(0.70, 0.95)  # 5-30% below market
                else:
                    listing_price = base_price * random.uniform(1.05, 1.25)  # 5-25% above market
                
                listing = ActiveListing(
                    card_id=card.id,
                    listing_price=listing_price,
                    listing_type="buy_it_now",
                    ebay_item_id=f"listing_{card.id}_{i}",
                    snapshot_date=date.today()
                )
                db.add(listing)
            
            print(f"✅ {idx}. {card_data['player']} - ${base_price} (trend: {price_trend:.2f}x, velocity: {card_data['velocity']})")
        
        db.commit()
        print(f"\n✅ Created {len(SAMPLE_CARDS)} cards with sales and listings\n")
        
        # Calculate trends
        print("📊 Calculating trends...")
        pipeline = DataPipeline()
        pipeline.calculate_trends()
        print("✅ Trends calculated\n")
        
        # Show top 10
        print("🔥 TOP 10 TRENDING CARDS:")
        print("=" * 80)
        trending = pipeline.get_trending_cards(limit=10)
        
        for i, card in enumerate(trending, 1):
            print(f"{i}. {card['player_name']} - {card['card_year']} {card['card_set']}")
            print(f"   💰 ${card['avg_price']:.2f} | 🔥 {card['hotness_score']:.1f} | 📈 {card['velocity_score']:.1f}")
            print()
        
        print("✅ Sample data generation complete!")
        print(f"📊 Total cards: {len(SAMPLE_CARDS)}")
        print("🎯 Mix includes: Green (BUY), Yellow (WATCH), White (SKIP)")
        print("💵 Price range: $18 - $8,500")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    generate_sample_data()
