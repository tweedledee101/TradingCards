"""
Test eBay API Connection
Quick test to verify credentials and API access
"""
from backend.scrapers.ebay_scraper import EbayScraper
from backend.utils.token_manager import token_manager

def test_connection():
    """Test eBay API with minimal call"""
    print("=" * 60)
    print("eBay API Connection Test")
    print("=" * 60)
    
    # Test token generation
    print("\n1. Testing Token Generation...")
    try:
        token = token_manager.get_token()
        print(f"✅ Token obtained: {token[:30]}...")
    except Exception as e:
        print(f"❌ Token generation failed: {e}")
        return False
    
    # Test API call (minimal - 1 call)
    print("\n2. Testing API Call (1 call)...")
    scraper = EbayScraper()
    
    try:
        # Single test query - limit to 1 result
        results = scraper.search_sold_listings("Wembanyama rookie", days_back=7)
        print(f"✅ API call successful")
        print(f"   Found {len(results)} results")
        
        if results:
            print(f"\n   Sample result:")
            print(f"   - Player: {results[0].get('player_name', 'N/A')}")
            print(f"   - Price: ${results[0].get('price', 0):.2f}")
            print(f"   - Year: {results[0].get('card_year', 'N/A')}")
            print(f"   - Set: {results[0].get('card_set', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ API call failed: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    print("\n" + "=" * 60)
    if success:
        print("✅ eBay API is working correctly")
    else:
        print("❌ eBay API connection failed - check credentials")
    print("=" * 60)
