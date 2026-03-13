"""
Discovery Aggregator

Analyzes PWCC sales data to identify trending players.
Runs daily at 1 AM to auto-populate targets.yaml.

Data Sources:
1. PWCC sales (via NovaAct webhook)
2. Sports performance data (future)

Scoring:
- Sales volume (50%): More sales = more demand
- Average price (30%): Higher prices = stronger market
- Price velocity (20%): Rising prices = momentum
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict
import logging

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.utils.database import SessionLocal
from backend.models import Card, Sale
from sqlalchemy import and_, func

logger = logging.getLogger(__name__)


class DiscoveryAggregator:
    """Analyze sales data to discover trending players"""
    
    MIN_SALES = 2  # Minimum sales to consider
    
    def discover_trending_players(self, days: int = 180, limit: int = 50) -> List[Dict]:
        """
        Discover trending players from PWCC sales
        
        Args:
            days: Look back period
            limit: Maximum players to return
            
        Returns:
            List of discovered players with scores
        """
        db = SessionLocal()
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).date()
            
            logger.info(f"Analyzing PWCC sales from last {days} days...")
            
            # Get all PWCC sales in period
            sales = db.query(Sale).filter(
                and_(
                    Sale.source == 'pwcc',
                    Sale.sale_date >= cutoff_date
                )
            ).all()
            
            logger.info(f"Found {len(sales)} PWCC sales")
            
            # Group by player (aggregate across all their cards)
            by_player = defaultdict(lambda: {
                'sales': [],
                'cards': set(),
                'sport': None,
                'is_rookie': False
            })
            
            for sale in sales:
                card = db.query(Card).get(sale.card_id)
                if not card or not card.player_name:
                    continue
                
                key = card.player_name
                by_player[key]['sales'].append(float(sale.sale_price))
                by_player[key]['cards'].add(f"{card.card_year} {card.card_set}")
                by_player[key]['sport'] = card.sport or by_player[key]['sport']
                by_player[key]['is_rookie'] = card.is_rookie or by_player[key]['is_rookie']
            
            # Calculate scores
            discoveries = []
            for player_name, data in by_player.items():
                sales_count = len(data['sales'])
                
                if sales_count < self.MIN_SALES:
                    continue
                
                avg_price = sum(data['sales']) / sales_count
                
                # Calculate price velocity (compare first half to second half)
                mid = len(data['sales']) // 2
                if mid > 0:
                    first_half = sum(data['sales'][:mid]) / mid
                    second_half = sum(data['sales'][mid:]) / (len(data['sales']) - mid)
                    price_velocity = ((second_half - first_half) / first_half) * 100 if first_half > 0 else 0
                else:
                    price_velocity = 0
                
                # Calculate discovery score
                score = self._calculate_score(sales_count, avg_price, price_velocity)
                
                # Get most common card for display
                card_sets = ', '.join(sorted(data['cards']))
                
                discoveries.append({
                    'player_name': player_name,
                    'sport': data['sport'] or 'Unknown',
                    'card_year': None,  # Multiple cards
                    'card_set': card_sets,
                    'sales_volume': sales_count,
                    'avg_price': round(avg_price, 2),
                    'price_velocity': round(price_velocity, 2),
                    'discovery_score': score,
                    'discovered_at': datetime.now().isoformat(),
                    'source': 'pwcc'
                })
            
            # Sort by score
            discoveries.sort(key=lambda x: x['discovery_score'], reverse=True)
            
            logger.info(f"Discovered {len(discoveries)} trending players")
            return discoveries[:limit]
            
        finally:
            db.close()
    
    def _calculate_score(self, sales_count: int, avg_price: float, price_velocity: float) -> float:
        """
        Calculate discovery score (0-100)
        
        Scoring:
        - Volume: 0-50 points (more sales = higher score)
        - Price: 0-30 points (sweet spot $50-$500)
        - Velocity: 0-20 points (rising prices = higher score)
        """
        # Volume score (0-50)
        volume_score = min(sales_count / 20 * 50, 50)
        
        # Price score (0-30)
        if 50 <= avg_price <= 500:
            price_score = 30
        elif 25 <= avg_price < 50 or 500 < avg_price <= 1000:
            price_score = 20
        elif 10 <= avg_price < 25 or 1000 < avg_price <= 2000:
            price_score = 10
        else:
            price_score = 5
        
        # Velocity score (0-20)
        if price_velocity > 0:
            velocity_score = min(abs(price_velocity) / 50 * 20, 20)
        else:
            velocity_score = 0  # Penalize falling prices
        
        total = volume_score + price_score + velocity_score
        return round(total, 2)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    aggregator = DiscoveryAggregator()
    discoveries = aggregator.discover_trending_players(days=7, limit=20)
    
    print(f"\nTop 20 Trending Players (from PWCC sales):\n")
    for i, player in enumerate(discoveries, 1):
        print(f"{i}. {player['player_name']} ({player['sport']})")
        print(f"   Score: {player['discovery_score']} | Sales: {player['sales_volume']} | "
              f"Avg: ${player['avg_price']:.2f} | Velocity: {player['price_velocity']:+.1f}%")
        print(f"   {player['card_year']} {player['card_set']}\n")
