"""
Daily Discovery Job

Runs at 1 AM (before 2 AM scraper) to auto-populate targets.yaml

Workflow:
1. Discover trending cards from eBay
2. Score and rank discoveries
3. Update targets.yaml (preserve manual favorites)
4. Log summary for monitoring
"""

from backend.scrapers.ebay_discovery_workaround import EbayDiscoveryWorkaround
from backend.services.target_discovery import TargetDiscoveryService
from datetime import datetime
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_discovery():
    """Run daily target discovery"""
    
    start_time = datetime.now()
    logger.info(f"🚀 Starting daily discovery at {start_time}")
    
    try:
        # Step 1: Discover trending cards from eBay
        logger.info("📡 Discovering trending cards from eBay...")
        discovery = EbayDiscoveryWorkaround()
        trending_cards = discovery.discover_trending_cards(days=7)
        
        logger.info(f"✅ Discovered {len(trending_cards)} trending cards")
        
        # Step 2: Update targets.yaml
        logger.info("💾 Updating targets.yaml...")
        service = TargetDiscoveryService()
        summary = service.update_targets(trending_cards)
        
        # Step 3: Log summary
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"""
╔══════════════════════════════════════════════════════════╗
║           DAILY DISCOVERY COMPLETE                       ║
╠══════════════════════════════════════════════════════════╣
║  Total Targets:      {summary['total_targets']:>3}                              ║
║  Manual Favorites:   {summary['manual_favorites']:>3}                              ║
║  Auto-Discovered:    {summary['auto_discovered']:>3}                              ║
║  Duration:           {duration:.1f}s                             ║
║  Updated:            {summary['updated_at'][:19]}        ║
╚══════════════════════════════════════════════════════════╝
        """)
        
        # Display top 10 discoveries
        if trending_cards:
            logger.info("\n🔥 Top 10 Discoveries:")
            for i, card in enumerate(trending_cards[:10], 1):
                logger.info(
                    f"  {i:>2}. {card['player_name']} {card['card_year']} {card['card_set']} "
                    f"(Score: {card['discovery_score']}, Sales: {card['sales_volume']})"
                )
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Discovery failed: {e}", exc_info=True)
        return None


if __name__ == '__main__':
    # Support --now flag for immediate testing
    if '--now' in sys.argv:
        logger.info("⚡ Running discovery immediately (test mode)")
        run_discovery()
    else:
        # Schedule for 1 AM daily
        from apscheduler.schedulers.blocking import BlockingScheduler
        
        scheduler = BlockingScheduler()
        
        # Run at 1 AM daily
        scheduler.add_job(
            run_discovery,
            'cron',
            hour=1,
            minute=0,
            id='daily_discovery'
        )
        
        logger.info("⏰ Discovery scheduler started (runs daily at 1:00 AM)")
        logger.info("   Press Ctrl+C to stop")
        
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("🛑 Discovery scheduler stopped")
