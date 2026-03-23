"""
Shared fixtures for QA tests.
Sets up an in-memory SQLite database with realistic card data
so tests don't need PostgreSQL or real data.
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import create_engine, event, Text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import JSONB
from backend.models import (
    Base, Card, Sale, ActiveListing, MarketRate
)


@pytest.fixture
def db():
    """Create a fresh in-memory database for each test.
    
    Remaps PostgreSQL JSONB to Text so SQLite can handle it.
    """
    engine = create_engine("sqlite:///:memory:")

    # SQLite can't handle JSONB -- remap to Text at compile time
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        pass  # placeholder for future pragmas

    # Swap JSONB columns to Text for SQLite compatibility
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, JSONB):
                col.type = Text()

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_cards(db):
    """Insert realistic cards that mirror actual bugs we've hit"""
    cards = [
        # Griffey Bowman Chrome Impact Refractor -- was showing $267 instead of $98
        Card(
            id=1, player_name="Ken Griffey Jr", card_year=1999,
            card_set="Bowman Chrome", card_number="I20",
            parallel="Refractor", sport="Baseball"
        ),
        # Henderson Pink Foil Stadium Club -- was showing $10 instead of $2.37
        Card(
            id=2, player_name="Gunnar Henderson", card_year=2025,
            card_set="Stadium Club", card_number="96",
            parallel="Pink Foil", sport="Baseball"
        ),
        # Holliday Heritage Auto -- legit $92 opportunity at $70 BIN
        Card(
            id=3, player_name="Jackson Holliday", card_year=2025,
            card_set="Topps Heritage", card_number="ROA-JHO",
            parallel="Autograph", sport="Baseball"
        ),
        # Cheap base card -- should NOT show as opportunity (sub-$10 profit)
        Card(
            id=4, player_name="Dylan Crews", card_year=2025,
            card_set="Topps Heritage", card_number="76PI-15",
            parallel="Base", is_rookie=True, sport="Baseball"
        ),
        # Card with no card_number -- should not match SCP
        Card(
            id=5, player_name="Gunnar Henderson", card_year=2025,
            card_set="Stadium Club", card_number=None,
            parallel="Pink", sport="Baseball"
        ),
        # Auction-only opportunity
        Card(
            id=6, player_name="Roki Sasaki", card_year=2025,
            card_set="Bowman Chrome", card_number="12",
            parallel="Base", is_rookie=True, sport="Baseball"
        ),
        # Card where SCP rate is wildly off (3x+ sanity check)
        Card(
            id=7, player_name="Corbin Carroll", card_year=2023,
            card_set="Topps Series 2", card_number="401",
            parallel="Base", sport="Baseball"
        ),
    ]
    db.add_all(cards)
    db.commit()
    return cards


@pytest.fixture
def sample_sales(db, sample_cards):
    """Insert sales data for test cards"""
    now = datetime.now()
    sales = []

    # Griffey #I20 -- avg ~$100
    for i, price in enumerate([112.0, 100.0, 98.0, 105.0, 95.0]):
        sales.append(Sale(
            card_id=1, sale_price=price,
            sale_date=now - timedelta(days=i * 5),
            ebay_item_id=f"grif-{i}", source="ebay"
        ))

    # Henderson Pink Foil -- avg ~$2.50
    for i, price in enumerate([2.37, 2.50, 2.75, 2.25, 2.60]):
        sales.append(Sale(
            card_id=2, sale_price=price,
            sale_date=now - timedelta(days=i * 5),
            ebay_item_id=f"hend-{i}", source="ebay"
        ))

    # Holliday Auto -- avg ~$92
    for i, price in enumerate([50.0, 125.0, 102.50, 82.55, 80.99]):
        sales.append(Sale(
            card_id=3, sale_price=price,
            sale_date=now - timedelta(days=i * 7),
            ebay_item_id=f"holl-{i}", source="ebay"
        ))

    # Crews cheap base -- avg ~$1.50
    for i, price in enumerate([1.25, 1.50, 1.75, 1.50, 1.25]):
        sales.append(Sale(
            card_id=4, sale_price=price,
            sale_date=now - timedelta(days=i * 5),
            ebay_item_id=f"crew-{i}", source="ebay"
        ))

    # Sasaki -- avg ~$25
    for i, price in enumerate([22.0, 25.0, 28.0, 24.0, 26.0]):
        sales.append(Sale(
            card_id=6, sale_price=price,
            sale_date=now - timedelta(days=i * 5),
            ebay_item_id=f"sasa-{i}", source="ebay"
        ))

    # Carroll -- avg ~$1.00 (SCP will say $803 = sanity check fail)
    for i, price in enumerate([1.00, 0.99, 1.10, 0.95, 1.05]):
        sales.append(Sale(
            card_id=7, sale_price=price,
            sale_date=now - timedelta(days=i * 5),
            ebay_item_id=f"carr-{i}", source="ebay"
        ))

    db.add_all(sales)
    db.commit()
    return sales


@pytest.fixture
def sample_listings(db, sample_cards):
    """Insert active listings (BIN + auction)"""
    today = date.today()
    listings = [
        # Griffey -- BIN at $112
        ActiveListing(card_id=1, listing_price=112.0, listing_type="buy_it_now",
                      ebay_item_id="grif-bin-1", snapshot_date=today),
        ActiveListing(card_id=1, listing_price=124.99, listing_type="buy_it_now",
                      ebay_item_id="grif-bin-2", snapshot_date=today),

        # Henderson Pink Foil -- BIN at $3.50 (above market, no profit)
        ActiveListing(card_id=2, listing_price=3.50, listing_type="buy_it_now",
                      ebay_item_id="hend-bin-1", snapshot_date=today),

        # Holliday Auto -- BIN at $70 (below $92 market)
        ActiveListing(card_id=3, listing_price=70.0, listing_type="buy_it_now",
                      ebay_item_id="holl-bin-1", snapshot_date=today),
        ActiveListing(card_id=3, listing_price=45.0, listing_type="auction",
                      ebay_item_id="holl-auc-1", snapshot_date=today),

        # Crews cheap -- BIN at $1.99 (sub-$10 profit)
        ActiveListing(card_id=4, listing_price=1.99, listing_type="buy_it_now",
                      ebay_item_id="crew-bin-1", snapshot_date=today),
        ActiveListing(card_id=4, listing_price=1.25, listing_type="auction",
                      ebay_item_id="crew-auc-1", snapshot_date=today),

        # Sasaki -- auction only at $5 (potential $20 profit)
        ActiveListing(card_id=6, listing_price=5.0, listing_type="auction",
                      ebay_item_id="sasa-auc-1", snapshot_date=today),

        # Carroll -- BIN at $0.99
        ActiveListing(card_id=7, listing_price=0.99, listing_type="buy_it_now",
                      ebay_item_id="carr-bin-1", snapshot_date=today),
    ]
    db.add_all(listings)
    db.commit()
    return listings


@pytest.fixture
def sample_market_rates(db, sample_cards):
    """Insert SCP market rates -- including known bad ones for sanity check tests"""
    today = date.today()
    rates = [
        # Griffey -- correct rate $98.57
        MarketRate(card_id=1, source="sportscardspro", ungraded_price=98.57,
                   grade_9_price=196.50, psa_10_price=449.72, date_recorded=today,
                   scp_product_url="https://www.sportscardspro.com/game/baseball-cards-1999-bowman-chrome-impact/ken-griffey-jr-refractor-i20"),

        # Henderson Pink Foil -- correct rate $2.37
        MarketRate(card_id=2, source="sportscardspro", ungraded_price=2.37,
                   grade_9_price=None, psa_10_price=None, date_recorded=today,
                   scp_product_url="https://www.sportscardspro.com/game/baseball-cards-2025-stadium-club/gunnar-henderson-pink-96"),

        # Holliday Auto -- correct rate $92.53
        MarketRate(card_id=3, source="sportscardspro", ungraded_price=92.53,
                   grade_9_price=177.48, psa_10_price=265.0, date_recorded=today,
                   scp_product_url="https://www.sportscardspro.com/game/baseball-cards-2025-topps-heritage-real-one-autograph/jackson-holliday-roa-jho"),

        # Crews cheap -- correct rate $1.92
        MarketRate(card_id=4, source="sportscardspro", ungraded_price=1.92,
                   grade_9_price=7.0, psa_10_price=36.48, date_recorded=today),

        # Sasaki -- correct rate $25.00
        MarketRate(card_id=6, source="sportscardspro", ungraded_price=25.0,
                   grade_9_price=45.0, psa_10_price=120.0, date_recorded=today),

        # Carroll -- BAD rate $803.93 (should be ~$1.00, sanity check should catch)
        MarketRate(card_id=7, source="sportscardspro", ungraded_price=803.93,
                   grade_9_price=None, psa_10_price=None, date_recorded=today),
    ]
    db.add_all(rates)
    db.commit()
    return rates


@pytest.fixture
def full_test_data(db, sample_cards, sample_sales, sample_listings, sample_market_rates):
    """Convenience fixture that loads everything"""
    return {
        "cards": sample_cards,
        "sales": sample_sales,
        "listings": sample_listings,
        "rates": sample_market_rates,
    }
