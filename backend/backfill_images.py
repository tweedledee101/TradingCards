"""Backfill image_url for cards missing images. Groups by player to minimize API calls."""
import requests
import time
from backend.scrapers.ebay_scraper import EbayScraper
from backend.utils.database import SessionLocal
from backend.models import Card

def backfill_images():
    db = SessionLocal()
    scraper = EbayScraper()

    # Get cards without images
    cards = db.query(Card).filter(
        (Card.image_url == None) | (Card.image_url == '')
    ).all()

    # Group by player+year+set to batch lookups
    groups = {}
    for card in cards:
        key = (card.player_name, card.card_year, card.card_set)
        groups.setdefault(key, []).append(card)

    print(f"{len(cards)} cards missing images across {len(groups)} search groups")

    # Only search unique player names to minimize API calls
    players_searched = set()
    updated = 0
    api_calls = 0

    for (player, year, card_set), group_cards in groups.items():
        search_key = player
        if search_key in players_searched:
            # Already have results for this player, try matching from DB
            continue
        players_searched.add(search_key)

        print(f"  Searching: {player}...", end=" ", flush=True)
        scraper.headers['Authorization'] = f'Bearer {scraper.token_manager.get_token()}'
        resp = requests.get(
            scraper.base_url + '/item_summary/search',
            headers=scraper.headers,
            params={'q': f'{player} card', 'limit': 200},
            timeout=30
        )
        api_calls += 1
        time.sleep(0.5)

        if resp.status_code != 200:
            print(f"error {resp.status_code}")
            continue

        items = resp.json().get('itemSummaries', [])
        print(f"{len(items)} results")

        # Build lookup: extract card info from each result
        for item in items:
            title = item.get('title', '')
            info = scraper._extract_card_info(title, item.get('condition'))

            # Get image
            image_url = None
            thumbs = item.get('thumbnailImages', [])
            if thumbs:
                image_url = thumbs[0].get('imageUrl')
            if not image_url:
                img = item.get('image', {})
                image_url = img.get('imageUrl') if img else None
            if not image_url:
                continue

            # Try to match to our cards
            for card in cards:
                if card.image_url:
                    continue
                if card.player_name != player:
                    continue
                if card.card_year != info.get('card_year'):
                    continue
                if card.card_set != info.get('card_set'):
                    continue
                parallel = info.get('parallel', 'Base')
                if card.parallel and card.parallel != parallel:
                    continue
                card.image_url = image_url
                updated += 1
                break

    db.commit()
    db.close()
    print(f"\nDone. Updated {updated} cards with images. {api_calls} API calls used.")

if __name__ == '__main__':
    backfill_images()
