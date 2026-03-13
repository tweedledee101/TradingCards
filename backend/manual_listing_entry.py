"""
Manual Listing Entry - Paste eBay URLs to add active listings

Usage:
    python backend/manual_listing_entry.py
    
Then paste eBay item URLs one per line, press Enter twice when done.
"""
import sys
sys.path.insert(0, '/app')

import requests
from bs4 import BeautifulSoup
import re
from datetime import date
from backend.utils.database import SessionLocal
from backend.models import Card, ActiveListing

def extract_from_url(url):
    """Extract listing data from eBay URL"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title_elem = soup.find('h1', class_='x-item-title__mainTitle')
        if not title_elem:
            title_elem = soup.find('h1')
        title = title_elem.text.strip() if title_elem else "Unknown"
        
        # Extract price
        price_elem = soup.find('div', class_='x-price-primary')
        if not price_elem:
            price_elem = soup.find('span', class_='ux-textspans')
        price_text = price_elem.text.strip() if price_elem else "0"
        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
        price = float(price_match.group()) if price_match else 0
        
        # Extract item ID from URL
        item_id_match = re.search(r'/itm/(\d+)', url)
        ebay_item_id = item_id_match.group(1) if item_id_match else None
        
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
        
        # Extract player name (simple heuristic)
        player_name = "Shohei Ohtani"  # Default for now
        
        return {
            'title': title,
            'price': price,
            'ebay_item_id': ebay_item_id,
            'player_name': player_name,
            'card_year': card_year,
            'card_set': card_set,
            'is_rookie': is_rookie,
            'sport': 'Baseball'
        }
    except Exception as e:
        print(f"Error extracting from URL: {e}")
        return None

def add_listing_to_db(listing_data):
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
            ebay_item_id=listing_data['ebay_item_id'],
            listing_price=listing_data['price'],
            listing_type='buy_it_now',
            snapshot_date=date.today()
        )
        db.add(listing)
        db.commit()
        
        print(f"✓ Added: ${listing_data['price']:.2f} - {listing_data['title'][:60]}")
        return True
    except Exception as e:
        db.rollback()
        print(f"✗ Error: {e}")
        return False
    finally:
        db.close()

if __name__ == '__main__':
    print("Manual Listing Entry")
    print("=" * 70)
    print("Paste eBay item URLs (one per line), press Enter twice when done:\n")
    
    urls = []
    while True:
        line = input().strip()
        if not line:
            break
        urls.append(line)
    
    print(f"\nProcessing {len(urls)} URLs...\n")
    
    success = 0
    for url in urls:
        print(f"Fetching: {url}")
        data = extract_from_url(url)
        if data and add_listing_to_db(data):
            success += 1
    
    print(f"\n{'=' * 70}")
    print(f"Added {success}/{len(urls)} listings to database")
