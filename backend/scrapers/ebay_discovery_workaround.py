"""
eBay Discovery Workaround

Uses existing eBay scraper (that works) to discover trending cards.
Analyzes sold listings to find high-volume cards.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.scrapers.ebay_scraper import EbayScraper
from backend.utils.player_extractor import PlayerExtractor
from typing import List, Dict
from datetime import datetime
from collections import defaultdict
import logging
import time

logger = logging.getLogger(__name__)


class EbayDiscoveryWorkaround:
    """Discover trending cards using existing eBay scraper"""
    
    MIN_SALES_VOLUME = 3  # Minimum sales to fetch player name
    
    # Broad search queries to find trending cards (reduced to avoid rate limits)
    DISCOVERY_QUERIES = [
        "prizm rookie PSA 10",
        "bowman chrome rookie PSA",
        "select rookie PSA 10"
    ]
    
    def __init__(self):
        self.scraper = EbayScraper()
        self.player_extractor = PlayerExtractor()
    
    def discover_trending_cards(self, days: int = 7) -> List[Dict]:
        """
        Discover trending cards by analyzing sold listings
        
        Args:
            days: Look back period
            
        Returns:
            List of discovered cards with metadata
        """
        all_cards = defaultdict(lambda: {
            'sales': [],
            'title': None,
            'card_year': None,
            'card_set': None,
            'player_name': None,
            'item_id': None
        })
        
        # Search each discovery query
        for i, query in enumerate(self.DISCOVERY_QUERIES, 1):
            logger.info(f"Searching ({i}/{len(self.DISCOVERY_QUERIES)}): {query}")
            
            try:
                results = self.scraper.search_sold_listings(query, days_back=days)
                
                for item in results:
                    card_year = item.get('card_year')
                    card_set = item.get('card_set', 'Unknown')
                    
                    if not card_year:
                        continue
                    
                    # Group by year + set (will get player name later)
                    key = f"{card_year}_{card_set}"
                    
                    # Aggregate sales
                    all_cards[key]['sales'].append(item['price'])
                    all_cards[key]['title'] = item['title']  # Keep one title
                    all_cards[key]['card_year'] = card_year
                    all_cards[key]['card_set'] = card_set
                    all_cards[key]['item_id'] = item.get('ebay_item_id')
                
                logger.info(f"  Found {len(results)} sales")
                
                # Rate limiting - wait 5 seconds between queries
                if i < len(self.DISCOVERY_QUERIES):
                    logger.info(f"  Waiting 5 seconds before next query...")
                    time.sleep(5)
                
            except Exception as e:
                logger.error(f"Error searching {query}: {e}")
                logger.info(f"  Waiting 10 seconds after error...")
                time.sleep(10)  # Wait longer on error
                continue
        
        logger.info(f"Found {len(all_cards)} unique cards, filtering by volume...")
        
        # Filter by volume first, then fetch player names
        cards_to_lookup = []
        for key, data in all_cards.items():
            if len(data['sales']) >= self.MIN_SALES_VOLUME:
                cards_to_lookup.append((key, data))
        
        logger.info(f"Fetching player names for {len(cards_to_lookup)} high-volume cards...")
        
        # Fetch player names only for high-volume cards
        for i, (key, data) in enumerate(cards_to_lookup, 1):
            if i % 10 == 0:
                logger.info(f"  Progress: {i}/{len(cards_to_lookup)}")
            
            item_id = data.get('item_id')
            if item_id:
                player_name = self.scraper._get_player_from_product(item_id)
                if player_name:
                    data['player_name'] = player_name
                    logger.info(f"  Found: {player_name} ({data['card_year']} {data['card_set']})")
                
                # Rate limiting
                time.sleep(0.5)
        
        # Convert to discovery format
        discoveries = []
        for key, data in all_cards.items():
            sales_count = len(data['sales'])
            
            if sales_count < self.MIN_SALES_VOLUME:
                continue
            
            avg_price = sum(data['sales']) / sales_count
            
            # Calculate price velocity
            mid = len(data['sales']) // 2
            if mid > 0:
                first_half_avg = sum(data['sales'][:mid]) / mid
                second_half_avg = sum(data['sales'][mid:]) / (len(data['sales']) - mid)
                price_velocity = ((second_half_avg - first_half_avg) / first_half_avg) * 100 if first_half_avg > 0 else 0
            else:
                price_velocity = 0
            
            # Get player name
            player_name = data.get('player_name')
            if not player_name:
                continue
            
            # Detect sport from title
            title_lower = data['title'].lower()
            if any(word in title_lower for word in ['prizm', 'select', 'optic', 'nba', 'basketball']):
                sport = 'Basketball'
            elif any(word in title_lower for word in ['bowman', 'topps', 'mlb', 'baseball']):
                sport = 'Baseball'
            elif any(word in title_lower for word in ['panini', 'nfl', 'football']):
                sport = 'Football'
            elif any(word in title_lower for word in ['upper deck', 'nhl', 'hockey']):
                sport = 'Hockey'
            else:
                sport = 'Unknown'
            
            # Extract set from data or title
            card_set = data.get('card_set', 'Unknown')
            if card_set == 'Unknown':
                title_lower = data['title'].lower()
                for set_name in ['Prizm', 'Select', 'Optic', 'Bowman', 'Topps', 'Mosaic', 'Donruss']:
                    if set_name.lower() in title_lower:
                        card_set = set_name
                        break
            
            # Get year from data
            card_year = data['card_year']
            
            discovery_score = self._calculate_discovery_score(sales_count, price_velocity, avg_price)
            
            discoveries.append({
                'player_name': player_name,
                'sport': sport,
                'card_year': card_year,
                'card_set': card_set,
                'sales_volume': sales_count,
                'avg_price': round(avg_price, 2),
                'price_velocity': round(price_velocity, 2),
                'discovery_score': discovery_score,
                'discovered_at': datetime.now().isoformat()
            })
        
        # Sort by score
        discoveries.sort(key=lambda x: x['discovery_score'], reverse=True)
        
        logger.info(f"Discovered {len(discoveries)} trending cards")
        return discoveries
    
    def _calculate_discovery_score(self, sales_count: int, price_velocity: float, avg_price: float) -> float:
        """Calculate discovery score (0-100)"""
        
        # Volume score (0-50)
        volume_score = min(sales_count / 50 * 50, 50)
        
        # Velocity score (0-30)
        velocity_score = min(abs(price_velocity) / 50 * 30, 30)
        
        # Price score (0-20)
        if 50 <= avg_price <= 500:
            price_score = 20
        elif 25 <= avg_price < 50 or 500 < avg_price <= 1000:
            price_score = 15
        elif 10 <= avg_price < 25 or 1000 < avg_price <= 2000:
            price_score = 10
        else:
            price_score = 5
        
        total_score = volume_score + velocity_score + price_score
        return round(total_score, 2)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    discovery = EbayDiscoveryWorkaround()
    trending = discovery.discover_trending_cards(days=7)
    
    print(f"\n🔥 Top 20 Trending Cards:\n")
    for i, card in enumerate(trending[:20], 1):
        print(f"{i}. {card['player_name']} {card['card_year']} {card['card_set']}")
        print(f"   Score: {card['discovery_score']} | Sales: {card['sales_volume']} | "
              f"Avg: ${card['avg_price']:.2f} | Velocity: {card['price_velocity']}%\n")
