"""
SQLAlchemy ORM Models
"""
from sqlalchemy import Column, Integer, String, Boolean, DECIMAL, TIMESTAMP, Date, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Card(Base):
    __tablename__ = 'cards'
    
    id = Column(Integer, primary_key=True)
    player_name = Column(String(255), nullable=False)
    card_year = Column(Integer, nullable=False)
    card_set = Column(String(255))
    card_number = Column(String(50))
    parallel = Column(String(100))
    grade_company = Column(String(20))
    grade_value = Column(DECIMAL(3, 1))
    image_url = Column(String(500))
    ungraded_price = Column(DECIMAL(10, 2))
    ebay_search_url = Column(Text)
    is_rookie = Column(Boolean, default=False)
    sport = Column(String(50))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    sales = relationship("Sale", back_populates="card")
    active_listings = relationship("ActiveListing", back_populates="card")
    price_trends = relationship("PriceTrend", back_populates="card")
    inventory = relationship("Inventory", back_populates="card")
    watchlist = relationship("Watchlist", back_populates="card")


class Sale(Base):
    __tablename__ = 'sales'
    
    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey('cards.id'))
    sale_price = Column(DECIMAL(10, 2), nullable=False)
    sale_date = Column(TIMESTAMP, nullable=False)
    listing_title = Column(Text)
    ebay_item_id = Column(String(50), unique=True)
    condition = Column(String(50))
    graded = Column(Boolean, default=False)
    grade_company = Column(String(20))
    grade_value = Column(DECIMAL(3, 1))
    source = Column(String(50), default='ebay')
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    card = relationship("Card", back_populates="sales")


class ActiveListing(Base):
    __tablename__ = 'active_listings'
    
    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey('cards.id'))
    listing_price = Column(DECIMAL(10, 2), nullable=False)
    listing_type = Column(String(20))
    ebay_item_id = Column(String(50), unique=True)
    snapshot_date = Column(Date, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    card = relationship("Card", back_populates="active_listings")


class PriceTrend(Base):
    __tablename__ = 'price_trends'
    
    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey('cards.id'))
    trend_date = Column(Date, nullable=False)
    avg_price = Column(DECIMAL(10, 2))
    median_price = Column(DECIMAL(10, 2))
    sales_count = Column(Integer, default=0)
    active_listings_count = Column(Integer, default=0)
    price_change_7d = Column(DECIMAL(5, 2))
    price_change_30d = Column(DECIMAL(5, 2))
    velocity_score = Column(DECIMAL(5, 2))
    momentum_score = Column(DECIMAL(5, 2))
    hotness_score = Column(DECIMAL(5, 2))
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    card = relationship("Card", back_populates="price_trends")


class PSAPopulation(Base):
    __tablename__ = 'psa_population'
    
    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey('cards.id'))
    grade_value = Column(DECIMAL(3, 1), nullable=False)
    population_count = Column(Integer, nullable=False)
    snapshot_date = Column(Date, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class GradingPopulation(Base):
    """New table for aggregated PSA grading data from NovaAct"""
    __tablename__ = 'grading_population'
    
    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey('cards.id'))
    grade_company = Column(String(10), nullable=False, default='PSA')
    psa_10_count = Column(Integer, default=0)
    psa_9_count = Column(Integer, default=0)
    psa_8_count = Column(Integer, default=0)
    total_graded = Column(Integer, default=0)
    psa_10_rate = Column(DECIMAL(5, 4))  # 0.2250 = 22.5%
    date_recorded = Column(Date, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class PriceBenchmark(Base):
    """Price benchmark data from Card Ladder, 130point, etc."""
    __tablename__ = 'price_benchmarks'
    
    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey('cards.id'))
    source = Column(String(50), nullable=False)  # 'cardladder', '130point'
    current_price = Column(DECIMAL(10, 2))
    price_7d_ago = Column(DECIMAL(10, 2))
    price_30d_ago = Column(DECIMAL(10, 2))
    change_7d = Column(DECIMAL(5, 2))  # Percentage
    change_30d = Column(DECIMAL(5, 2))
    velocity_rating = Column(String(20))  # 'Hot', 'Warm', 'Cold', 'Stable'
    market_cap = Column(DECIMAL(12, 2))
    date_recorded = Column(Date, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class SocialSignal(Base):
    __tablename__ = 'social_signals'
    
    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey('cards.id'))
    platform = Column(String(50))
    mention_count = Column(Integer, default=0)
    sentiment_score = Column(DECIMAL(3, 2))
    signal_date = Column(Date, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class Inventory(Base):
    __tablename__ = 'inventory'
    
    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey('cards.id'))
    purchase_date = Column(Date, nullable=False)
    purchase_price = Column(DECIMAL(10, 2), nullable=False)
    purchase_source = Column(String(100))
    quantity = Column(Integer, default=1)
    condition = Column(String(50))
    graded = Column(Boolean, default=False)
    grade_company = Column(String(20))
    grade_value = Column(DECIMAL(3, 1))
    storage_location = Column(String(100))
    notes = Column(Text)
    status = Column(String(20), default='owned')
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    card = relationship("Card", back_populates="inventory")
    sales = relationship("InventorySale", back_populates="inventory_item")


class InventorySale(Base):
    __tablename__ = 'inventory_sales'
    
    id = Column(Integer, primary_key=True)
    inventory_id = Column(Integer, ForeignKey('inventory.id'))
    sale_date = Column(Date, nullable=False)
    sale_price = Column(DECIMAL(10, 2), nullable=False)
    sale_platform = Column(String(100))
    fees = Column(DECIMAL(10, 2), default=0)
    shipping_cost = Column(DECIMAL(10, 2), default=0)
    net_profit = Column(DECIMAL(10, 2))
    roi_percentage = Column(DECIMAL(5, 2))
    notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    inventory_item = relationship("Inventory", back_populates="sales")


class Watchlist(Base):
    __tablename__ = 'watchlist'
    
    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey('cards.id'))
    target_price = Column(DECIMAL(10, 2))
    alert_threshold = Column(DECIMAL(5, 2))
    notes = Column(Text)
    added_at = Column(TIMESTAMP, server_default=func.now())
    
    card = relationship("Card", back_populates="watchlist")
