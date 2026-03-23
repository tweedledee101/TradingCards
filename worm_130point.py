#!/usr/bin/env python3
"""
130point Data Worm -- Background Sold Comps Builder

Slowly crawls 130point.com building a local cache of eBay sold data.
Runs independently of the pipeline. No eBay API calls consumed.

Rate: ~8 queries/minute (under 130point's 10/min limit)
Coverage: iterates through DB cards that lack recent sold comps
Priority: cards with SCP prices first (validates our pricing),
          then cards without SCP (discovers new pricing data)

Usage:
    python3 worm_130point.py                    # Default: 100 queries
    python3 worm_130point.py --limit 500        # Run longer
    python3 worm_130point.py --player "Juan Soto"  # Focus on one player
    nohup python3 worm_130point.py --limit 1000 > /tmp/worm.log 2>&1 &  # Background
"""
import argparse
import re
import time
from datetime import datetime, timedelta
from backend.scrapers.oneThirtyPoint_scraper import OneThirtyPointScraper
from backend.utils.database import SessionLocal
from backend.utils.logger import get_logger
from backend.models import Card, MarketRate, SoldComp, Opportunity
from sqlalchemy import func, and_

log = get_logger('worm_130point')


def get_cards_to_crawl(db, limit: int, player_name: str = None, from_opportunities: bool = False) -> list:
    """Get cards that need sold comp data, prioritized by value.

    Priority:
    1. Cards from opportunities table (cross-validate pipeline results)
    2. Cards with SCP market rates but no recent sold comps (cross-validate)
    3. Cards with no SCP and no sold comps (discover pricing)
    """
    cutoff = datetime.now() - timedelta(hours=48)

    # Cards that already have recent comps
    recent_comps = db.query(SoldComp.player_name, SoldComp.card_year, SoldComp.card_number)\
        .filter(SoldComp.created_at > cutoff)\
        .distinct().subquery()

    if from_opportunities:
        # Pull directly from opportunities table
        query = db.query(
            Opportunity.player_name,
            Opportunity.card_year,
            Opportunity.card_set,
            Opportunity.card_number,
            Opportunity.parallel,
        ).outerjoin(
            recent_comps,
            and_(
                func.lower(Opportunity.player_name) == func.lower(recent_comps.c.player_name),
                Opportunity.card_year == recent_comps.c.card_year,
                func.lower(Opportunity.card_number) == func.lower(recent_comps.c.card_number),
            )
        ).filter(
            recent_comps.c.player_name.is_(None),
            Opportunity.card_number.isnot(None),
            Opportunity.card_number != '',
        ).distinct().order_by(Opportunity.scp_price.desc())

        if player_name:
            query = query.filter(func.lower(Opportunity.player_name) == player_name.lower())

        return query.limit(limit).all()

    query = db.query(
        Card.player_name,
        Card.card_year,
        Card.card_set,
        Card.card_number,
        Card.parallel,
    ).outerjoin(
        recent_comps,
        and_(
            func.lower(Card.player_name) == func.lower(recent_comps.c.player_name),
            Card.card_year == recent_comps.c.card_year,
            func.lower(Card.card_number) == func.lower(recent_comps.c.card_number),
        )
    ).filter(
        recent_comps.c.player_name.is_(None),  # No recent comps
        Card.card_number.isnot(None),
        Card.card_number != '',
    )

    if player_name:
        query = query.filter(func.lower(Card.player_name) == player_name.lower())

    # Prioritize cards with market rates (cross-validation value)
    cards_with_rates = query.join(
        MarketRate, Card.id == MarketRate.card_id
    ).order_by(MarketRate.ungraded_price.desc()).limit(limit // 2).all()

    # Then cards without rates (discovery value)
    cards_without_rates = query.outerjoin(
        MarketRate, Card.id == MarketRate.card_id
    ).filter(MarketRate.id.is_(None)).limit(limit // 2).all()

    # Deduplicate by (player, year, card_number)
    seen = set()
    result = []
    for card in list(cards_with_rates) + list(cards_without_rates):
        key = (card.player_name.lower(), card.card_year, (card.card_number or '').lower())
        if key not in seen:
            seen.add(key)
            result.append(card)

    return result[:limit]


def build_query(player_name: str, card_year: int, card_set: str,
                card_number: str, parallel: str) -> str:
    """Build a 130point search query from card details."""
    parts = [player_name]
    if card_year:
        parts.append(str(card_year))
    if card_set and card_set.lower() not in ('unknown', 'base'):
        parts.append(card_set)
    if parallel and parallel.lower() not in ('base', 'numbered'):
        parts.append(parallel)
    if card_number:
        parts.append(f'#{card_number}')
    return ' '.join(parts)


def store_comps(db, sales: list, card, query: str):
    """Store sold comps in the database."""
    stored = 0
    for sale in sales:
        comp = SoldComp(
            player_name=card.player_name,
            card_year=card.card_year,
            card_set=card.card_set,
            card_number=card.card_number,
            parallel=card.parallel,
            sale_price=sale['price'],
            sale_type=sale.get('sale_type'),
            sale_date=sale.get('sale_date', ''),
            listing_title=sale.get('title', '')[:500],
            source='130point',
            search_query=query,
        )
        db.add(comp)
        stored += 1
    if stored:
        db.commit()
    return stored


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='130point Data Worm')
    parser.add_argument('--limit', type=int, default=100, help='Max cards to crawl (default: 100)')
    parser.add_argument('--player', type=str, help='Focus on a specific player')
    parser.add_argument('--opportunities', action='store_true',
                        help='Crawl cards from opportunities table first (cross-validation)')
    args = parser.parse_args()

    print("=" * 70)
    print("130POINT DATA WORM -- Background Sold Comps Builder")
    print("=" * 70)
    print(f"Limit: {args.limit} cards | Rate: ~8 queries/min")
    if args.player:
        print(f"Player: {args.player}")
    if args.opportunities:
        print(f"Mode: Opportunity cross-validation")
    print()

    db = SessionLocal()
    scraper = OneThirtyPointScraper()

    cards = get_cards_to_crawl(db, args.limit, args.player, from_opportunities=args.opportunities)
    print(f"Cards to crawl: {len(cards)}")
    print()

    total_comps = 0
    total_queries = 0
    cards_with_data = 0
    cards_empty = 0

    for i, card in enumerate(cards, 1):
        query = build_query(
            card.player_name, card.card_year, card.card_set,
            card.card_number, card.parallel
        )

        sales = scraper.search(query)
        total_queries += 1

        if sales:
            stored = store_comps(db, sales, card, query)
            total_comps += stored
            cards_with_data += 1
            median = scraper.median_price(sales)
            print(f"  [{i}/{len(cards)}] {card.player_name} {card.card_year} #{card.card_number} [{card.parallel}]")
            print(f"    {len(sales)} sold, median ${median:.2f}, stored {stored}")
        else:
            cards_empty += 1
            if i <= 20 or i % 25 == 0:
                print(f"  [{i}/{len(cards)}] {card.player_name} {card.card_year} #{card.card_number} -- no sold data")

        # Progress
        if i % 25 == 0:
            print(f"\n  Progress: {i}/{len(cards)} | {total_comps} comps stored | {cards_with_data} with data, {cards_empty} empty\n")

    db.close()

    print()
    print("=" * 70)
    print(f"WORM COMPLETE")
    print(f"  Queries: {total_queries}")
    print(f"  Cards with data: {cards_with_data}")
    print(f"  Cards empty: {cards_empty}")
    print(f"  Total comps stored: {total_comps}")
    print("=" * 70)
