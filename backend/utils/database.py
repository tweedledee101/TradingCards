"""
Database connection and utilities
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.config.settings import config

# pool_pre_ping: reconnect if RDS dropped an idle connection (e.g. long eBay 429 sleeps in pipelines).
# pool_recycle: proactively recycle before typical RDS / network idle caps.
engine = create_engine(
    config.get_database_url,
    pool_pre_ping=True,
    pool_recycle=280,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db():
    """FastAPI dependency for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    from backend.models import Base
    Base.metadata.create_all(bind=engine)
