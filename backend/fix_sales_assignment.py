"""Re-assign sales to correct cards by re-parsing listing titles.

When set extraction was too generic (e.g. 'Leaf'), multiple different cards
got lumped into one card_id. This script re-parses each sale's listing_title,
finds or creates the correct card, and re-assigns the sale.
"""
from backend.scrapers.ebay_scraper import EbayScraper
from backend.utils.database import SessionLocal
from backend.models import Card, Sale

db = SessionLocal()
s = EbayScraper()

# Get all sales and re-check their card assignment
sales = db.query(Sale).all()
print(f"Checking {len(sales)} sales...")

moved = 0
created = 0

for sale in sales:
    if not sale.listing_title:
        continue

    # Re-parse the title
    info = s._extract_card_info(sale.listing_title)
    new_set = s._extract_card_set(sale.listing_title)
    new_parallel = s._extract_parallel(sale.listing_title)

    if not info.get('card_year') or not new_set:
        continue

    card = sale.card
    if not card:
        continue

    # Check if the sale's parsed set matches the card's set
    if card.card_set == new_set and card.parallel == new_parallel:
        continue  # Already correct

    # Find or create the correct card
    correct_card = db.query(Card).filter(
        Card.player_name == card.player_name,
        Card.card_year == info.get('card_year', card.card_year),
        Card.card_set == new_set,
        Card.parallel == new_parallel,
    ).first()

    if not correct_card:
        correct_card = Card(
            player_name=card.player_name,
            card_year=info.get('card_year', card.card_year),
            card_set=new_set,
            parallel=new_parallel,
            card_number=info.get('card_number'),
            grade_company=info.get('grade_company'),
            grade_value=info.get('grade_value'),
            is_rookie=info.get('is_rookie', False),
            sport=card.sport,
            image_url=card.image_url,
        )
        db.add(correct_card)
        db.flush()
        created += 1

    # Re-assign the sale
    old_set = card.card_set
    sale.card_id = correct_card.id
    moved += 1
    if moved <= 30:
        print(f"  {old_set:25s} -> {new_set:25s} | {sale.listing_title[:55]}")

if moved > 30:
    print(f"  ... and {moved - 30} more")

db.commit()
db.close()
print(f"\nDone. Moved {moved} sales, created {created} new cards.")
