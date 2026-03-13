"""
Run Discovery - Integrated System

Combines PWCC sales analysis with target auto-population.
Runs daily at 1 AM to update targets.yaml.

Workflow:
1. Analyze PWCC sales (last 7 days)
2. Score and rank players
3. Auto-populate targets.yaml
4. Preserve manual favorites
"""

import sys
from pathlib import Path
import logging
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.discovery_aggregator import DiscoveryAggregator
from backend.services.target_discovery import TargetDiscoveryService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def run_discovery():
    """Run complete discovery workflow"""
    
    logger.info("=" * 60)
    logger.info("AUTOMATED TARGET DISCOVERY")
    logger.info("=" * 60)
    
    # Step 1: Discover trending players from PWCC sales
    logger.info("\nStep 1: Analyzing PWCC sales data...")
    aggregator = DiscoveryAggregator()
    discoveries = aggregator.discover_trending_players(days=180, limit=50)
    
    logger.info(f"Found {len(discoveries)} trending players")
    
    if discoveries:
        logger.info("\nTop 10 Discoveries:")
        for i, player in enumerate(discoveries[:10], 1):
            logger.info(f"  {i}. {player['player_name']} - Score: {player['discovery_score']}")
    
    # Step 2: Update targets.yaml
    logger.info("\nStep 2: Updating targets.yaml...")
    service = TargetDiscoveryService()
    summary = service.update_targets(discoveries)
    
    # Step 3: Summary
    logger.info("\n" + "=" * 60)
    logger.info("DISCOVERY COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total Targets: {summary['total_targets']}")
    logger.info(f"Manual Favorites: {summary['manual_favorites']}")
    logger.info(f"Auto-Discovered: {summary['auto_discovered']}")
    logger.info(f"Updated: {summary['updated_at']}")
    logger.info("=" * 60)
    
    return summary


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run automated target discovery')
    parser.add_argument('--now', action='store_true', help='Run immediately (test mode)')
    args = parser.parse_args()
    
    if args.now:
        # Run immediately
        logger.info("Running discovery in TEST MODE (--now flag)")
        summary = run_discovery()
        print(f"\nDiscovery complete: {summary['total_targets']} targets")
    else:
        # Schedule for daily run
        from apscheduler.schedulers.blocking import BlockingScheduler
        
        scheduler = BlockingScheduler()
        
        # Run daily at 1:00 AM
        scheduler.add_job(
            run_discovery,
            'cron',
            hour=1,
            minute=0,
            id='discovery_job'
        )
        
        logger.info("Discovery scheduler started (runs daily at 1:00 AM)")
        logger.info("Press Ctrl+C to stop")
        
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Discovery scheduler stopped")
