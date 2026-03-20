"""
Collect Active Listings via eBay API

Populates the active_listings table so OpportunityAnalyzer can find deals.
Uses the same eBay Browse API as the sold listings scraper.

Runs generic + set-specific queries per player to surface high-value cards.

Usage:
    python3 -m backend.collect_active_listings
"""

from datetime import date
from backend.scrapers.ebay_scraper import EbayScraper
from backend.utils.database import SessionLocal
from backend.utils.player_extractor import player_extractor
from backend.models import Card, ActiveListing
from backend.config.sets import get_set_queries
from backend.utils.listing_filter import is_noise_listing
from sqlalchemy import func


def collect_active_listings():
    db = SessionLocal()
    scraper = EbayScraper()

    try:
        # Get all players that have sales in the database
        players = db.query(
            Card.player_name, Card.sport
        ).group_by(
            Card.player_name, Card.sport
        ).all()

        print(f"Collecting active listings for {len(players)} players...")
        print("=" * 70)

        # Clear old listings
        deleted = db.query(ActiveListing).delete()
        db.commit()
        print(f"Cleared {deleted} old listings\n")

        total_imported = 0
        api_calls = 0

        for player_name, sport in players:
            print(f"  {player_name}")

            # Generic query + set-specific queries
            queries = [f"{player_name} card"] + get_set_queries(player_name, sport)
            seen_ids = set()  # dedup across queries
            player_imported = 0

            for qi, query in enumerate(queries):
                label = "generic" if qi == 0 else query.split(player_name)[-1].strip()
                print(f"    [{label}]...", end=" ", flush=True)

                listings = scraper.get_active_listings(query)
                api_calls += 1

                q_imported = 0
                for listing in listings:
                    # Dedup across queries for same player
                    if listing['ebay_item_id'] in seen_ids:
                        continue
                    seen_ids.add(listing['ebay_item_id'])

                    card_info = listing.get('card_info', {})
                    if not card_info.get('card_year') or not card_info.get('card_set'):
                        continue

                    # Skip noise listings ("You Pick", "Complete Your Set", lots)
                    if is_noise_listing(listing.get('title', '')):
                        continue

                    # Skip $0 BIN listings (broken data)
                    # Keep $0 auctions — they have a starting price worth watching
                    if listing['price'] <= 0 and listing['listing_type'] != 'auction':
                        continue

                    parallel = card_info.get('parallel') or 'Base'
                    grade_company = card_info.get('grade_company')
                    grade_value = card_info.get('grade_value')
                    card_number = card_info.get('card_number')

                    # Match to existing card in DB - try with card_number first
                    card = None
                    if card_number:
                        card = db.query(Card).filter(
                            Card.player_name == player_name,
                            Card.card_year == card_info['card_year'],
                            Card.card_set == card_info['card_set'],
                            Card.parallel == parallel,
                            Card.card_number == card_number
                        ).first()

                    # Fall back to without card_number
                    if not card:
                        card = db.query(Card).filter(
                            Card.player_name == player_name,
                            Card.card_year == card_info['card_year'],
                            Card.card_set == card_info['card_set'],
                            Card.parallel == parallel
                        ).first()

                    if not card:
                        card = Card(
                            player_name=player_name,
                            card_year=card_info['card_year'],
                            card_set=card_info['card_set'],
                            parallel=parallel,
                            grade_company=grade_company,
                            grade_value=grade_value,
                            sport=sport or 'Unknown',
                            image_url=listing.get('image_url')
                        )
                        db.add(card)
                        db.flush()
                    elif listing.get('image_url') and not card.image_url:
                        card.image_url = listing['image_url']

                    # Skip duplicate ebay_item_id already in DB
                    existing = db.query(ActiveListing).filter(
                        ActiveListing.ebay_item_id == listing['ebay_item_id']
                    ).first()
                    if existing:
                        continue

                    # Construct eBay URL from item ID
                    item_id = listing['ebay_item_id']
                    legacy_id = item_id.split('|')[1] if '|' in item_id else item_id
                    ebay_url = f"https://www.ebay.com/itm/{legacy_id}"

                    new_listing = ActiveListing(
                        card_id=card.id,
                        listing_price=listing['price'],
                        listing_type=listing['listing_type'],
                        ebay_item_id=listing['ebay_item_id'],
                        snapshot_date=date.today(),
                        listing_title=listing.get('title', ''),
                        listing_url=ebay_url
                    )
                    db.add(new_listing)
                    q_imported += 1

                db.commit()
                player_imported += q_imported
                print(f"{q_imported} listings")

            total_imported += player_imported

        print("\n" + "=" * 70)
        print(f"Done. {total_imported} active listings imported. {api_calls} API calls used.")

    finally:
        db.close()


if __name__ == '__main__':
    collect_active_listings()
