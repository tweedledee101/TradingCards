"""
Configuration management for trading card platform
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend directory
backend_dir = Path(__file__).parent.parent
env_path = backend_dir / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    # eBay API Mode
    EBAY_USE_SANDBOX = os.getenv('EBAY_USE_SANDBOX', 'false').lower() == 'true'
    
    # Database (optional second target for dev replica — migrations + pipelines via env override)
    DATABASE_URL_DEV = os.getenv('DATABASE_URL_DEV', '').strip() or None

    DATABASE_URL = os.getenv('DATABASE_URL')
    if DATABASE_URL:
        # Use DATABASE_URL if provided (for Docker)
        database_url = DATABASE_URL
    else:
        # Build from individual components (for local dev)
        DB_HOST = os.getenv('DB_HOST', 'localhost')
        DB_PORT = os.getenv('DB_PORT', '5432')
        DB_NAME = os.getenv('DB_NAME', 'trading_cards')
        DB_USER = os.getenv('DB_USER', 'postgres')
        DB_PASSWORD = os.getenv('DB_PASSWORD', '')
        database_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # eBay API
    EBAY_APP_ID = os.getenv('EBAY_APP_ID')
    EBAY_CERT_ID = os.getenv('EBAY_CERT_ID')
    EBAY_DEV_ID = os.getenv('EBAY_DEV_ID')
    EBAY_TOKEN = os.getenv('EBAY_TOKEN')
    
    # Production credentials
    EBAY_CLIENT_ID = os.getenv('EBAY_CLIENT_ID', os.getenv('EBAY_APP_ID'))
    EBAY_CLIENT_SECRET = os.getenv('EBAY_CLIENT_SECRET', os.getenv('EBAY_CERT_ID'))
    
    # Sandbox credentials
    EBAY_SANDBOX_CLIENT_ID = os.getenv('EBAY_SANDBOX_CLIENT_ID')
    EBAY_SANDBOX_CLIENT_SECRET = os.getenv('EBAY_SANDBOX_CLIENT_SECRET')
    
    # Card Ladder (if they have API)
    CARD_LADDER_API_KEY = os.getenv('CARD_LADDER_API_KEY')
    
    # PSA
    PSA_BASE_URL = 'https://www.psacard.com/pop'
    
    # Social APIs
    TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
    REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
    REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
    
    # Cognito Auth (pool + client required for JWT verification; see backend/utils/auth.py)
    COGNITO_REGION = os.getenv('COGNITO_REGION', 'us-east-1')
    COGNITO_USER_POOL_ID = os.getenv('COGNITO_USER_POOL_ID', '')
    COGNITO_CLIENT_ID = os.getenv('COGNITO_CLIENT_ID', '')

    # Frontend (for redirect targets - Stripe onboarding, checkout success/cancel)
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'https://ragnarokgamez.com')

    # Stripe
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
    STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
    STRIPE_PLATFORM_FEE_CENTS = 100  # $1 per transaction

    # Scraping settings
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    REQUEST_DELAY = 2  # seconds between requests
    _scp_tmo = os.getenv('SCP_PAGE_LOAD_TIMEOUT', '60')
    try:
        SCP_PAGE_LOAD_TIMEOUT = max(15, min(180, int(_scp_tmo)))
    except ValueError:
        SCP_PAGE_LOAD_TIMEOUT = 60
    
    @property
    def get_database_url(self):
        return self.database_url

config = Config()
