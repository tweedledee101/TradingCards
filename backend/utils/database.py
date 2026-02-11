"""
Database connection and utilities
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.config.settings import config

engine = create_engine(config.database_url)
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
