#!/usr/bin/env python3
"""Generate eBay search URLs for all card variations"""
from backend.utils.database import SessionLocal
from backend.models import Card
from urllib.parse import quote_plus

def generate_ebay_url(player_name, card_year, card_set, card_number, parallel):
    """Generate eBay search URL"""
    # Build search query
    parts = [player_name, str(card_year), card_set]
    
    if card_number:
        parts.append(f"#{card_number}")
    
    if parallel and parallel != 'Base':
        parts.append(parallel)
    
    query = ' '.join(parts)
    encoded = quote_plus(query)
    
    return f"https://www.ebay.com/sch/i.html?_nkw={encoded}"

db = SessionLocal()

# Get all cards with ungraded_price (variations we scraped)
cards = db.query(Card).filter(Card.ungraded_price.isnot(None)).all()

print(f"Generating eBay URLs for {len(cards)} card variations...")

updated = 0
skipped = 0

for card in cards:
    url = generate_ebay_url(
        card.player_name,
        card.card_year,
        card.card_set,
        card.card_number,
        card.parallel
    )
    
    card.ebay_search_url = url
    updated += 1
    
    if updated <= 3:
        print(f"  Sample: {card.player_name} {card.card_year} {card.parallel} -> {url[:80]}...")

db.commit()
db.close()

print(f"✓ Updated {updated} cards with eBay URLs")
