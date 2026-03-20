"""Re-parse card_set for cards where set extraction was too generic (e.g. 'Leaf')."""
from backend.scrapers.ebay_scraper import EbayScraper
from backend.utils.database import SessionLocal
from backend.models import Card, Sale

db = SessionLocal()
s = EbayScraper()

# Find cards with generic set names that need re-parsing
generic_sets = ['Leaf', 'Unknown']
cards = db.query(Card).filter(Card.card_set.in_(generic_sets)).all()
print(f"Found {len(cards)} cards with generic set names")

updated = 0
for card in cards:
    # Get a sale title for this card to re-parse
    sale = db.query(Sale).filter(Sale.card_id == card.id).first()
    if not sale or not sale.listing_title:
        continue

    new_set = s._extract_card_set(sale.listing_title)
    if new_set != card.card_set:
        print(f"  {card.card_set:15s} -> {new_set:30s} | {sale.listing_title[:60]}")
        card.card_set = new_set
        updated += 1

db.commit()
db.close()
print(f"\nUpdated {updated} cards")
