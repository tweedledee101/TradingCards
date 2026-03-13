"""Test eBay Item API for player names"""
import sys
from pathlib import Path
import json

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.utils.token_manager import token_manager
import requests

# Item ID from previous test
item_id = "v1|188049932459|0"

headers = {
    "Authorization": f"Bearer {token_manager.get_token()}",
    "Content-Type": "application/json"
}

print(f"Testing Item API with ID: {item_id}")
print("=" * 60)

try:
    response = requests.get(
        f"https://api.ebay.com/buy/browse/v1/item/{item_id}",
        headers=headers,
        timeout=30
    )
    
    if response.status_code == 401:
        print("Token expired, refreshing...")
        token_manager._refresh_token()
        headers["Authorization"] = f"Bearer {token_manager.get_token()}"
        response = requests.get(
            f"https://api.ebay.com/buy/browse/v1/item/{item_id}",
            headers=headers,
            timeout=30
        )
    
    print(f"Status: {response.status_code}\n")
    
    if response.status_code == 200:
        data = response.json()
        
        # Check for localizedAspects
        if 'localizedAspects' in data:
            print("Found localizedAspects:")
            print(json.dumps(data['localizedAspects'], indent=2))
            
            # Look for player name
            for aspect in data['localizedAspects']:
                if aspect.get('name') in ['Player', 'Player/Athlete', 'Athlete', 'Player Name']:
                    print(f"\nPLAYER FOUND: {aspect.get('value')}")
        else:
            print("No localizedAspects field")
            print("\nAvailable fields:")
            for key in data.keys():
                print(f"  - {key}")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
