"""
Test the new Opportunities API

Shows arbitrage opportunities with momentum validation
"""
import requests
import json

BASE_URL = "http://localhost:8000/api"


def test_opportunities():
    """Test the opportunities endpoint"""
    print("=" * 80)
    print("🎯 TESTING OPPORTUNITIES API")
    print("=" * 80)
    
    # Test 1: Get all opportunities
    print("\n1️⃣  GET ALL OPPORTUNITIES")
    print("-" * 80)
    response = requests.get(f"{BASE_URL}/opportunities")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {data['count']} opportunities\n")
        
        for i, opp in enumerate(data['opportunities'][:5], 1):
            print(f"{i}. {opp['player_name']} {opp['card_year']} {opp['card_set']}")
            print(f"   💰 ARBITRAGE:")
            print(f"      Buy: ${opp['arbitrage']['buy_price']} | Sell: ${opp['arbitrage']['sell_price']}")
            print(f"      Profit: ${opp['arbitrage']['net_profit']} ({opp['arbitrage']['roi']}% ROI)")
            print(f"   📈 MOMENTUM:")
            print(f"      Price Trend: {opp['momentum']['price_trend']} {opp['momentum']['price_change_14d']:+.1f}% (14d)")
            print(f"      Sales: {opp['momentum']['sales_per_week']}/week | STR: {opp['momentum']['str_rate']:.0f}%")
            print(f"      Listings: {opp['momentum']['active_listings']}")
            print(f"   ⭐ SCORE: {opp['opportunity_score']}/100 | Confidence: {opp['confidence']}")
            print()
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
    
    # Test 2: Filter by budget
    print("\n2️⃣  FILTER: Budget $50-$150")
    print("-" * 80)
    response = requests.get(f"{BASE_URL}/opportunities", params={
        'min_budget': 50,
        'max_budget': 150
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {data['count']} opportunities in $50-$150 range\n")
        
        for opp in data['opportunities'][:3]:
            print(f"• {opp['player_name']} - Buy: ${opp['arbitrage']['buy_price']} → Profit: ${opp['arbitrage']['net_profit']}")
    else:
        print(f"❌ Error: {response.status_code}")
    
    # Test 3: Filter by ROI
    print("\n3️⃣  FILTER: Minimum 20% ROI")
    print("-" * 80)
    response = requests.get(f"{BASE_URL}/opportunities", params={
        'min_roi': 20
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {data['count']} opportunities with 20%+ ROI\n")
        
        for opp in data['opportunities'][:3]:
            print(f"• {opp['player_name']} - ROI: {opp['arbitrage']['roi']}% | Profit: ${opp['arbitrage']['net_profit']}")
    else:
        print(f"❌ Error: {response.status_code}")
    
    # Test 4: Filter by momentum
    print("\n4️⃣  FILTER: Rising prices only")
    print("-" * 80)
    response = requests.get(f"{BASE_URL}/opportunities", params={
        'momentum': 'rising'
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {data['count']} opportunities with rising prices\n")
        
        for opp in data['opportunities'][:3]:
            print(f"• {opp['player_name']} - {opp['momentum']['price_trend']} {opp['momentum']['price_change_14d']:+.1f}%")
    else:
        print(f"❌ Error: {response.status_code}")
    
    # Test 5: Get stats
    print("\n5️⃣  MARKET STATS")
    print("-" * 80)
    response = requests.get(f"{BASE_URL}/opportunities-stats")
    
    if response.status_code == 200:
        stats = response.json()
        print(f"Total Opportunities: {stats['total_opportunities']}")
        print(f"Average ROI: {stats['avg_roi']}%")
        print(f"Average Profit: ${stats['avg_profit']}")
        print(f"High Confidence: {stats['high_confidence_count']}")
        
        if stats.get('best_opportunity'):
            best = stats['best_opportunity']
            print(f"\n🏆 BEST OPPORTUNITY:")
            print(f"   {best['player_name']} {best['card_year']} {best['card_set']}")
            print(f"   Score: {best['opportunity_score']}/100")
            print(f"   Profit: ${best['arbitrage']['net_profit']} ({best['arbitrage']['roi']}% ROI)")
    else:
        print(f"❌ Error: {response.status_code}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        test_opportunities()
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to API server")
        print("   Make sure the API is running: python -m backend.api.run")
    except Exception as e:
        print(f"❌ ERROR: {e}")
