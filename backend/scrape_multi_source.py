"""
Multi-Source Card Data Scraper

Aggregates data from 3 sources:
1. COMC - Budget/mid-range active listings
2. PWCC - High-end auction results
3. 130point - eBay sales data (free tier)

Combined = More reliable than any single source
"""
import sys
sys.path.insert(0, '/app')

import requests
from bs4 import BeautifulSoup
import re
from datetime import date, datetime, timedelta
from backend.utils.database import SessionLocal
from backend.models import Card, ActiveListing, Sale
import time

class MultiSourceScraper:
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def scrape_comc(self, player_name, max_results=15):
        """COMC - Active listings"""
        url = f"https://www.comc.com/Cards/Baseball/{player_name.replace(' ', '_')}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            listings = []
            # COMC uses simple div structure
            items = soup.find_all('div', class_='product-item')[:max_results]
            
            for item in items:
                try:
                    title = item.find('a', class_='product-name').text.strip()
                    price_text = item.find('span', class_='price').text.strip()
                    price = float(re.search(r'[\d.]+', price_text.replace(',', '')).group())
                    
                    listings.append({
                        'source': 'COMC',
                        'title': title,
                        'price': price,
                        'player_name': player_name
                    })
                except:
                    continue
            
            return listings
        except:
            return []
    
    def scrape_pwcc(self, player_name, max_results=15):
        """PWCC - Auction results"""
        # PWCC search format
        query = player_name.replace(' ', '+')
        url = f"https://www.pwccmarketplace.com/search?q={query}&sort=date"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            listings = []
            items = soup.find_all('div', class_='auction-item')[:max_results]
            
            for item in items:
                try:
                    title = item.find('h3').text.strip()
                    price_elem = item.find('span', class_='final-price')
                    if price_elem:
                        price = float(re.search(r'[\d.]+', price_elem.text.replace(',', '')).group())
                        
                        listings.append({
                            'source': 'PWCC',
                            'title': title,
                            'price': price,
                            'player_name': player_name
                        })
                except:
                    continue
            
            return listings
        except:
            return []
    
    def scrape_130point(self, player_name, max_results=15):
        """130point - eBay aggregator (free tier)"""
        query = player_name.replace(' ', '%20')
        url = f"https://130point.com/sales/?q={query}&s=d&p=0"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            sales = []
            rows = soup.find_all('tr', class_='sale-row')[:max_results]
            
            for row in rows:
                try:
                    title = row.find('td', class_='title').text.strip()
                    price_text = row.find('td', class_='price').text.strip()
                    price = float(re.search(r'[\d.]+', price_text.replace(',', '').replace('$', '')).group())
                    date_text = row.find('td', class_='date').text.strip()
                    
                    sales.append({
                        'source': '130point',
                        'title': title,
                        'price': price,
                        'player_name': player_name,
                        'date': date_text
                    })
                except:
                    continue
            
            return sales
        except:
            return []
    
    def parse_card_details(self, title):
        """Extract card details from title"""
        year_match = re.search(r'\b(20\d{2})\b', title)
        card_year = int(year_match.group()) if year_match else 2023
        
        is_rookie = bool(re.search(r'\brc\b|\brookie\b', title.lower()))
        
        sets = ['Prizm', 'Select', 'Optic', 'Bowman', 'Topps', 'Mosaic', 'Donruss']
        card_set = 'Unknown'
        for s in sets:
            if s.lower() in title.lower():
                card_set = s
                break
        
        return {
            'card_year': card_year,
            'card_set': card_set,
            'is_rookie': is_rookie
        }
    
    def scrape_all(self, player_name):
        """Scrape all sources for a player"""
        print(f"\n{player_name}")
        print("-" * 70)
        
        # Active listings from COMC
        comc_listings = self.scrape_comc(player_name)
        print(f"  COMC: {len(comc_listings)} active listings")
        time.sleep(1)
        
        # High-end from PWCC
        pwcc_listings = self.scrape_pwcc(player_name)
        print(f"  PWCC: {len(pwcc_listings)} auction results")
        time.sleep(1)
        
        # eBay aggregated from 130point
        point130_sales = self.scrape_130point(player_name)
        print(f"  130point: {len(point130_sales)} eBay sales")
        time.sleep(1)
        
        return {
            'active_listings': comc_listings + pwcc_listings,
            'sales': point130_sales
        }

def add_to_database(data, player_name, sport='Baseball'):
    """Add scraped data to database"""
    db = SessionLocal()
    added_listings = 0
    added_sales = 0
    
    try:
        # Add active listings
        for listing in data['active_listings']:
            details = MultiSourceScraper().parse_card_details(listing['title'])
            
            # Find or create card
            card = db.query(Card).filter(
                Card.player_name == player_name,
                Card.card_year == details['card_year'],
                Card.card_set == details['card_set']
            ).first()
            
            if not card:
                card = Card(
                    player_name=player_name,
                    card_year=details['card_year'],
                    card_set=details['card_set'],
                    is_rookie=details['is_rookie'],
                    sport=sport
                )
                db.add(card)
                db.flush()
            
            # Add listing
            active_listing = ActiveListing(
                card_id=card.id,
                ebay_item_id=f"{listing['source']}_{hash(listing['title'])}",
                listing_price=listing['price'],
                listing_type='buy_it_now',
                snapshot_date=date.today()
            )
            db.add(active_listing)
            added_listings += 1
        
        # Add sales
        for sale in data['sales']:
            details = MultiSourceScraper().parse_card_details(sale['title'])
            
            card = db.query(Card).filter(
                Card.player_name == player_name,
                Card.card_year == details['card_year'],
                Card.card_set == details['card_set']
            ).first()
            
            if not card:
                card = Card(
                    player_name=player_name,
                    card_year=details['card_year'],
                    card_set=details['card_set'],
                    is_rookie=details['is_rookie'],
                    sport=sport
                )
                db.add(card)
                db.flush()
            
            # Add sale
            sale_record = Sale(
                card_id=card.id,
                ebay_item_id=f"130P_{hash(sale['title'])}",
                sale_price=sale['price'],
                sale_date=datetime.now() - timedelta(days=7),  # Approximate
                condition='Unknown'
            )
            db.add(sale_record)
            added_sales += 1
        
        db.commit()
        return added_listings, added_sales
        
    except Exception as e:
        db.rollback()
        print(f"  Error: {e}")
        return 0, 0
    finally:
        db.close()

if __name__ == '__main__':
    from backend.services.volume_discovery import VolumeDiscovery
    
    print("Multi-Source Card Data Scraper")
    print("=" * 70)
    print("Sources: COMC + PWCC + 130point")
    print()
    
    # Get top players
    discovery = VolumeDiscovery()
    top_players = discovery.discover_by_volume(days=90, limit=100)
    
    scraper = MultiSourceScraper()
    total_listings = 0
    total_sales = 0
    
    for player in top_players[:10]:  # Top 10 players
        player_name = player['player_name']
        sport = player.get('sport', 'Baseball')
        
        # Scrape all sources
        data = scraper.scrape_all(player_name)
        
        # Add to database
        listings, sales = add_to_database(data, player_name, sport)
        total_listings += listings
        total_sales += sales
        
        print(f"  ✓ Added {listings} listings, {sales} sales")
    
    print(f"\n{'=' * 70}")
    print(f"TOTAL: {total_listings} active listings, {total_sales} sales")
    print("Multi-source data collection complete!")
    print("\nRun Phase 2 test now!")
