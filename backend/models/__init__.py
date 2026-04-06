"""
SQLAlchemy ORM Models
"""
from sqlalchemy import Column, Integer, String, Boolean, DECIMAL, TIMESTAMP, Date, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Account(Base):
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    account_type = Column(String(20), nullable=False, default='individual')
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())

    users = relationship("User", back_populates="account")


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    cognito_sub = Column(String(128), unique=True)
    email = Column(String(255), nullable=False, unique=True)
    display_name = Column(String(255))
    role = Column(String(20), nullable=False, default='owner')
    is_active = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())

    account = relationship("Account", back_populates="users")


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
    listing_title = Column(Text)
    listing_url = Column(Text)
    
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
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False, default=1)
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
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False, default=1)
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
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False, default=1)
    card_id = Column(Integer, ForeignKey('cards.id'))
    target_price = Column(DECIMAL(10, 2))
    alert_threshold = Column(DECIMAL(5, 2))
    notes = Column(Text)
    added_at = Column(TIMESTAMP, server_default=func.now())
    
    card = relationship("Card", back_populates="watchlist")


class JobRun(Base):
    """Tracks background job execution state"""
    __tablename__ = 'job_runs'

    id = Column(Integer, primary_key=True)
    job_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default='running')
    started_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    completed_at = Column(TIMESTAMP)
    items_processed = Column(Integer, default=0)
    items_total = Column(Integer)
    error_message = Column(Text)
    parameters = Column(Text)      # JSON string
    results_summary = Column(Text)  # JSON string
    created_at = Column(TIMESTAMP, server_default=func.now())


class Opportunity(Base):
    """Pipeline-discovered arbitrage opportunities"""
    __tablename__ = 'opportunities'

    id = Column(Integer, primary_key=True)
    player_name = Column(String(255), nullable=False)
    card_year = Column(Integer)
    card_set = Column(String(255))
    card_number = Column(String(50))
    parallel = Column(String(100))
    scp_title = Column(Text)
    scp_price = Column(DECIMAL(10, 2), nullable=False)
    buy_price = Column(DECIMAL(10, 2), nullable=False)
    profit = Column(DECIMAL(10, 2), nullable=False)
    roi = Column(DECIMAL(8, 2), nullable=False)
    ebay_title = Column(Text)
    ebay_url = Column(Text)
    ebay_item_id = Column(String(50))
    image_url = Column(Text)
    listing_image_urls = Column(JSONB)
    scp_url = Column(Text)
    scp_grade_9 = Column(DECIMAL(10, 2))
    scp_psa_10 = Column(DECIMAL(10, 2))
    listing_type = Column(String(20), default='buy_it_now')
    shipping = Column(DECIMAL(10, 2), default=0)
    bid_count = Column(Integer, default=0)
    end_time = Column(TIMESTAMP)
    scp_volume = Column(Text)
    flagged = Column(Boolean, default=False)
    qa_status = Column(String(20), default='pending')
    qa_flags = Column(JSONB, default=[])
    qa_reviewed_at = Column(TIMESTAMP)
    verification_status = Column(String(32), nullable=False, default='pending')
    verification_detail = Column(JSONB)
    price_source = Column(String(20), default='scp')
    scan_id = Column(Integer, ForeignKey('job_runs.id'))
    created_at = Column(TIMESTAMP, server_default=func.now())


class SCPCache(Base):
    """Caches SCP Selenium search results to avoid re-scraping"""
    __tablename__ = 'scp_cache'

    id = Column(Integer, primary_key=True)
    player_name = Column(String(255), nullable=False)
    card_year = Column(Integer)
    card_number = Column(String(50), nullable=False)
    search_query = Column(Text)
    variants = Column(JSONB, nullable=False, default=[])
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())


class SoldComp(Base):
    """130point eBay sold data cache -- actual completed sale prices"""
    __tablename__ = 'sold_comps'

    id = Column(Integer, primary_key=True)
    player_name = Column(String(255), nullable=False)
    card_year = Column(Integer)
    card_set = Column(String(255))
    card_number = Column(String(50))
    parallel = Column(String(100))
    sale_price = Column(DECIMAL(10, 2), nullable=False)
    sale_type = Column(String(20))
    sale_date = Column(String(50))
    listing_title = Column(Text)
    source = Column(String(50), default='130point')
    search_query = Column(Text)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())


class ErrorLog(Base):
    """Runtime error and event log for observability"""
    __tablename__ = 'error_log'

    id = Column(Integer, primary_key=True)
    timestamp = Column(TIMESTAMP, nullable=False, server_default=func.now())
    level = Column(String(10), nullable=False, default='ERROR')
    category = Column(String(50))
    source = Column(String(100))
    message = Column(Text, nullable=False)
    context = Column(JSONB)
    request_id = Column(String(36))
    stack_trace = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())


class ScheduledBid(Base):
    """Snipe queue -- scheduled bids for auctions"""
    __tablename__ = 'scheduled_bids'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False, default=1)
    player_name = Column(String(255), nullable=False)
    card_year = Column(Integer)
    card_set = Column(String(255))
    card_number = Column(String(50))
    parallel = Column(String(100))
    max_bid = Column(DECIMAL(10, 2), nullable=False)
    snipe_seconds = Column(Integer, nullable=False, default=10)
    ebay_item_id = Column(String(50))
    ebay_url = Column(Text)
    image_url = Column(Text)
    scp_price = Column(DECIMAL(10, 2))
    end_time = Column(TIMESTAMP)
    status = Column(String(20), nullable=False, default='scheduled')
    notes = Column(Text)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())


class BusinessGoal(Base):
    """Annual business goals and constraints"""
    __tablename__ = 'business_goals'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False, default=1)
    annual_income_target = Column(DECIMAL(10, 2), nullable=False)
    starting_capital = Column(DECIMAL(10, 2), nullable=False)
    weekly_hours_weekday = Column(DECIMAL(4, 1), default=12.5)
    weekly_hours_weekend = Column(DECIMAL(4, 1), default=8.0)
    target_margin_pct = Column(DECIMAL(5, 2), default=0.25)
    avg_shipping_cost = Column(DECIMAL(6, 2), default=4.50)
    platform_fee_pct = Column(DECIMAL(5, 2), default=0.13)
    reinvest_pct = Column(DECIMAL(5, 2), default=1.00)
    goal_start_date = Column(Date, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class DailySnapshot(Base):
    """End-of-day business state capture"""
    __tablename__ = 'daily_snapshots'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False, default=1)
    snapshot_date = Column(Date, nullable=False)
    available_capital = Column(DECIMAL(10, 2))
    inventory_count = Column(Integer, default=0)
    inventory_cost_basis = Column(DECIMAL(10, 2), default=0)
    inventory_market_value = Column(DECIMAL(10, 2), default=0)
    listed_count = Column(Integer, default=0)
    unlisted_count = Column(Integer, default=0)
    revenue_today = Column(DECIMAL(10, 2), default=0)
    profit_today = Column(DECIMAL(10, 2), default=0)
    revenue_mtd = Column(DECIMAL(10, 2), default=0)
    profit_mtd = Column(DECIMAL(10, 2), default=0)
    revenue_ytd = Column(DECIMAL(10, 2), default=0)
    profit_ytd = Column(DECIMAL(10, 2), default=0)
    cards_bought_today = Column(Integer, default=0)
    cards_sold_today = Column(Integer, default=0)
    cards_listed_today = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())


class DailyPlan(Base):
    """Generated daily action plan"""
    __tablename__ = 'daily_plans'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False, default=1)
    plan_date = Column(Date, nullable=False)
    available_hours = Column(DECIMAL(4, 1))
    target_revenue = Column(DECIMAL(10, 2))
    target_profit = Column(DECIMAL(10, 2))
    buy_budget = Column(DECIMAL(10, 2))
    status = Column(String(20), default='pending')
    actions = Column(JSONB, default=[])
    results = Column(JSONB)
    created_at = Column(TIMESTAMP, server_default=func.now())


class CapitalTransaction(Base):
    """Tracks every capital movement: buys, sells, deposits, withdrawals"""
    __tablename__ = 'capital_transactions'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False, default=1)
    transaction_date = Column(Date, nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    type = Column(String(20), nullable=False)  # deposit, withdrawal, purchase, sale
    description = Column(Text)
    opportunity_id = Column(Integer, ForeignKey('opportunities.id'))
    inventory_id = Column(Integer, ForeignKey('inventory.id'))
    created_at = Column(TIMESTAMP, server_default=func.now())


class MarketRate(Base):
    """Market rates from SportsCardsPro (Ungraded, Grade 9, PSA 10)"""
    __tablename__ = 'market_rates'
    
    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey('cards.id', ondelete='CASCADE'))
    source = Column(String(50), nullable=False, default='sportscardspro')
    ungraded_price = Column(DECIMAL(10, 2))
    grade_9_price = Column(DECIMAL(10, 2))
    psa_10_price = Column(DECIMAL(10, 2))
    scp_product_url = Column(Text)
    date_recorded = Column(Date, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
