"""
NovaAct PSA Population Scraper
Scrapes PSA grading data and sends to webhook
"""
import requests
import yaml
import os
from time import sleep
from datetime import datetime

# Configuration
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'http://localhost:8000/api/webhooks/novaact/psa')
TARGETS_FILE = os.path.join(os.path.dirname(__file__), '../config/targets.yaml')

# Card year mappings for each player
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

# Set mappings from query strings
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
    """Extract card set from query string"""
    query_lower = query.lower().replace('{name}', '').strip()
    for key, value in SET_MAPPINGS.items():
        if key in query_lower:
            return value
    return 'Prizm'  # Default

def scrape_psa_data(player_name, card_year, card_set):
    """
    NovaAct Browser Automation Steps:
    
    1. navigate('https://www.psacard.com/pop')
    2. fill_search(f'{player_name} {card_year} {card_set}')
    3. click_search_button()
    4. wait_for_results()
    5. psa_10 = extract_text('.grade-10-count')
    6. psa_9 = extract_text('.grade-9-count')
    7. psa_8 = extract_text('.grade-8-count')
    8. total = extract_text('.total-graded')
    9. return data
    
    For testing, returns mock data
    """
    import random
    total = random.randint(100, 1000)
    psa_10_rate = random.uniform(0.10, 0.30)
    psa_10 = int(total * psa_10_rate)
    psa_9 = int(total * random.uniform(0.30, 0.50))
    psa_8 = total - psa_10 - psa_9
    
    return {
        'player_name': player_name,
        'card_year': card_year,
        'card_set': card_set,
        'psa_10_count': psa_10,
        'psa_9_count': psa_9,
        'psa_8_count': psa_8,
        'total_graded': total,
        'scrape_date': datetime.now().strftime('%Y-%m-%d')
    }

def send_to_webhook(data):
    try:
        response = requests.post(WEBHOOK_URL, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        print(f"✅ {data['player_name']} {data['card_set']}: PSA 10 rate = {result.get('psa_10_rate', 0):.1%}")
        return True
    except Exception as e:
        print(f"❌ {data['player_name']}: {e}")
        return False

def main():
    print(f"🚀 PSA Scraper started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📡 Webhook: {WEBHOOK_URL}")
    
    targets = load_targets()
    success_count = 0
    
    for player in targets:
        player_name = player['name']
        card_year = CARD_YEARS.get(player_name, 2024)
        
        # Scrape first query only (avoid duplicates)
        query = player['queries'][0]
        card_set = parse_query(query, player_name)
        
        print(f"\n🔍 Scraping {player_name} {card_year} {card_set}...")
        
        data = scrape_psa_data(player_name, card_year, card_set)
        if send_to_webhook(data):
            success_count += 1
        
        sleep(5)  # Rate limit
    
    print(f"\n✅ Complete: {success_count}/{len(targets)} cards processed")

if __name__ == '__main__':
    main()
