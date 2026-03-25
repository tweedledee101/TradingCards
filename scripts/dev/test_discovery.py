"""
Test Automated Target Discovery

Tests the complete discovery workflow with mock data:
1. Mock eBay trending discovery
2. Score and rank cards
3. Update targets.yaml
4. Verify output
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.target_discovery import TargetDiscoveryService
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_mock_discoveries():
    """Generate realistic mock discovered cards"""
    
    return [
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
        },
        {
            'player_name': 'Paul Skenes',
            'sport': 'Baseball',
            'card_year': 2024,
            'card_set': 'Bowman Chrome',
            'sales_volume': 120,
            'avg_price': 45.00,
            'price_velocity': 22.1,
            'discovery_score': 78.5,
            'discovered_at': datetime.now().isoformat()
        },
        {
            'player_name': 'Caitlin Clark',
            'sport': 'Basketball',
            'card_year': 2024,
            'card_set': 'Prizm',
            'sales_volume': 200,
            'avg_price': 85.00,
            'price_velocity': 35.2,
            'discovery_score': 92.1,
            'discovered_at': datetime.now().isoformat()
        },
        {
            'player_name': 'CJ Stroud',
            'sport': 'Football',
            'card_year': 2023,
            'card_set': 'Prizm',
            'sales_volume': 95,
            'avg_price': 65.00,
            'price_velocity': 15.8,
            'discovery_score': 72.3,
            'discovered_at': datetime.now().isoformat()
        },
        {
            'player_name': 'Shohei Ohtani',
            'sport': 'Baseball',
            'card_year': 2024,
            'card_set': 'Topps',
            'sales_volume': 180,
            'avg_price': 150.00,
            'price_velocity': 28.5,
            'discovery_score': 88.7,
            'discovered_at': datetime.now().isoformat()
        },
        {
            'player_name': 'Connor Bedard',
            'sport': 'Hockey',
            'card_year': 2023,
            'card_set': 'Upper Deck',
            'sales_volume': 110,
            'avg_price': 95.00,
            'price_velocity': 19.3,
            'discovery_score': 75.8,
            'discovered_at': datetime.now().isoformat()
        },
        {
            'player_name': 'Anthony Richardson',
            'sport': 'Football',
            'card_year': 2023,
            'card_set': 'Select',
            'sales_volume': 65,
            'avg_price': 35.00,
            'price_velocity': 12.4,
            'discovery_score': 58.2,
            'discovered_at': datetime.now().isoformat()
        },
        {
            'player_name': 'Elly De La Cruz',
            'sport': 'Baseball',
            'card_year': 2023,
            'card_set': 'Bowman',
            'sales_volume': 85,
            'avg_price': 55.00,
            'price_velocity': 25.7,
            'discovery_score': 68.9,
            'discovered_at': datetime.now().isoformat()
        }
    ]


def test_discovery():
    """Test the discovery workflow"""
    
    logger.info("🧪 Testing Automated Target Discovery\n")
    
    # Generate mock discoveries
    logger.info("📊 Generating mock discovered cards...")
    discoveries = generate_mock_discoveries()
    logger.info(f"✅ Generated {len(discoveries)} mock discoveries\n")
    
    # Display discoveries
    logger.info("🔥 Mock Discovered Cards:")
    for i, card in enumerate(discoveries, 1):
        logger.info(
            f"  {i}. {card['player_name']} {card['card_year']} {card['card_set']} "
            f"({card['sport']})"
        )
        logger.info(
            f"     Score: {card['discovery_score']} | Sales: {card['sales_volume']} | "
            f"Avg: ${card['avg_price']:.2f} | Velocity: {card['price_velocity']}%"
        )
    
    # Update targets
    logger.info("\n💾 Updating targets.yaml...")
    service = TargetDiscoveryService()
    summary = service.update_targets(discoveries)
    
    # Display summary
    logger.info(f"""
╔══════════════════════════════════════════════════════════╗
║           DISCOVERY TEST COMPLETE                        ║
╠══════════════════════════════════════════════════════════╣
║  Total Targets:      {summary['total_targets']:>3}                              ║
║  Manual Favorites:   {summary['manual_favorites']:>3}                              ║
║  Auto-Discovered:    {summary['auto_discovered']:>3}                              ║
║  Updated:            {summary['updated_at'][:19]}        ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    logger.info("\n✅ Test complete! Check config/targets.yaml to see results")
    logger.info("   Run: cat config/targets.yaml")


if __name__ == '__main__':
    test_discovery()
