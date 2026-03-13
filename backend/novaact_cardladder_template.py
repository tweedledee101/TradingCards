"""
NovaAct Card Ladder Price Benchmark Scraper
Scrapes Card Ladder price data and sends to webhook
"""
import requests
import yaml
import os
from time import sleep
from datetime import datetime

# Configuration
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'http://localhost:8000/api/webhooks/novaact/price-benchmark')
TARGETS_FILE = os.path.join(os.path.dirname(__file__), '../config/targets.yaml')

CARD_YEARS = {
    'Victor Wembanyama': 2023,
    'Paul Skenes': 2024,
    'Caleb Williams': 2024,
    'Caitlin Clark': 2024,
    'Shohei Ohtani': 2018,
    'Patrick Mahomes': 2017,
    'LeBron James': 2003,
    'Michael Jordan': 1986
}

SET_MAPPINGS = {
    'prizm': 'Prizm',
    'select': 'Select',
    'optic': 'Optic',
    'bowman chrome': 'Bowman Chrome',
    'topps chrome': 'Topps Chrome',
    'fleer': 'Fleer',
    'upper deck': 'Upper Deck'
}

def load_targets():
    with open(TARGETS_FILE) as f:
        return yaml.safe_load(f)['players']

def parse_query(query, player_name):
    query_lower = query.lower().replace('{name}', '').strip()
    for key, value in SET_MAPPINGS.items():
        if key in query_lower:
            return value
    return 'Prizm'

def scrape_cardladder_data(player_name, card_year, card_set):
    """
    NovaAct Browser Automation Steps:
    
    1. navigate('https://www.cardladder.com')
    2. fill_search(f'{player_name} {card_year} {card_set}')
    3. click_first_result()
    4. current = extract_text('.current-price')
    5. price_7d = extract_text('.price-7d-ago')
    6. price_30d = extract_text('.price-30d-ago')
    7. velocity = extract_text('.velocity-rating')
    8. return data
    
    For testing, returns mock data
    """
    import random
    base_price = random.uniform(20, 200)
    change_7d = random.uniform(-10, 30)
    change_30d = random.uniform(-5, 50)
    
    price_7d_ago = base_price / (1 + change_7d/100)
    price_30d_ago = base_price / (1 + change_30d/100)
    
    if change_7d > 15:
        velocity = 'Hot'
    elif change_7d > 5:
        velocity = 'Warm'
    elif change_7d < -5:
        velocity = 'Cold'
    else:
        velocity = 'Stable'
    
    return {
        'player_name': player_name,
        'card_year': card_year,
        'card_set': card_set,
        'source': 'cardladder',
        'current_price': round(base_price, 2),
        'price_7d_ago': round(price_7d_ago, 2),
        'price_30d_ago': round(price_30d_ago, 2),
        'velocity_rating': velocity,
        'scrape_date': datetime.now().strftime('%Y-%m-%d')
    }

def scrape_130point_data(player_name, card_year, card_set):
    """
    NovaAct Browser Automation Steps:
    
    1. navigate('https://130point.com')
    2. fill_search(f'{player_name} {card_year} {card_set}')
    3. click_first_result()
    4. Extract price data
    5. return data
    """
    import random
    base_price = random.uniform(20, 200)
    change_7d = random.uniform(-10, 30)
    change_30d = random.uniform(-5, 50)
    
    price_7d_ago = base_price / (1 + change_7d/100)
    price_30d_ago = base_price / (1 + change_30d/100)
    
    if change_7d > 15:
        velocity = 'Hot'
    elif change_7d > 5:
        velocity = 'Warm'
    elif change_7d < -5:
        velocity = 'Cold'
    else:
        velocity = 'Stable'
    
    return {
        'player_name': player_name,
        'card_year': card_year,
        'card_set': card_set,
        'source': '130point',
        'current_price': round(base_price, 2),
        'price_7d_ago': round(price_7d_ago, 2),
        'price_30d_ago': round(price_30d_ago, 2),
        'velocity_rating': velocity,
        'scrape_date': datetime.now().strftime('%Y-%m-%d')
    }

def send_to_webhook(data):
    try:
        response = requests.post(WEBHOOK_URL, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        change_7d = result.get('change_7d', 0)
        print(f"✅ {data['player_name']} {data['card_set']} ({data['source']}): ${data['current_price']:.2f} ({change_7d:+.1f}% 7d)")
        return True
    except Exception as e:
        print(f"❌ {data['player_name']}: {e}")
        return False

def main():
    print(f"🚀 Card Ladder Scraper started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📡 Webhook: {WEBHOOK_URL}")
    
    targets = load_targets()
    success_count = 0
    
    for player in targets:
        player_name = player['name']
        card_year = CARD_YEARS.get(player_name, 2024)
        query = player['queries'][0]
        card_set = parse_query(query, player_name)
        
        print(f"\n🔍 Scraping {player_name} {card_year} {card_set}...")
        
        # Scrape Card Ladder
        data = scrape_cardladder_data(player_name, card_year, card_set)
        if send_to_webhook(data):
            success_count += 1
        sleep(5)
        
        # Optionally scrape 130point for cross-validation
        # data = scrape_130point_data(player_name, card_year, card_set)
        # if send_to_webhook(data):
        #     success_count += 1
        # sleep(5)
    
    print(f"\n✅ Complete: {success_count}/{len(targets)} cards processed")

if __name__ == '__main__':
    main()
