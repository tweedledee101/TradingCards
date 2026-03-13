"""
Player Name Extractor
Matches eBay listing titles to known players from targets.yaml
"""
import yaml
from pathlib import Path
from typing import Optional

class PlayerExtractor:
    def __init__(self):
        # Load known players from targets.yaml
        config_path = Path(__file__).parent.parent.parent / 'config' / 'targets.yaml'
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        self.players = [(p['name'], p['sport']) for p in config['players']]
    
    def extract_player(self, title: str) -> Optional[tuple]:
        """
        Extract player name and sport from listing title
        
        Args:
            title: eBay listing title
            
        Returns:
            (player_name, sport) tuple or None
        """
        title_lower = title.lower()
        
        # Check each known player
        for player_name, sport in self.players:
            # Split name into parts for flexible matching
            name_parts = player_name.lower().split()
            
            # Check if all name parts are in title
            if all(part in title_lower for part in name_parts):
                return (player_name, sport)
        
        return None

# Global instance
player_extractor = PlayerExtractor()
