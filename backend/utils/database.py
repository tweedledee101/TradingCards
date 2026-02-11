"""
Database connection and utilities
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.config.settings import config

engine = create_engine(config.database_url)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
