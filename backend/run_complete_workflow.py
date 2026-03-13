"""
Complete Workflow - Volume-Based Discovery System

Phase 1: Volume Discovery (find top players by sales volume)
Phase 2: Budget Filtering (keep only players with cards in budget)
Phase 3: Update Targets (write to targets.yaml)
Phase 4: Scrape Data (get real eBay data for those 20 players)
Phase 5: Find Opportunities (analyze for arbitrage)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.services.volume_discovery import VolumeDiscovery
from backend.services.target_discovery import TargetDiscoveryService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main(user_budget: float = 100.0):
    """Run complete workflow"""
    
    print("=" * 70)
    print("COMPLETE WORKFLOW - Volume-Based Discovery")
    print("=" * 70)
    
    # Phase 1 & 2: Volume Discovery + Budget Filtering
    print("\n[Phase 1 & 2] Volume Discovery + Budget Filtering")
    print("-" * 70)
    print(f"User Budget: ${user_budget}")
    print("Finding top 20 players by volume with cards in budget...")
    
    discovery = VolumeDiscovery()
    players = discovery.discover_by_volume(
        days=90,  # 1 quarter
        user_budget=user_budget,
        target_count=20
    )
    
    print(f"\n✓ Found {len(players)} players with budget-friendly cards")
    for i, p in enumerate(players[:5], 1):
        print(f"  {i}. {p['player_name']} - {p['sales_volume']} sales (${p['min_price']}-${p['max_price']})")
    if len(players) > 5:
        print(f"  ... and {len(players) - 5} more")
    
    # Phase 3: Update Targets
    print("\n[Phase 3] Update Targets")
    print("-" * 70)
    
    target_service = TargetDiscoveryService()
    summary = target_service.update_targets(players, user_budget)
    
    print(f"✓ Updated targets.yaml:")
    print(f"  Total: {summary['total_targets']} players")
    print(f"  Manual Favorites: {summary['manual_favorites']}")
    print(f"  Auto-Discovered: {summary['auto_discovered']}")
    
    # Phase 4: Scrape Data
    print("\n[Phase 4] Scrape Data")
    print("-" * 70)
    print("Next: Run real eBay scraper")
    print("  sudo /usr/local/bin/docker-compose exec -T api python backend/scrape_ebay_real_simple.py")
    
    # Phase 5: Find Opportunities
    print("\n[Phase 5] Find Opportunities")
    print("-" * 70)
    print("After scraping, run:")
    print("  sudo /usr/local/bin/docker-compose exec -T api python -m backend.run_opportunity_analyzer")
    
    print("\n" + "=" * 70)
    print("WORKFLOW COMPLETE!")
    print("=" * 70)
    print(f"\nTargets updated with {len(players)} budget-friendly players")
    print("Run scrapers to collect data, then analyze for opportunities")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--budget', type=float, default=100.0, help='User budget (default: $100)')
    args = parser.parse_args()
    
    main(user_budget=args.budget)
