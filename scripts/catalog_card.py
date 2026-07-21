#!/usr/bin/env python3
"""Catalog a physical card into Inventory + a Ragnarok Exclusive listing.

Takes the card details you'd read straight off the card, looks up the real
SCP comp for that exact player/year/number/parallel (same matching engine
comp_verifier.py uses to verify pipeline opportunities), and creates:
  1. An Inventory row (personal purchase/sale ledger - what Core-tier
     tracking in the Ragnarok Inventory table was always meant to be)
  2. A MarketplaceListing row (what actually shows up in the Shop as
     "Ragnarok Exclusive" and is buyable through Stripe checkout)

Usage:
    python3 scripts/catalog_card.py \
        --player "Bobby Witt Jr" --year 2024 --set "Bowman Chrome" \
        --number 150 --parallel "Refractor" \
        --purchase-price 12.00 --ask-price 20.00 \
        --condition "Near Mint" --category Baseball \
        --seller-id 4

Add --dry-run to see the SCP comp and proposed listing without writing
anything to the database.
"""
import argparse
import sys
from datetime import date
from decimal import Decimal

sys.path.insert(0, '.')

from backend.utils.database import SessionLocal
from backend.models import Card, Inventory, MarketplaceListing
from sqlalchemy import text


def find_or_create_card(db, player, year, card_set, number, parallel):
    existing = db.query(Card).filter(
        Card.player_name.ilike(player),
        Card.card_year == year,
        Card.card_number == (number or None),
        Card.parallel.ilike(parallel) if parallel else Card.parallel.is_(None),
    ).first()
    if existing:
        return existing, False

    card = Card(
        player_name=player,
        card_year=year,
        card_set=card_set,
        card_number=number,
        parallel=parallel or 'Base',
    )
    db.add(card)
    db.flush()
    return card, True


def lookup_scp_comp(db, player, year, number, parallel):
    """Best-effort real comp from the SCP cache for this exact card."""
    rows = db.execute(text("""
        SELECT variants FROM scp_cache
        WHERE player_name ILIKE :player AND card_year = :year
    """), {'player': f'%{player}%', 'year': year}).fetchall()

    best = None
    for row in rows:
        variants = row.variants if isinstance(row.variants, list) else []
        for v in variants:
            v_parallel = (v.get('parallel') or 'Base').lower()
            v_number = str(v.get('card_number') or '')
            score = 0
            if parallel and v_parallel == parallel.lower():
                score += 3
            elif not parallel and v_parallel == 'base':
                score += 2
            if number and v_number and str(number).lower() == v_number.lower():
                score += 2
            if score > (best['score'] if best else 0):
                best = {'score': score, 'price': v.get('ungraded'), 'url': v.get('url'), 'volume': v.get('volume')}

    return best if best and best['score'] >= 2 else None


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--player', required=True)
    p.add_argument('--year', required=True, type=int)
    p.add_argument('--set', dest='card_set', required=True)
    p.add_argument('--number', default=None)
    p.add_argument('--parallel', default=None)
    p.add_argument('--purchase-price', type=float, required=True)
    p.add_argument('--ask-price', type=float, required=True, help='What it lists for on Ragnarok')
    p.add_argument('--condition', default='Near Mint')
    p.add_argument('--category', default='Baseball')
    p.add_argument('--graded', action='store_true')
    p.add_argument('--grade-company', default=None)
    p.add_argument('--grade-value', type=float, default=None)
    p.add_argument('--seller-id', type=int, required=True, help='Your user id (the seller)')
    p.add_argument('--purchase-source', default='box break')
    p.add_argument('--image-url', default=None)
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()

    db = SessionLocal()

    comp = lookup_scp_comp(db, args.player, args.year, args.number, args.parallel)
    print(f"\n{'='*60}")
    print(f"{args.player} - {args.year} {args.card_set} #{args.number or '?'} {args.parallel or 'Base'}")
    print(f"{'='*60}")
    if comp:
        print(f"Real SCP comp: ${comp['price']} (volume: {comp['volume']})")
        print(f"  {comp['url']}")
    else:
        print("No SCP comp found for this exact card - listing without a verified reference price.")

    print(f"\nYour purchase price: ${args.purchase_price:.2f}")
    print(f"Proposed ask price:  ${args.ask_price:.2f}")
    if comp and comp['price']:
        margin = float(comp['price']) - args.ask_price
        print(f"Room below SCP comp: ${margin:.2f}")

    if args.dry_run:
        print("\n--dry-run: nothing written to the database.")
        db.close()
        return

    card, created = find_or_create_card(db, args.player, args.year, args.card_set, args.number, args.parallel)
    print(f"\n{'Created' if created else 'Matched existing'} Card id={card.id}")

    inv = Inventory(
        account_id=1,
        card_id=card.id,
        purchase_date=date.today(),
        purchase_price=Decimal(str(args.purchase_price)),
        purchase_source=args.purchase_source,
        condition=args.condition,
        graded=args.graded,
        grade_company=args.grade_company,
        grade_value=Decimal(str(args.grade_value)) if args.grade_value else None,
        status='listed',
        listing_ask_price=Decimal(str(args.ask_price)),
        listed_at=date.today(),
    )
    db.add(inv)

    title = f"{args.year} {args.card_set} {args.player} #{args.number or ''}".strip()
    if args.parallel and args.parallel.lower() != 'base':
        title += f" {args.parallel}"
    if args.graded and args.grade_company and args.grade_value:
        title += f" {args.grade_company} {args.grade_value}"

    listing = MarketplaceListing(
        seller_id=args.seller_id,
        title=title,
        description=f"{args.condition}. Pulled and shipped personally - Ragnarok Exclusive.",
        price_cents=round(args.ask_price * 100),
        category=args.category,
        condition=args.condition,
        shipping_cents=400,
        image_urls=[args.image_url] if args.image_url else [],
        status='active',
    )
    db.add(listing)
    db.commit()
    db.refresh(inv)
    db.refresh(listing)

    print(f"Inventory id={inv.id} (status=listed)")
    print(f"MarketplaceListing id={listing.id} - now live on /shop as Ragnarok Exclusive")
    db.close()


if __name__ == '__main__':
    main()
