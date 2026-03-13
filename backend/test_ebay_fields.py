"""
Test script to see what fields eBay API actually returns
"""
import sys
from pathlib import Path
import json

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.scrapers.ebay_scraper import EbayScraper

scraper = EbayScraper()

# Make a simple search
print("Testing eBay API response structure...")
print("=" * 60)

try:
    import requests
    from backend.utils.token_manager import token_manager
    
    headers = {
        "Authorization": f"Bearer {token_manager.get_token()}",
        "Content-Type": "application/json"
    }
    
    params = {
        "q": "Wembanyama rookie",
        "limit": 1
    }
    
    response = requests.get(
        "https://api.ebay.com/buy/browse/v1/item_summary/search",
        headers=headers,
        params=params,
        timeout=30
    )
    
    # Handle 401 - refresh token
    if response.status_code == 401:
        print("Token expired, refreshing...")
        token_manager._refresh_token()
        headers["Authorization"] = f"Bearer {token_manager.get_token()}"
        response = requests.get(
            "https://api.ebay.com/buy/browse/v1/item_summary/search",
            headers=headers,
            params=params,
            timeout=30
        )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('itemSummaries'):
            item = data['itemSummaries'][0]
            print("\nFull item structure:")
            print(json.dumps(item, indent=2))
            
            print("\n" + "=" * 60)
            print("Available top-level fields:")
            for key in item.keys():
                print(f"  - {key}")
            
            # Check for player name fields
            print("\n" + "=" * 60)
            print("Checking for player name fields:")
            
            potential_fields = [
                'player', 'playerName', 'player_name',
                'additionalInfo', 'localizedAspects', 'aspects',
                'itemAffiliateWebUrl', 'categoryPath', 'categories'
            ]
            
            for field in potential_fields:
                if field in item:
                    print(f"  ✓ Found: {field}")
                    print(f"    Value: {item[field]}")
                else:
                    print(f"  ✗ Not found: {field}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
