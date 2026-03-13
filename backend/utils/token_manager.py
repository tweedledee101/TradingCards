"""
eBay Token Auto-Refresh
Automatically refreshes expired tokens before API calls
"""
import requests
import base64
from datetime import datetime, timedelta
from backend.config.settings import config


class TokenManager:
    """Manages eBay OAuth token lifecycle"""
    
    def __init__(self):
        self.token = None
        self.expires_at = None
        
        # Use sandbox or production credentials
        if config.EBAY_USE_SANDBOX:
            self.client_id = config.EBAY_SANDBOX_CLIENT_ID
            self.client_secret = config.EBAY_SANDBOX_CLIENT_SECRET
        else:
            self.client_id = config.EBAY_CLIENT_ID
            self.client_secret = config.EBAY_CLIENT_SECRET
    
    def get_token(self):
        """Get valid token, refresh if expired"""
        if self._is_expired():
            self._refresh_token()
        return self.token
    
    def _is_expired(self):
        """Check if token is expired or about to expire"""
        if not self.token:
            return True  # No token yet, need to generate
        
        if not self.expires_at:
            return True  # No expiry set, need to refresh
        
        # Refresh 5 minutes before expiry
        return datetime.now() >= (self.expires_at - timedelta(minutes=5))
    
    def _refresh_token(self):
        """Generate new Application Token"""
        mode = "SANDBOX" if config.EBAY_USE_SANDBOX else "PRODUCTION"
        print(f"🔄 Refreshing eBay token ({mode})...")
        print(f"   Client ID: {self.client_id[:20]}...")
        print(f"   Client Secret: {self.client_secret[:10]}...")
        
        # Use sandbox or production token URL
        if config.EBAY_USE_SANDBOX:
            token_url = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
        else:
            token_url = "https://api.ebay.com/identity/v1/oauth2/token"
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded}"
        }
        
        data = {
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope"
        }
        
        try:
            print(f"   POST {token_url}")
            response = requests.post(token_url, headers=headers, data=data, timeout=10)
            print(f"   Response: {response.status_code}")
            if response.status_code != 200:
                print(f"   Error body: {response.text}")
            response.raise_for_status()
            
            token_data = response.json()
            self.token = token_data['access_token']
            expires_in = token_data['expires_in']
            self.expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            print(f"✅ Token refreshed (expires in {expires_in/3600:.1f} hours)")
            
            # Update config for other parts of app
            config.EBAY_TOKEN = self.token
            
        except Exception as e:
            print(f"❌ Token refresh failed: {e}")
            raise


# Global token manager
token_manager = TokenManager()
