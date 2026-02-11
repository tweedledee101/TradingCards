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
    is_rookie = Column(Boolean, default=False)
    sport = Column(String(50))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    sales = relationship("Sale", back_populates="card")
    active_listings = relationship("ActiveListing", back_populates="card")
    price_trends = relationship("PriceTrend", back_populates="card")


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


class SocialSignal(Base):
    __tablename__ = 'social_signals'
    
    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey('cards.id'))
    platform = Column(String(50))
    mention_count = Column(Integer, default=0)
    sentiment_score = Column(DECIMAL(3, 2))
    signal_date = Column(Date, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
