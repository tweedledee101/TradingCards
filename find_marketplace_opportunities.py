#!/usr/bin/env python3
"""
Marketplace Opportunity Pipeline

Searches non-eBay marketplaces (Mercari, COMC) for liquid SCP cards
and stores cross-platform arbitrage opportunities.

Same liquid-first approach as the auction pipeline:
1. Load liquid cards from SCP cache (cards with known volume + price)
2. Search each marketplace for those cards
3. Compare marketplace price vs SCP price (sell on eBay)
4. Store profitable opportunities in DB with listing_type='mercari'/'comc'

Usage:
    python find_marketplace_opportunities.py --platform mercari --limit 50
    python find_marketplace_opportunities.py --platform comc --headed
    python find_marketplace_opportunities.py --platform all --dry-run
"""
import argparse
import sys
import os
import time
from contextlib import closing
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.utils.database import SessionLocal
from backend.utils.job_tracker import JobTracker
from backend.utils.logger import get_logger
from backend.models import Opportunity
from backend.services.liquid_auction_queries import fetch_liquid_cards, build_ebay_query
from backend.services.marketplace_adapter import calculate_arbitrage, PLATFORM_FEES

log = get_logger('marketplace_finder')

FEE_RATE = 0.13  # eBay seller fee (sell side)


def run_marketplace_pipeline(
    platform: str,
    min_profit: float = 10.0,
    max_buy_price: float = 200.0,
    liquid_limit: int = 200,
    headless: bool = True,
    dry_run: bool = False,
    sport: str = 'Baseball',
):
    tracker = JobTracker('marketplace_finder')
    tracker.start(
        total=liquid_limit,
        parameters={
            'platform': platform,
            'min_profit': min_profit,
            'max_buy_price': max_buy_price,
            'liquid_limit': liquid_limit,
            'sport': sport,
        }
    )

    try:
        # Load liquid cards from SCP cache
        with closing(SessionLocal()) as db:
            cards = fetch_liquid_cards(db, min_price=5, max_price=max_buy_price * 2, limit=liquid_limit)

        print(f"Loaded {len(cards)} liquid cards from SCP cache")
        if not cards:
            print("No liquid cards found. Run the SCP volume worm first.")
            tracker.complete(summary={'opportunities_found': 0, 'cards_searched': 0})
            return

        # Group cards by player+year+number (same as auction pipeline)
        from collections import OrderedDict
        grouped = OrderedDict()
        for card in cards:
            q = build_ebay_query(card)  # reuse same query builder (no parallel)
            key = q.lower()
            if key not in grouped:
                grouped[key] = {'query': q, 'cards': []}
            grouped[key]['cards'].append(card)

        queries = list(grouped.values())
        print(f"Grouped into {len(queries)} unique card queries")
        print(f"Platform: {platform} | Budget: ${max_buy_price} | Min profit: ${min_profit}")
        print("=" * 60)

        # Search the marketplace
        opportunities = []
        searched = 0
        errors = 0

        if platform == 'mercari':
            from backend.scrapers.mercari_scraper import search_mercari
            for i, group in enumerate(queries, 1):
                q = group['query']
                scp_cards = group['cards']
                if i % 10 == 0 or i == 1:
                    print(f"  [{i}/{len(queries)}] Searching Mercari: {q[:60]}...")

                try:
                    listings = search_mercari(q, max_results=10, headless=headless)
                    searched += 1

                    for listing in listings:
                        price = listing.get('price', 0)
                        if price <= 0 or price > max_buy_price:
                            continue

                        # Find best SCP match from the card group
                        best_scp = max(scp_cards, key=lambda c: float(c.get('price', 0)))
                        scp_price = float(best_scp['price'])

                        arb = calculate_arbitrage(price, 'mercari', scp_price, 'ebay')
                        if arb['profit'] >= min_profit:
                            opp = {
                                'player_name': best_scp.get('player_name', ''),
                                'card_year': best_scp.get('card_year'),
                                'card_set': best_scp.get('card_set', ''),
                                'card_number': best_scp.get('card_number', ''),
                                'parallel': best_scp.get('parallel', 'Base'),
                                'scp_price': scp_price,
                                'buy_price': price,
                                'profit': arb['profit'],
                                'roi': arb['roi'],
                                'ebay_title': listing.get('title', ''),
                                'ebay_url': listing.get('url', ''),
                                'ebay_item_id': listing.get('item_id', ''),
                                'image_url': listing.get('image_url', ''),
                                'listing_type': 'mercari',
                                'price_source': 'scp_cache',
                                'scp_url': best_scp.get('scp_url'),
                                'scp_volume': best_scp.get('volume', ''),
                            }
                            opportunities.append(opp)
                            print(f"    FOUND: ${price:.2f} Mercari -> ${scp_price:.2f} SCP = ${arb['profit']:.2f} profit")
                            print(f"           {listing.get('title', '')[:80]}")

                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        print(f"    Error: {e}")
                    if errors == 5:
                        print("    (suppressing further errors)")

                # Rate limit between searches
                time.sleep(2.0)
                tracker.update(processed=i)

        elif platform == 'comc':
            from backend.scrapers.comc_scraper import search_comc
            for i, group in enumerate(queries, 1):
                q = group['query']
                scp_cards = group['cards']
                if i % 10 == 0 or i == 1:
                    print(f"  [{i}/{len(queries)}] Searching COMC: {q[:60]}...")

                try:
                    listings = search_comc(q, max_results=10, headless=headless)
                    searched += 1

                    for listing in listings:
                        price = listing.get('price', 0)
                        if price <= 0 or price > max_buy_price:
                            continue

                        best_scp = max(scp_cards, key=lambda c: float(c.get('price', 0)))
                        scp_price = float(best_scp['price'])

                        arb = calculate_arbitrage(price, 'comc', scp_price, 'ebay')
                        if arb['profit'] >= min_profit:
                            opp = {
                                'player_name': best_scp.get('player_name', ''),
                                'card_year': best_scp.get('card_year'),
                                'card_set': best_scp.get('card_set', ''),
                                'card_number': best_scp.get('card_number', ''),
                                'parallel': best_scp.get('parallel', 'Base'),
                                'scp_price': scp_price,
                                'buy_price': price,
                                'profit': arb['profit'],
                                'roi': arb['roi'],
                                'ebay_title': listing.get('title', ''),
                                'ebay_url': listing.get('url', ''),
                                'ebay_item_id': listing.get('item_id', ''),
                                'image_url': listing.get('image_url', ''),
                                'listing_type': 'comc',
                                'price_source': 'scp_cache',
                                'scp_url': best_scp.get('scp_url'),
                                'scp_volume': best_scp.get('volume', ''),
                            }
                            opportunities.append(opp)
                            print(f"    FOUND: ${price:.2f} COMC -> ${scp_price:.2f} SCP = ${arb['profit']:.2f} profit")

                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        print(f"    Error: {e}")

                time.sleep(3.0)  # COMC is slower (Playwright)
                tracker.update(processed=i)

        elif platform == 'goldin':
            from backend.scrapers.goldin_scraper import search_goldin
            for i, group in enumerate(queries, 1):
                q = group['query']
                scp_cards = group['cards']
                if i % 10 == 0 or i == 1:
                    print(f"  [{i}/{len(queries)}] Searching Goldin: {q[:60]}...")

                try:
                    listings = search_goldin(q, max_results=10, status='active')
                    searched += 1

                    for listing in listings:
                        price = listing.get('total_with_premium', 0)
                        if price <= 0 or price > max_buy_price:
                            continue

                        best_scp = max(scp_cards, key=lambda c: float(c.get('price', 0)))
                        scp_price = float(best_scp['price'])

                        arb = calculate_arbitrage(listing.get('price', 0), 'goldin', scp_price, 'ebay')
                        if arb['profit'] >= min_profit:
                            opp = {
                                'player_name': best_scp.get('player_name', ''),
                                'card_year': best_scp.get('card_year'),
                                'card_set': best_scp.get('card_set', ''),
                                'card_number': best_scp.get('card_number', ''),
                                'parallel': best_scp.get('parallel', 'Base'),
                                'scp_price': scp_price,
                                'buy_price': price,
                                'profit': arb['profit'],
                                'roi': arb['roi'],
                                'ebay_title': listing.get('title', ''),
                                'ebay_url': listing.get('url', ''),
                                'ebay_item_id': listing.get('item_id', ''),
                                'image_url': listing.get('image_url', ''),
                                'listing_type': 'goldin',
                                'price_source': 'scp_cache',
                                'scp_url': best_scp.get('scp_url'),
                                'scp_volume': best_scp.get('volume', ''),
                            }
                            opportunities.append(opp)
                            print(f"    FOUND: ${listing['price']:.0f} bid + 20% = ${price:.0f} -> ${scp_price:.0f} SCP = ${arb['profit']:.0f} profit")

                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        print(f"    Error: {e}")

                time.sleep(1.0)  # Algolia is fast, light rate limit
                tracker.update(processed=i)

        # Store opportunities
        print(f"\n{'=' * 60}")
        print(f"RESULTS: {len(opportunities)} {platform} opportunities found")
        print(f"Searched: {searched} queries | Errors: {errors}")

        if opportunities and not dry_run:
            db = SessionLocal()
            stored = 0
            for opp in opportunities:
                try:
                    from sqlalchemy import text as _t
                    existing = db.execute(
                        _t("SELECT id FROM opportunities WHERE ebay_item_id = :eid LIMIT 1"),
                        {"eid": opp['ebay_item_id']},
                    ).first()
                    if existing:
                        continue

                    row = Opportunity(
                        player_name=opp['player_name'],
                        card_year=opp['card_year'],
                        card_set=opp['card_set'],
                        card_number=opp['card_number'],
                        parallel=opp['parallel'],
                        scp_price=opp['scp_price'],
                        buy_price=opp['buy_price'],
                        shipping=0,
                        profit=opp['profit'],
                        roi=opp['roi'],
                        ebay_title=opp['ebay_title'],
                        ebay_url=opp['ebay_url'],
                        ebay_item_id=opp['ebay_item_id'],
                        image_url=opp.get('image_url'),
                        listing_type=opp['listing_type'],
                        price_source=opp['price_source'],
                        scp_url=opp.get('scp_url'),
                        scp_volume=opp.get('scp_volume'),
                        verification_status='pending',
                        sport=sport,
                        scan_id=tracker.run_id,
                    )
                    db.add(row)
                    db.commit()
                    stored += 1
                except Exception as e:
                    db.rollback()
                    log.warn(f'DB write failed: {e}', category='db_write_error')
            db.close()
            print(f"Stored {stored} new opportunities in DB")
        elif dry_run:
            print("[DRY RUN] No DB writes")

        for i, opp in enumerate(opportunities[:20], 1):
            print(f"\n{i}. {opp['player_name']} {opp['card_year']} #{opp['card_number']} [{opp['parallel']}]")
            print(f"   ${opp['buy_price']:.2f} {platform} -> ${opp['scp_price']:.2f} SCP = ${opp['profit']:.2f} profit ({opp['roi']}% ROI)")
            print(f"   {opp['ebay_url']}")

        tracker.complete(summary={
            'platform': platform,
            'cards_searched': searched,
            'errors': errors,
            'opportunities_found': len(opportunities),
        })

    except Exception as e:
        log.error(f'Marketplace pipeline failed: {e}', category='pipeline_crash')
        tracker.fail(str(e))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Marketplace Opportunity Pipeline')
    parser.add_argument('--platform', required=True, choices=['mercari', 'comc', 'goldin', 'all'])
    parser.add_argument('--min-profit', type=float, default=10.0)
    parser.add_argument('--max-budget', type=float, default=200.0)
    parser.add_argument('--liquid-limit', type=int, default=200)
    parser.add_argument('--headed', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--sport', default='Baseball')
    args = parser.parse_args()

    platforms = ['mercari', 'comc', 'goldin'] if args.platform == 'all' else [args.platform]
    for plat in platforms:
        print(f"\n{'=' * 60}")
        print(f"MARKETPLACE PIPELINE: {plat.upper()}")
        print(f"{'=' * 60}")
        run_marketplace_pipeline(
            platform=plat,
            min_profit=args.min_profit,
            max_buy_price=args.max_budget,
            liquid_limit=args.liquid_limit,
            headless=not args.headed,
            dry_run=args.dry_run,
            sport=args.sport,
        )
