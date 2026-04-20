"""
Want List Scraper - find what cards people are actively looking for.

Scrapes ISO (In Search Of) posts from:
- Reddit /r/baseballcards (weekly ISO threads + individual posts)
- SportsCardForum (ISO section)
- The Bench Trading (want list section)

Use case: match your inventory against what people want.
If you have a card someone is looking for, that's a guaranteed sale.

Usage:
    python backend/scrapers/want_list_scraper.py --source reddit --limit 50
    python backend/scrapers/want_list_scraper.py --source all --match-inventory
"""
from __future__ import annotations

import re
import requests
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta


# Reddit doesn't require auth for public JSON endpoints
REDDIT_BASE = 'https://www.reddit.com'
REDDIT_UA = 'RagnarokGaming/1.0 (trading card research)'

# Subreddits with ISO/want posts
CARD_SUBREDDITS = [
    'baseballcards',
    'baseballcardsales',  # Dedicated buy/sell/trade
]


def scrape_reddit_wants(
    subreddit: str = 'baseballcards',
    limit: int = 50,
    search_terms: List[str] = None,
) -> List[Dict]:
    """Scrape ISO/want posts from a subreddit.

    Reddit's public JSON API (no auth needed for read-only):
    https://www.reddit.com/r/{sub}/search.json?q=ISO&restrict_sr=on&sort=new
    """
    if search_terms is None:
        search_terms = ['ISO', 'in search of', 'looking for', 'want to buy', 'WTB']

    all_wants = []
    seen_ids = set()

    for term in search_terms:
        try:
            resp = requests.get(
                f'{REDDIT_BASE}/r/{subreddit}/search.json',
                params={
                    'q': term,
                    'restrict_sr': 'on',
                    'sort': 'new',
                    't': 'week',  # Last week only
                    'limit': min(limit, 25),
                },
                headers={'User-Agent': REDDIT_UA},
                timeout=10,
            )

            if resp.status_code == 429:
                print(f'  Reddit rate limited, sleeping 60s...')
                time.sleep(60)
                continue

            if resp.status_code != 200:
                print(f'  Reddit HTTP {resp.status_code} for term "{term}"')
                continue

            data = resp.json()
            posts = data.get('data', {}).get('children', [])

            for post in posts:
                pd = post.get('data', {})
                post_id = pd.get('id', '')
                if post_id in seen_ids:
                    continue
                seen_ids.add(post_id)

                title = pd.get('title', '')
                body = pd.get('selftext', '')
                author = pd.get('author', '')
                created = pd.get('created_utc', 0)
                url = f"https://www.reddit.com{pd.get('permalink', '')}"

                # Extract card wants from the post
                cards_wanted = extract_card_wants(title + '\n' + body)

                if cards_wanted:
                    all_wants.append({
                        'source': 'reddit',
                        'subreddit': subreddit,
                        'post_id': post_id,
                        'title': title[:200],
                        'body': body[:500],
                        'author': author,
                        'url': url,
                        'created_at': datetime.utcfromtimestamp(created).isoformat() if created else None,
                        'cards_wanted': cards_wanted,
                    })

            time.sleep(2)  # Reddit rate limit: 1 req/2sec without auth

        except Exception as e:
            print(f'  Reddit error for "{term}": {e}')

    return all_wants


def extract_card_wants(text: str) -> List[Dict]:
    """Extract individual card wants from an ISO post body.

    People write things like:
    - "ISO: 2024 Bowman Chrome Bobby Witt Jr autos"
    - "Looking for any Julio Rodriguez refractors"
    - "WTB: PSA 10 2022 Topps Chrome Elly De La Cruz RC"
    """
    wants = []
    if not text:
        return wants

    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue

        # Skip lines that are clearly not card wants
        if any(skip in line.lower() for skip in ['http', 'www.', 'imgur', 'i have', 'for trade', 'ft:']):
            continue

        # Look for card-like patterns
        has_year = bool(re.search(r'\b(19[89]\d|20\d{2})\b', line))
        has_player = len(line.split()) >= 2  # At least 2 words
        has_card_term = any(t in line.lower() for t in [
            'topps', 'bowman', 'chrome', 'prizm', 'select', 'auto', 'refractor',
            'rc', 'rookie', 'psa', 'bgs', 'sgc', 'parallel', 'numbered',
            'panini', 'heritage', 'stadium club', 'finest',
        ])

        if (has_year and has_player) or has_card_term:
            # Try to extract structured data
            year_match = re.search(r'\b(19[89]\d|20\d{2})\b', line)
            card_year = int(year_match.group(1)) if year_match else None

            wants.append({
                'raw_text': line[:200],
                'card_year': card_year,
                'is_graded': bool(re.search(r'\b(psa|bgs|sgc)\b', line, re.I)),
            })

    return wants


def match_wants_against_inventory(wants: List[Dict], db) -> List[Dict]:
    """Match extracted want list items against your inventory.

    Returns matches where you have a card someone is looking for.
    """
    from sqlalchemy import text

    matches = []
    for want_post in wants:
        for card_want in want_post.get('cards_wanted', []):
            raw = card_want.get('raw_text', '')
            year = card_want.get('card_year')

            if not raw or len(raw) < 10:
                continue

            # Build a search against inventory
            # Simple approach: check if any words from the want match inventory card descriptions
            words = [w for w in raw.lower().split() if len(w) > 3]
            if not words or not year:
                continue

            # Search inventory for cards matching year + key terms
            inv_rows = db.execute(text("""
                SELECT i.id, i.listing_ask_price, c.player_name, c.card_year,
                       c.card_set, c.card_number, c.parallel
                FROM inventory i
                JOIN cards c ON i.card_id = c.id
                WHERE i.status IN ('owned', 'listed')
                  AND c.card_year = :year
                  AND (
                    LOWER(c.player_name) LIKE :term1
                    OR LOWER(c.card_set) LIKE :term1
                    OR LOWER(c.parallel) LIKE :term1
                  )
                LIMIT 5
            """), {'year': year, 'term1': f'%{words[0]}%'}).fetchall()

            for row in inv_rows:
                matches.append({
                    'want_post': {
                        'source': want_post['source'],
                        'author': want_post['author'],
                        'url': want_post['url'],
                        'raw_want': raw,
                    },
                    'inventory_match': {
                        'inventory_id': row[0],
                        'ask_price': float(row[1]) if row[1] else None,
                        'player_name': row[2],
                        'card_year': row[3],
                        'card_set': row[4],
                        'card_number': row[5],
                        'parallel': row[6],
                    },
                })

    return matches


if __name__ == '__main__':
    import argparse, sys, os

    parser = argparse.ArgumentParser(description='Want list scraper')
    parser.add_argument('--source', choices=['reddit', 'all'], default='reddit')
    parser.add_argument('--subreddit', default='baseballcards')
    parser.add_argument('--limit', type=int, default=25)
    parser.add_argument('--match-inventory', action='store_true')
    args = parser.parse_args()

    print(f'Scraping want lists from: {args.source}')

    wants = []
    if args.source in ('reddit', 'all'):
        wants.extend(scrape_reddit_wants(subreddit=args.subreddit, limit=args.limit))

    print(f'\nFound {len(wants)} ISO posts with card wants:')
    total_cards = sum(len(w.get('cards_wanted', [])) for w in wants)
    print(f'Total individual card wants: {total_cards}')

    for w in wants[:10]:
        print(f"\n  [{w['source']}] u/{w['author']}: {w['title'][:80]}")
        print(f"  {w['url']}")
        for card in w['cards_wanted'][:3]:
            print(f"    - {card['raw_text'][:80]}")

    if args.match_inventory and wants:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend', '.env'))
        from contextlib import closing
        from backend.utils.database import SessionLocal

        with closing(SessionLocal()) as db:
            matches = match_wants_against_inventory(wants, db)

        if matches:
            print(f'\n{"="*60}')
            print(f'INVENTORY MATCHES: {len(matches)} cards you have that people want!')
            print(f'{"="*60}')
            for m in matches[:10]:
                inv = m['inventory_match']
                want = m['want_post']
                print(f"\n  You have: {inv['player_name']} {inv['card_year']} {inv['card_set']} #{inv['card_number']} [{inv['parallel']}]")
                print(f"  Price: ${inv['ask_price']:.2f}" if inv['ask_price'] else "  Price: not set")
                print(f"  Wanted by: u/{want['author']} - {want['raw_want'][:60]}")
                print(f"  Contact: {want['url']}")
        else:
            print('\nNo matches between want lists and your inventory.')
