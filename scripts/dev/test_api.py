"""
Quick API test script
Tests all endpoints with sample data
"""
import requests
import time

BASE_URL = "http://localhost:8000"

def test_api():
    print("🧪 Testing Trading Card API\n")
    
    # Test health check
    print("1. Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print(f"   ✅ Health check passed: {response.json()['status']}\n")
        else:
            print(f"   ❌ Health check failed: {response.status_code}\n")
            return
    except requests.exceptions.ConnectionError:
        print("   ❌ Cannot connect to API. Is it running?")
        print("   Start with: python -m backend.api.run\n")
        return
    
    # Test trending cards
    print("2. Testing /api/trending...")
    response = requests.get(f"{BASE_URL}/api/trending", params={"limit": 5})
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Found {data['count']} trending cards")
        if data['cards']:
            card = data['cards'][0]
            print(f"   Top card: {card['player_name']} - Hotness: {card['hotness_score']}\n")
        else:
            print("   ⚠️  No cards found. Import data first with run_pipeline.py\n")
    else:
        print(f"   ❌ Failed: {response.status_code}\n")
    
    # Test trending rookies
    print("3. Testing /api/trending/rookies...")
    response = requests.get(f"{BASE_URL}/api/trending/rookies", params={"limit": 5})
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Found {data['count']} trending rookies\n")
    else:
        print(f"   ❌ Failed: {response.status_code}\n")
    
    # Test card search
    print("4. Testing /api/cards (search)...")
    response = requests.get(f"{BASE_URL}/api/cards", params={"rookie_only": True, "limit": 5})
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Found {data['count']} cards")
        if data['cards']:
            card_id = data['cards'][0]['id']
            
            # Test card details
            print(f"\n5. Testing /api/cards/{card_id} (details)...")
            response = requests.get(f"{BASE_URL}/api/cards/{card_id}")
            if response.status_code == 200:
                card = response.json()
                print(f"   Card details retrieved")
                print(f"   Player: {card['player_name']}")
                print(f"   Recent sales: {len(card['recent_sales'])}")
                if 'trend' in card and card['trend']:
                    print(f"   Avg price: ${card['trend'].get('avg_price', 'N/A')}")
            else:
                print(f"   Failed: {response.status_code}")
        else:
            print("   ⚠️  No cards in database. Import data first.\n")
    else:
        print(f"   ❌ Failed: {response.status_code}\n")
    
    print("\n✅ API tests complete!")
    print(f"\n📚 View interactive docs at: {BASE_URL}/docs")

if __name__ == "__main__":
    test_api()
