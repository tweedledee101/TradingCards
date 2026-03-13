"""
Volume-Based Discovery System

Phase 1: Find top players by sales volume (ignore price)
Phase 2: Filter for players with cards in user's budget
Phase 3: Analyze opportunities for those 20 players
"""

from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict
from backend.utils.database import SessionLocal
from backend.models import Card, Sale
from sqlalchemy import func

class VolumeDiscovery:
    """Discover trending players by sales volume only"""
    
    def discover_by_volume(self, days: int = 90, limit: int = 100) -> List[Dict]:
        """
        Phase 1: Find top players by sales volume ONLY
        
        NO PRICE FILTERING - Just pure volume ranking
        
        Args:
            days: Lookback period (default 90 days = 1 quarter)
            limit: Number of players to return (default 100)
            
        Returns:
            List of top players ranked by sales volume
        """
        db = SessionLocal()
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).date()
            
            # Get all sales in period
            sales = db.query(Sale).filter(Sale.sale_date >= cutoff_date).all()
            
            # Group by player, count total sales
            by_player = defaultdict(lambda: {
                'sales_count': 0,
                'min_price': float('inf'),
                'max_price': 0,
                'sport': None
            })
            
            for sale in sales:
                card = db.query(Card).get(sale.card_id)
                if not card or not card.player_name:
                    continue
                
                player = card.player_name
                price = float(sale.sale_price)
                
                by_player[player]['sales_count'] += 1
                by_player[player]['min_price'] = min(by_player[player]['min_price'], price)
                by_player[player]['max_price'] = max(by_player[player]['max_price'], price)
                by_player[player]['sport'] = card.sport or by_player[player]['sport']
            
            # Sort by volume (most sales first)
            sorted_players = sorted(
                by_player.items(),
                key=lambda x: x[1]['sales_count'],
                reverse=True
            )
            
            # Return top N players by volume - NO PRICE FILTERING
            result = []
            for player_name, data in sorted_players[:limit]:
                result.append({
                    'player_name': player_name,
                    'sport': data['sport'],
                    'sales_volume': data['sales_count'],
                    'min_price': round(data['min_price'], 2),
                    'max_price': round(data['max_price'], 2),
                    'discovered_at': datetime.now().isoformat()
                })
            
            return result
            
        finally:
            db.close()

if __name__ == '__main__':
    discovery = VolumeDiscovery()
    
    # Phase 1: Get top 100 players by volume (NO PRICE FILTERING)
    players = discovery.discover_by_volume(days=90, limit=100)
    
    print("TOP 100 PLAYERS BY SALES VOLUME (Last 90 Days)")
    print("=" * 70)
    print("Rank | Player | Sport | Volume | Price Range")
    print("-" * 70)
    for i, p in enumerate(players[:20], 1):  # Show top 20
        print(f"{i:3d}. {p['player_name']:25s} {p['sport'] or 'Unknown':12s} "
              f"{p['sales_volume']:4d} sales  ${p['min_price']:.0f}-${p['max_price']:.0f}")
    
    if len(players) > 20:
        print(f"\n... and {len(players) - 20} more players")
    
    print(f"\nTotal: {len(players)} players found")
