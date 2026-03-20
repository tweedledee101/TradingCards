"""
Master Pipeline - Run the entire data collection process in one command.

Steps (in order):
1. Discover top players by eBay volume
2. Import sold listings for those players
3. Collect active listings
4. Calculate trends
5. Collect SCP market rates
6. Restart API server (optional)

Usage:
    /usr/bin/python3 -m backend.run_pipeline_full
    /usr/bin/python3 -m backend.run_pipeline_full --sport Baseball --top 20
    /usr/bin/python3 -m backend.run_pipeline_full --skip-discovery --skip-scp
    /usr/bin/python3 -m backend.run_pipeline_full --fresh  # wipe and start clean
"""

import sys
import os
import time
import argparse
import logging
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)


def step_banner(step_num, total, title):
    print(f"\n{'='*70}")
    print(f"  STEP {step_num}/{total}: {title}")
    print(f"{'='*70}\n")


def run_pipeline(
    sport='Baseball',
    top=20,
    days=7,
    fresh=False,
    skip_discovery=False,
    skip_scp=False,
    scp_timeout=1800,
):
    total_steps = 5 - (1 if skip_discovery else 0) - (1 if skip_scp else 0)
    current_step = 0
    start_time = time.time()

    print("\n" + "=" * 70)
    print("  MASTER PIPELINE - Full Data Collection")
    print(f"  Sport: {sport} | Top Players: {top} | Days: {days}")
    print(f"  Fresh: {fresh} | Skip Discovery: {skip_discovery} | Skip SCP: {skip_scp}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # ----------------------------------------------------------------
    # STEP 0 (optional): Wipe all data for fresh start
    # ----------------------------------------------------------------
    if fresh:
        print("\nWiping all existing data for fresh start...")
        from backend.utils.database import SessionLocal
        from backend.models import Card, Sale, ActiveListing, MarketRate
        db = SessionLocal()
        try:
            # Import PriceTrend if it exists
            try:
                from backend.models import PriceTrend
                db.query(PriceTrend).delete()
            except ImportError:
                pass
            db.query(MarketRate).delete()
            db.query(ActiveListing).delete()
            db.query(Sale).delete()
            db.query(Card).delete()
            db.commit()
            print("All data wiped.")
        finally:
            db.close()

    # ----------------------------------------------------------------
    # STEP 1: Discover top players by volume
    # ----------------------------------------------------------------
    if not skip_discovery:
        current_step += 1
        step_banner(current_step, total_steps, "DISCOVER TOP PLAYERS")

        from backend.discover_players import discover_top_players
        players = discover_top_players(days=days, limit=top, sport=sport)

        if not players:
            print("ERROR: No players discovered. Aborting.")
            return False

        print(f"\nTop {len(players)} players by volume:")
        for i, p in enumerate(players, 1):
            print(f"  {i:2d}. {p['player_name']:<28} {p['sales_volume']:>10,} listings")

        PLAYERS = [(p['player_name'], p['sport']) for p in players]
    else:
        current_step += 0
        print("\nSkipping discovery - using players already in database...")
        from backend.utils.database import SessionLocal
        from backend.models import Card
        db = SessionLocal()
        PLAYERS = db.query(Card.player_name, Card.sport).group_by(
            Card.player_name, Card.sport
        ).all()
        db.close()
        PLAYERS = [(name, sport_val or 'Baseball') for name, sport_val in PLAYERS]
        print(f"Found {len(PLAYERS)} players in database.")

    # ----------------------------------------------------------------
    # STEP 2: Import sold listings from eBay
    # ----------------------------------------------------------------
    current_step += 1
    step_banner(current_step, total_steps, "IMPORT SOLD LISTINGS")

    from backend.scrapers.ebay_scraper import EbayScraper
    from backend.services.data_pipeline import DataPipeline
    from backend.utils.database import SessionLocal
    from backend.models import Card, Sale
    from backend.config.sets import get_set_queries

    scraper = EbayScraper()
    pipeline = DataPipeline()
    db = SessionLocal()

    total_sales = 0
    total_api_calls = 0
    for player_name, player_sport in PLAYERS:
        print(f"  {player_name}")

        # Generic query + set-specific queries
        queries = [f"{player_name} card"] + get_set_queries(player_name, player_sport)
        seen_ids = set()  # dedup across queries
        player_imported = 0

        for qi, query in enumerate(queries):
            label = "generic" if qi == 0 else query.split(player_name)[-1].strip()
            print(f"    [{label}]...", end=" ", flush=True)

            sales = scraper.search_sold_listings(
                query, days_back=30, player_name=player_name, sport=player_sport
            )
            total_api_calls += 1

            imported = 0
            for sale in sales:
                if sale['ebay_item_id'] in seen_ids:
                    continue
                seen_ids.add(sale['ebay_item_id'])

                sale['player_name'] = player_name
                sale['sport'] = player_sport

                card = pipeline.find_or_create_card(db, sale)

                existing = db.query(Sale).filter(Sale.ebay_item_id == sale['ebay_item_id']).first()
                if not existing:
                    sale_date = sale['sale_date']
                    if isinstance(sale_date, str):
                        sale_date = sale_date.replace('Z', '+00:00')
                        sale_date = datetime.fromisoformat(sale_date)

                    sale_record = Sale(
                        card_id=card.id,
                        sale_price=sale['price'],
                        sale_date=sale_date,
                        ebay_item_id=sale['ebay_item_id'],
                        listing_title=sale['title'],
                        graded=sale.get('graded', False),
                        grade_company=sale.get('grade_company'),
                        grade_value=sale.get('grade_value')
                    )
                    db.add(sale_record)
                    imported += 1

            db.commit()
            player_imported += imported
            print(f"{len(sales)} found, {imported} new")

        total_sales += player_imported

    db.close()
    print(f"\nTotal: {total_sales} new sales imported ({total_api_calls} API calls)")

    # ----------------------------------------------------------------
    # STEP 3: Collect active listings
    # ----------------------------------------------------------------
    current_step += 1
    step_banner(current_step, total_steps, "COLLECT ACTIVE LISTINGS")

    from backend.collect_active_listings import collect_active_listings
    collect_active_listings()

    # ----------------------------------------------------------------
    # STEP 4: Calculate trends
    # ----------------------------------------------------------------
    current_step += 1
    step_banner(current_step, total_steps, "CALCULATE TRENDS")

    try:
        from backend.calc_trends import calculate_trends
        calculate_trends()
    except ImportError:
        print("Trend calculator not found, skipping...")

    # ----------------------------------------------------------------
    # STEP 5: Collect SCP market rates
    # ----------------------------------------------------------------
    if not skip_scp:
        current_step += 1
        step_banner(current_step, total_steps, "COLLECT SCP MARKET RATES")

        from backend.collect_market_rates import collect_market_rates
        print(f"Timeout: {scp_timeout}s ({scp_timeout//60} minutes)")
        print("This step uses Selenium/Firefox and takes ~6s per card group.\n")

        import signal

        class SCPTimeout(Exception):
            pass

        def timeout_handler(signum, frame):
            raise SCPTimeout()

        try:
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(scp_timeout)
            collect_market_rates(skip_existing=True)
            signal.alarm(0)
        except SCPTimeout:
            print(f"\nSCP collection timed out after {scp_timeout}s. Partial data saved.")
        except Exception as e:
            print(f"\nSCP collection error: {e}. Partial data saved.")

    # ----------------------------------------------------------------
    # DONE
    # ----------------------------------------------------------------
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    print("\n" + "=" * 70)
    print(f"  PIPELINE COMPLETE")
    print(f"  Time: {minutes}m {seconds}s")
    print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Print summary
    from backend.utils.database import SessionLocal
    from backend.models import Card, Sale, ActiveListing, MarketRate
    db = SessionLocal()
    print(f"\n  Cards:          {db.query(Card).count():,}")
    print(f"  Sales:          {db.query(Sale).count():,}")
    print(f"  Active Listings:{db.query(ActiveListing).count():,}")
    print(f"  Market Rates:   {db.query(MarketRate).count():,}")
    print(f"  Players:        {db.query(Card.player_name).distinct().count()}")
    db.close()

    print(f"\nNext: Restart API server and check http://localhost:3000")
    print(f"  kill $(pgrep -f 'backend.api.run') 2>/dev/null")
    print(f"  cd /home/tweedledee101/TradingCards && nohup /usr/bin/python3 -m backend.api.run > /tmp/api.log 2>&1 &")

    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the full data collection pipeline')
    parser.add_argument('--sport', default='Baseball', help='Sport to focus on (default: Baseball)')
    parser.add_argument('--top', type=int, default=20, help='Number of top players (default: 20)')
    parser.add_argument('--days', type=int, default=7, help='Discovery lookback days (default: 7)')
    parser.add_argument('--fresh', action='store_true', help='Wipe all data and start clean')
    parser.add_argument('--skip-discovery', action='store_true', help='Skip player discovery, use existing DB players')
    parser.add_argument('--skip-scp', action='store_true', help='Skip SCP market rate collection')
    parser.add_argument('--scp-timeout', type=int, default=1800, help='SCP collection timeout in seconds (default: 1800)')
    args = parser.parse_args()

    run_pipeline(
        sport=args.sport,
        top=args.top,
        days=args.days,
        fresh=args.fresh,
        skip_discovery=args.skip_discovery,
        skip_scp=args.skip_scp,
        scp_timeout=args.scp_timeout,
    )
