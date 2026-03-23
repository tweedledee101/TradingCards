"""
Integration tests for database operations
Tests actual database connections, queries, and data flow
"""
import pytest
from datetime import datetime, date
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from tests.fixtures.sample_data import SAMPLE_CARDS, SAMPLE_SALES, SAMPLE_ACTIVE_LISTINGS


@pytest.fixture(scope='module')
def test_db():
    """
    Create test database connection
    Uses DATABASE_URL env var if set, falls back to local test DB
    """
    import os
    db_url = os.getenv('DATABASE_URL', 'postgresql://carduser:password@localhost/trading_cards_test')
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()
    engine.dispose()


@pytest.fixture(scope='function')
def clean_db(test_db):
    """Clean database before each test"""
    # Delete in correct order due to foreign keys
    test_db.execute(text("DELETE FROM social_signals"))
    test_db.execute(text("DELETE FROM psa_population"))
    test_db.execute(text("DELETE FROM price_trends"))
    test_db.execute(text("DELETE FROM active_listings"))
    test_db.execute(text("DELETE FROM sales"))
    test_db.execute(text("DELETE FROM cards"))
    test_db.commit()
    
    yield test_db


class TestDatabaseSchema:
    """Test database schema and constraints"""
    
    @pytest.mark.integration
    def test_tables_exist(self, test_db):
        """Verify all required tables exist"""
        result = test_db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        tables = [row[0] for row in result]
        
        required_tables = [
            'cards', 'sales', 'active_listings', 
            'price_trends', 'psa_population', 'social_signals'
        ]
        
        for table in required_tables:
            assert table in tables, f"Table {table} not found"
    
    @pytest.mark.integration
    def test_indexes_exist(self, test_db):
        """Verify performance indexes are created"""
        result = test_db.execute(text("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = 'public'
        """))
        indexes = [row[0] for row in result]
        
        expected_indexes = [
            'idx_sales_card_date',
            'idx_sales_date',
            'idx_cards_rookie',
            'idx_price_trends_date',
            'idx_price_trends_hotness'
        ]
        
        for index in expected_indexes:
            assert index in indexes, f"Index {index} not found"


class TestCardOperations:
    """Test CRUD operations on cards table"""
    
    @pytest.mark.integration
    def test_insert_card(self, clean_db):
        """Test inserting a new card"""
        clean_db.execute(text("""
            INSERT INTO cards (player_name, card_year, card_set, card_number, is_rookie, sport)
            VALUES (:name, :year, :set, :number, :rookie, :sport)
        """), {
            'name': 'Victor Wembanyama',
            'year': 2023,
            'set': 'Prizm',
            'number': '1',
            'rookie': True,
            'sport': 'Basketball'
        })
        clean_db.commit()
        
        result = clean_db.execute(text("SELECT * FROM cards WHERE player_name = 'Victor Wembanyama'"))
        card = result.fetchone()
        
        assert card is not None
        assert card[1] == 'Victor Wembanyama'  # player_name
        assert card[2] == 2023  # card_year
        assert card[5] is True  # is_rookie
    
    @pytest.mark.integration
    def test_unique_constraint(self, clean_db):
        """Test unique constraint on cards table"""
        insert_sql = text("""
            INSERT INTO cards (player_name, card_year, card_set, card_number, is_rookie, sport, parallel, grade_company, grade_value)
            VALUES (:name, :year, :set, :number, :rookie, :sport, :parallel, :grade_company, :grade_value)
        """)
        
        params = {
            'name': 'Test Player',
            'year': 2023,
            'set': 'Prizm',
            'number': '1',
            'rookie': True,
            'sport': 'Basketball',
            'parallel': 'Base',
            'grade_company': 'PSA',
            'grade_value': 10.0
        }
        
        # First insert should succeed
        clean_db.execute(insert_sql, params)
        clean_db.commit()
        
        # Second insert with same values should fail
        with pytest.raises(Exception):  # IntegrityError
            clean_db.execute(insert_sql, params)
            clean_db.commit()
        
        clean_db.rollback()


class TestSalesOperations:
    """Test sales data operations"""
    
    @pytest.mark.integration
    def test_insert_sale(self, clean_db):
        """Test inserting a sale record"""
        # First insert a card
        clean_db.execute(text("""
            INSERT INTO cards (id, player_name, card_year, is_rookie, sport)
            VALUES (1, 'Test Player', 2023, true, 'Basketball')
        """))
        
        # Then insert a sale
        clean_db.execute(text("""
            INSERT INTO sales (card_id, sale_price, sale_date, ebay_item_id, graded, grade_company, grade_value)
            VALUES (:card_id, :price, :date, :item_id, :graded, :company, :grade)
        """), {
            'card_id': 1,
            'price': 450.00,
            'date': datetime.now(),
            'item_id': '123456789',
            'graded': True,
            'company': 'PSA',
            'grade': 10.0
        })
        clean_db.commit()
        
        result = clean_db.execute(text("SELECT * FROM sales WHERE card_id = 1"))
        sale = result.fetchone()
        
        assert sale is not None
        assert float(sale[2]) == 450.00  # sale_price
        assert sale[7] is True  # graded
    
    @pytest.mark.integration
    def test_foreign_key_constraint(self, clean_db):
        """Test foreign key constraint on card_id"""
        with pytest.raises(Exception):  # ForeignKeyViolation
            clean_db.execute(text("""
                INSERT INTO sales (card_id, sale_price, sale_date, ebay_item_id)
                VALUES (999, 100.00, NOW(), 'test123')
            """))
            clean_db.commit()
        
        clean_db.rollback()
    
    @pytest.mark.integration
    def test_unique_ebay_item_id(self, clean_db):
        """Test unique constraint on ebay_item_id"""
        # Insert card
        clean_db.execute(text("""
            INSERT INTO cards (id, player_name, card_year, is_rookie, sport)
            VALUES (1, 'Test Player', 2023, true, 'Basketball')
        """))
        
        # First sale
        clean_db.execute(text("""
            INSERT INTO sales (card_id, sale_price, sale_date, ebay_item_id)
            VALUES (1, 100.00, NOW(), 'duplicate123')
        """))
        clean_db.commit()
        
        # Duplicate ebay_item_id should fail
        with pytest.raises(Exception):
            clean_db.execute(text("""
                INSERT INTO sales (card_id, sale_price, sale_date, ebay_item_id)
                VALUES (1, 200.00, NOW(), 'duplicate123')
            """))
            clean_db.commit()
        
        clean_db.rollback()


class TestDataFlow:
    """Test complete data flow from scraper to database"""
    
    @pytest.mark.integration
    def test_complete_sale_insertion_flow(self, clean_db):
        """Test inserting card and sales in correct order"""
        # Step 1: Insert card
        clean_db.execute(text("""
            INSERT INTO cards (id, player_name, card_year, card_set, is_rookie, sport)
            VALUES (1, 'Victor Wembanyama', 2023, 'Prizm', true, 'Basketball')
        """))
        
        # Step 2: Insert multiple sales
        for i, sale in enumerate(SAMPLE_SALES, 1):
            clean_db.execute(text("""
                INSERT INTO sales (card_id, sale_price, sale_date, ebay_item_id, graded, grade_company, grade_value)
                VALUES (:card_id, :price, :date, :item_id, :graded, :company, :grade)
            """), {
                'card_id': 1,
                'price': sale['sale_price'],
                'date': sale['sale_date'],
                'item_id': sale['ebay_item_id'],
                'graded': sale['graded'],
                'company': sale['grade_company'],
                'grade': sale['grade_value']
            })
        
        # Step 3: Insert active listings
        for listing in SAMPLE_ACTIVE_LISTINGS:
            clean_db.execute(text("""
                INSERT INTO active_listings (card_id, listing_price, listing_type, snapshot_date, ebay_item_id)
                VALUES (:card_id, :price, :type, :date, :item_id)
            """), {
                'card_id': 1,
                'price': listing['listing_price'],
                'type': listing['listing_type'],
                'date': listing['snapshot_date'],
                'item_id': f"active_{listing['id']}"
            })
        
        clean_db.commit()
        
        # Verify data
        sales_count = clean_db.execute(text("SELECT COUNT(*) FROM sales WHERE card_id = 1")).scalar()
        listings_count = clean_db.execute(text("SELECT COUNT(*) FROM active_listings WHERE card_id = 1")).scalar()
        
        assert sales_count == 3
        assert listings_count == 2
    
    @pytest.mark.integration
    def test_calculate_velocity_score(self, clean_db):
        """Test velocity score calculation from real data"""
        # Setup data
        clean_db.execute(text("""
            INSERT INTO cards (id, player_name, card_year, is_rookie, sport)
            VALUES (1, 'Test Player', 2023, true, 'Basketball')
        """))
        
        # 5 sales
        for i in range(5):
            clean_db.execute(text("""
                INSERT INTO sales (card_id, sale_price, sale_date, ebay_item_id)
                VALUES (1, 100.00, NOW(), :item_id)
            """), {'item_id': f'sale_{i}'})
        
        # 2 active listings
        for i in range(2):
            clean_db.execute(text("""
                INSERT INTO active_listings (card_id, listing_price, listing_type, snapshot_date, ebay_item_id)
                VALUES (1, 100.00, 'buy_it_now', CURRENT_DATE, :item_id)
            """), {'item_id': f'listing_{i}'})
        
        clean_db.commit()
        
        # Calculate velocity
        result = clean_db.execute(text("""
            SELECT 
                (SELECT COUNT(*) FROM sales WHERE card_id = 1)::float /
                NULLIF((SELECT COUNT(*) FROM active_listings WHERE card_id = 1), 0) as velocity
        """))
        velocity = result.scalar()
        
        assert velocity == 2.5  # 5 sales / 2 listings


class TestPriceTrends:
    """Test price trends calculations"""
    
    @pytest.mark.integration
    def test_insert_price_trend(self, clean_db):
        """Test inserting computed price trends"""
        # Insert card
        clean_db.execute(text("""
            INSERT INTO cards (id, player_name, card_year, is_rookie, sport)
            VALUES (1, 'Test Player', 2023, true, 'Basketball')
        """))
        
        # Insert price trend
        clean_db.execute(text("""
            INSERT INTO price_trends (
                card_id, trend_date, avg_price, median_price, 
                sales_count, velocity_score, hotness_score
            )
            VALUES (1, CURRENT_DATE, 450.00, 450.00, 10, 2.5, 75.5)
        """))
        clean_db.commit()
        
        result = clean_db.execute(text("SELECT * FROM price_trends WHERE card_id = 1"))
        trend = result.fetchone()
        
        assert trend is not None
        assert float(trend[3]) == 450.00  # avg_price
        assert float(trend[8]) == 2.5  # velocity_score
    
    @pytest.mark.integration
    def test_unique_card_date_constraint(self, clean_db):
        """Test unique constraint on (card_id, trend_date)"""
        clean_db.execute(text("""
            INSERT INTO cards (id, player_name, card_year, is_rookie, sport)
            VALUES (1, 'Test Player', 2023, true, 'Basketball')
        """))
        
        # First trend
        clean_db.execute(text("""
            INSERT INTO price_trends (card_id, trend_date, avg_price, sales_count)
            VALUES (1, CURRENT_DATE, 100.00, 5)
        """))
        clean_db.commit()
        
        # Duplicate should fail
        with pytest.raises(Exception):
            clean_db.execute(text("""
                INSERT INTO price_trends (card_id, trend_date, avg_price, sales_count)
                VALUES (1, CURRENT_DATE, 200.00, 10)
            """))
            clean_db.commit()
        
        clean_db.rollback()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
