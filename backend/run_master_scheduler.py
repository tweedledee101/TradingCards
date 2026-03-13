"""
Master Scheduler - Full Automated Workflow

12 AM: PWCC scraper discovers trending players
1 AM: Discovery aggregator scores players, updates targets.yaml
2 AM: eBay scraper collects data for discovered players
"""

from apscheduler.schedulers.blocking import BlockingScheduler
import subprocess
import sys
from datetime import datetime

scheduler = BlockingScheduler()

def run_pwcc_discovery():
    """12 AM - Scrape PWCC for trending players"""
    print(f"\n{'='*70}")
    print(f"[{datetime.now()}] Running PWCC Discovery...")
    print(f"{'='*70}\n")
    
    result = subprocess.run(
        [sys.executable, "backend/scrape_pwcc_with_nova_act.py"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.stderr:
        print(f"STDERR: {result.stderr}")

def run_discovery_aggregator():
    """1 AM - Analyze PWCC sales, update targets.yaml"""
    print(f"\n{'='*70}")
    print(f"[{datetime.now()}] Running Discovery Aggregator...")
    print(f"{'='*70}\n")
    
    result = subprocess.run(
        [sys.executable, "-m", "backend.run_discovery_integrated", "--now"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.stderr:
        print(f"STDERR: {result.stderr}")

def run_ebay_scraper():
    """2 AM - Scrape eBay for all discovered players"""
    print(f"\n{'='*70}")
    print(f"[{datetime.now()}] Running eBay Scraper...")
    print(f"{'='*70}\n")
    
    result = subprocess.run(
        [sys.executable, "backend/scrape_with_nova_act.py"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.stderr:
        print(f"STDERR: {result.stderr}")

# Schedule jobs
scheduler.add_job(run_pwcc_discovery, 'cron', hour=0, minute=0)  # 12 AM
scheduler.add_job(run_discovery_aggregator, 'cron', hour=1, minute=0)  # 1 AM
scheduler.add_job(run_ebay_scraper, 'cron', hour=2, minute=0)  # 2 AM

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--now', action='store_true', help='Run all jobs immediately for testing')
    args = parser.parse_args()
    
    if args.now:
        print("Running all jobs immediately (test mode)...")
        run_pwcc_discovery()
        run_discovery_aggregator()
        run_ebay_scraper()
        print("\n" + "="*70)
        print("All jobs complete!")
        print("="*70)
    else:
        print("Scheduler started. Jobs will run at:")
        print("  12 AM - PWCC Discovery")
        print("  1 AM  - Discovery Aggregator")
        print("  2 AM  - eBay Scraper")
        print("\nPress Ctrl+C to stop")
        scheduler.start()
