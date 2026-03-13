"""
COMC (Check Out My Cards) Scraper

Scrapes real active listings from COMC.com
- No API needed
- No rate limits
- Real prices
- Easy HTML structure
"""
import sys
sys.path.insert(0, '/app')

import requests
from bs4 import BeautifulSoup
import re
from datetime import date
from backend.utils.database import SessionLocal
from backend.models import Card, ActiveListing

def scrape_comc_listings(player_name, max_results=20):
    """Scrape COMC for active listings"""
    search_url = f"https://www.comc.com/Cards/Baseball/{player_name.replace(' ', '_')}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all card listings
        listings = []
        cards = soup.find_all('div', class_='card-item')[:max_results]
        
        for card_elem in cards:
            try:
                # Get title
                title_elem = card_elem.find('div', class_='card-title')
                if not title_elem:
                    continue
                title = title_elem.text.strip()
                
                # Get price
                price_elem = card_elem.find('span', class_='price')
                if not price_elem:
                    continue
                price_text = price_elem.text.strip().replace('$', '').replace(',', '')
                price = float(price_text)
                
                # Get item ID
                link_elem = card_elem.find('a')
                item_id = link_elem.get('href', '').split('/')[-1] if link_elem else None
                
                # Parse card details
                year_match = re.search(r'\b(20\d{2})\b', title)
                card_year = int(year_match.group()) if year_match else 2023
                
                is_rookie = bool(re.search(r'\brc\b|\brookie\b', title.lower()))
                
                sets = ['Prizm', 'Select', 'Optic', 'Bowman', 'Topps']
                card_set = 'Unknown'
                for s in sets:
                    if s.lower() in title.lower():
                        card_set = s
                        break
                
                listings.append({
                    'title': title,
                    'price': price,
                    'item_id': item_id,
                    'player_name': player_name,
                    'card_year': card_year,
                    'card_set': card_set,
                    'is_rookie': is_rookie,
                    'sport': 'Baseball'
                })
                
            except Exception as e:
                continue
        
        return listings
        
    except Exception as e:
        print(f"Error scraping COMC: {e}")
        return []

def add_to_database(listing_data):
    """Add listing to database"""
    db = SessionLocal()
    try:
        # Find or create card
        card = db.query(Card).filter(
            Card.player_name == listing_data['player_name'],
            Card.card_year == listing_data['card_year'],
            Card.card_set == listing_data['card_set']
        ).first()
        
        if not card:
            card = Card(
                player_name=listing_data['player_name'],
                card_year=listing_data['card_year'],
                card_set=listing_data['card_set'],
                is_rookie=listing_data['is_rookie'],
                sport=listing_data['sport']
            )
            db.add(card)
            db.flush()
        
        # Add active listing
        listing = ActiveListing(
            card_id=card.id,
            ebay_item_id=f"COMC_{listing_data['item_id']}",
            listing_price=listing_data['price'],
            listing_type='buy_it_now',
            snapshot_date=date.today()
        )
        db.add(listing)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Error adding to DB: {e}")
        return False
    finally:
        db.close()

if __name__ == '__main__':
    from backend.services.volume_discovery import VolumeDiscovery
    
    print("COMC Scraper - Real Active Listings")
    print("=" * 70)
    
    # Get top players from Phase 1
    discovery = VolumeDiscovery()
    top_players = discovery.discover_by_volume(days=90, limit=100)
    
    total_added = 0
    
    for player in top_players[:10]:  # Top 10 players
        player_name = player['player_name']
        print(f"\n{player_name}")
        print("-" * 70)
        
        listings = scrape_comc_listings(player_name)
        print(f"Found {len(listings)} listings")
        
        for listing in listings:
            if add_to_database(listing):
                print(f"  ✓ ${listing['price']:.2f} - {listing['title'][:60]}")
                total_added += 1
    
    print(f"\n{'=' * 70}")
    print(f"Added {total_added} REAL active listings from COMC")
    print("Run Phase 2 test now!")
