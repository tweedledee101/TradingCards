"""
Target Discovery Service

Automatically curates target player list from market signals:
- eBay trending searches
- High sales volume cards
- Price velocity movers

Replaces manual targets.yaml curation with automated discovery.
"""

from typing import List, Dict
from datetime import datetime
import yaml
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class TargetDiscoveryService:
    """Manage automated target discovery and curation"""
    
    TARGETS_FILE = Path(__file__).parent.parent.parent / 'config' / 'targets.yaml'
    
    # Curation thresholds
    MIN_DISCOVERY_SCORE = 20.0  # Only add high-quality targets
    MAX_TARGETS = 50  # Keep list manageable
    
    def __init__(self):
        self.manual_favorites = self._load_manual_favorites()
    
    def _load_manual_favorites(self) -> List[Dict]:
        """Load manually curated favorites (preserved across auto-updates)"""
        
        try:
            with open(self.TARGETS_FILE, 'r') as f:
                data = yaml.safe_load(f)
                
            # Extract players marked as favorites
            favorites = []
            for player in data.get('players', []):
                if player.get('favorite', False):
                    favorites.append(player)
            
            logger.info(f"📌 Loaded {len(favorites)} manual favorites")
            return favorites
            
        except Exception as e:
            logger.warning(f"Could not load favorites: {e}")
            return []
    
    def update_targets(self, discovered_players: List[Dict], user_budget: float = 100.0) -> Dict:
        """
        Update targets.yaml with volume-based discovered players
        
        Args:
            discovered_players: List from VolumeDiscovery (already filtered by budget)
            user_budget: User's budget (for reference)
            
        Returns:
            Summary of changes
        """
        
        # All players already filtered by budget in VolumeDiscovery
        # Just convert to target format
        auto_targets = self._convert_to_targets(discovered_players)
        
        # Combine with manual favorites
        all_targets = self.manual_favorites + auto_targets
        
        # Write to targets.yaml
        self._write_targets_file(all_targets)
        
        summary = {
            'total_targets': len(all_targets),
            'manual_favorites': len(self.manual_favorites),
            'auto_discovered': len(auto_targets),
            'updated_at': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Updated targets: {summary['total_targets']} total "
                   f"({summary['manual_favorites']} favorites + {summary['auto_discovered']} discovered)")
        
        return summary
    
    def _convert_to_targets(self, players: List[Dict]) -> List[Dict]:
        """Convert volume-discovered players to targets.yaml format"""
        
        targets = []
        
        for player in players:
            queries = [
                '{name} rookie',
                '{name} Prizm',
                '{name} Bowman',
                '{name} Topps',
                '{name} PSA'
            ]
            
            target = {
                'name': player['player_name'],
                'sport': player['sport'],
                'queries': queries,
                'auto_discovered': True,
                'sales_volume': player['sales_volume'],
                'min_price': player['min_price'],
                'max_price': player['max_price'],
                'discovered_at': player['discovered_at']
            }
            
            targets.append(target)
        
        return targets
    
    def _generate_queries(self, card: Dict) -> List[str]:
        """Generate search queries for a discovered card"""
        
        player = card['player_name']
        year = card.get('card_year')
        card_set = card.get('card_set')
        
        queries = []
        
        # Base query
        queries.append(f"{{name}}")
        
        # Year + set specific
        if year and card_set:
            queries.append(f"{{name}} {year} {card_set}")
        
        # Common variations
        if card_set:
            queries.append(f"{{name}} {card_set}")
        
        # Rookie cards (if recent year)
        if year and year >= 2020:
            queries.append(f"{{name}} rookie")
        
        # Graded versions
        queries.append(f"{{name}} PSA")
        
        return queries
    
    def _write_targets_file(self, targets: List[Dict]):
        """Write targets to targets.yaml"""
        
        # Build YAML structure
        data = {
            'players': targets,
            'schedule': {
                'daily_import_time': '02:00',
                'days_back': 7,
                'import_sales': True,
                'import_listings': True,
                'calculate_trends': True,
                'generate_reports': True
            },
            'reports': {
                'output_dir': 'reports',
                'top_cards_limit': 25,
                'email_enabled': False,
                'email_to': 'your-email@example.com'
            },
            'metadata': {
                'last_updated': datetime.now().isoformat(),
                'auto_discovery_enabled': True,
                'total_targets': len(targets)
            }
        }
        
        # Write to file
        with open(self.TARGETS_FILE, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"💾 Wrote {len(targets)} targets to {self.TARGETS_FILE}")
    
    def add_manual_favorite(self, player_name: str, sport: str, queries: List[str]):
        """Add a manual favorite (preserved across auto-updates)"""
        
        favorite = {
            'name': player_name,
            'sport': sport,
            'queries': queries,
            'favorite': True,
            'added_at': datetime.now().isoformat()
        }
        
        self.manual_favorites.append(favorite)
        logger.info(f"⭐ Added manual favorite: {player_name}")
    
    def remove_manual_favorite(self, player_name: str):
        """Remove a manual favorite"""
        
        self.manual_favorites = [
            f for f in self.manual_favorites 
            if f['name'] != player_name
        ]
        
        logger.info(f"🗑️ Removed manual favorite: {player_name}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Example: Update targets with mock discovered cards
    service = TargetDiscoveryService()
    
    mock_discoveries = [
        {
            'player_name': 'Victor Wembanyama',
            'sport': 'Basketball',
            'card_year': 2023,
            'card_set': 'Prizm',
            'sales_volume': 150,
            'avg_price': 125.50,
            'price_velocity': 18.4,
            'discovery_score': 85.2,
            'discovered_at': datetime.now().isoformat()
        }
    ]
    
    summary = service.update_targets(mock_discoveries)
    print(f"\n✅ Targets updated: {summary}")
