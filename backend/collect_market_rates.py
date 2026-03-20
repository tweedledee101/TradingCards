"""
Collect SportsCardsPro market rates for cards in the database.

Strategy:
  1. Cards with stored SCP URLs: scrape product page directly (fast, 100% accurate)
  2. Cards without URLs: search SCP, match by card_number first, store URL for next time

Card number is the primary match key (unique within a set).
Set name is a loose tiebreaker, not a gatekeeper.

Usage:
    /usr/bin/python3 -m backend.collect_market_rates
    /usr/bin/python3 -m backend.collect_market_rates --skip-existing
"""
import sys
import os
import logging
from datetime import date
from collections import defaultdict
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.utils.database import get_db
from backend.models import Card, MarketRate, Sale, ActiveListing
from backend.scrapers.sportscardspro_scraper import SportsCardsProScraper

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)


# ── Matching helpers ──────────────────────────────────────────────

# Color/variant words that distinguish different parallels
_COLOR_WORDS = {
    'red', 'blue', 'green', 'gold', 'orange', 'purple', 'pink', 'black',
    'white', 'silver', 'yellow', 'aqua', 'teal', 'lime', 'sepia', 'ruby',
    'sapphire', 'emerald', 'magenta', 'bronze', 'platinum', 'copper',
}
_VARIANT_WORDS = {
    'superfractor', 'mojo', 'raywave', 'shimmer', 'sparkle', 'speckle',
    'wave', 'geometric', 'diamante', 'camo', 'lava', 'ice', 'neon',
    'atomic', 'hyper', 'mega', 'prizm', 'disco', 'scope',
}
_VAGUE_PARALLELS = {'base', 'auto', 'autograph', 'numbered', 'sp', ''}


def _normalize_parallel(name: str) -> str:
    """Normalize parallel name for eBay<->SCP comparison."""
    n = name.lower().strip()
    words = n.split()
    remove = {'foil', 'chrome', 'parallel', 'sp'}
    words = [w for w in words if w not in remove]
    return ' '.join(words)


def _parallels_conflict(card_parallel: str, scp_parallel: str) -> bool:
    """Return True if two parallels are clearly different cards.

    'Purple Refractor' vs 'Gold Refractor' -> True (conflict)
    'Auto' vs 'Purple Auto' -> False (vague, can't tell)
    'Blue Refractor' vs 'Blue Refractor' -> False (same)
    'Base' vs anything -> False (vague)
    """
    a = card_parallel.lower().strip()
    b = scp_parallel.lower().strip()

    if a == b:
        return False

    a_words = set(a.split())
    b_words = set(b.split())
    if a_words.issubset(_VAGUE_PARALLELS) or b_words.issubset(_VAGUE_PARALLELS):
        return False

    a_colors = a_words & _COLOR_WORDS
    b_colors = b_words & _COLOR_WORDS
    if a_colors and b_colors and a_colors != b_colors:
        return True

    a_variants = a_words & _VARIANT_WORDS
    b_variants = b_words & _VARIANT_WORDS
    if a_variants and b_variants and a_variants != b_variants:
        return True

    return False


def _normalize_card_number(num: str) -> str:
    """Normalize card number: strip #, leading zeros, lowercase."""
    n = num.lower().strip().lstrip('#')
    # Strip leading zeros but keep '0' itself
    n = n.lstrip('0') or '0'
    return n


def _sets_loosely_match(card_set: str, scp_set: str) -> bool:
    """Loose set check -- used as tiebreaker, not gatekeeper.
    
    Returns True if the sets share enough words to be plausibly the same product line.
    'Bowman Chrome' matches 'Bowman Chrome Impact' (superset).
    'Topps Chrome' does NOT match 'Bowman Chrome' (different product).
    """
    if not card_set or not scp_set:
        return True  # Can't verify = don't penalize

    def normalize(s):
        s = s.lower().strip()
        s = re.sub(r'\s*\([^)]*\)\s*$', '', s)  # Remove "(Baseball)" etc.
        # Don't strip 'topps' -- it helps distinguish "Topps Chrome" from "Bowman Chrome"
        return set(s.split())

    c_words = normalize(card_set)
    s_words = normalize(scp_set)

    if not c_words or not s_words:
        return True

    # Both sets must share most of their words
    overlap = c_words & s_words
    if not overlap:
        return False
    # Check overlap against BOTH sides to prevent "Chrome" matching everything
    return (len(overlap) / len(c_words) >= 0.6 and
            len(overlap) / len(s_words) >= 0.4)


def match_scp_to_card(scp_result, cards):
    """Match an SCP result to the best DB card.
    
    Priority: card_number (primary) > parallel > set (tiebreaker)
    Card number is unique within a set, so player + year + card_number = definitive match.
    """
    scp_number = _normalize_card_number(scp_result.get("card_number") or "")
    scp_parallel = _normalize_parallel(scp_result.get("parallel") or "Base")
    scp_set = scp_result.get("set_text") or scp_result.get("card_set") or ""

    if not scp_number:
        return None  # Can't match without card number

    # Pass 1: card_number + parallel match
    for card in cards:
        card_number = _normalize_card_number(card.card_number or "")
        if not card_number or card_number != scp_number:
            continue
        card_parallel = _normalize_parallel(card.parallel or "Base")
        if card_parallel == scp_parallel:
            return card

    # Pass 2: card_number match, but REJECT if parallels clearly conflict
    number_matches = []
    for card in cards:
        card_number = _normalize_card_number(card.card_number or "")
        if card_number and card_number == scp_number:
            if not _parallels_conflict(card.parallel or "Base", scp_result.get("parallel") or "Base"):
                number_matches.append(card)

    if len(number_matches) == 1:
        return number_matches[0]

    if len(number_matches) > 1:
        for card in number_matches:
            if _sets_loosely_match(card.card_set, scp_set):
                return card
        return None  # Ambiguous - don't guess

    return None


# ── Direct URL scraping (fast path) ──────────────────────────────

def collect_via_urls(db, scraper, today, skip_existing=False):
    """Scrape prices for cards that already have stored SCP URLs."""
    # Find all cards with SCP URLs from previous runs
    existing_rates = db.query(MarketRate).filter(
        MarketRate.scp_product_url != None,
        MarketRate.scp_product_url != '',
    ).all()

    # Build card_id -> url mapping (most recent URL per card)
    url_map = {}
    for rate in existing_rates:
        url_map[rate.card_id] = rate.scp_product_url

    if not url_map:
        logger.info("No stored SCP URLs found -- all cards need search")
        return 0, set()

    logger.info(f"Found {len(url_map)} cards with stored SCP URLs")

    updated = 0
    done_card_ids = set()

    for card_id, url in url_map.items():
        if skip_existing:
            has_today = db.query(MarketRate).filter(
                MarketRate.card_id == card_id,
                MarketRate.date_recorded == today,
            ).first()
            if has_today:
                done_card_ids.add(card_id)
                continue

        prices = scraper.scrape_product_page(url)
        if not prices:
            continue

        _upsert_rate(db, card_id, prices, url, today)
        updated += 1
        done_card_ids.add(card_id)

        if updated % 50 == 0:
            db.commit()
            logger.info(f"  Direct URL progress: {updated} updated")

    db.commit()
    logger.info(f"Direct URL scraping: {updated} prices updated")
    return updated, done_card_ids


# ── Search-based collection (for cards without URLs) ─────────────

def build_search_groups(db, done_card_ids=None):
    """Group cards by (player, year, set) for efficient searching.
    
    Only includes cards that have both sales AND active listings (opportunity candidates).
    Excludes cards already handled by direct URL scraping.
    """
    card_ids_with_sales = db.query(Sale.card_id).distinct()
    card_ids_with_listings = db.query(ActiveListing.card_id).distinct()

    query = db.query(Card).filter(
        Card.card_set != None,
        Card.card_set != 'Unknown',
        Card.card_year != None,
        Card.card_number != None,
        Card.card_number != '',
        Card.id.in_(card_ids_with_sales),
        Card.id.in_(card_ids_with_listings),
    )

    cards = query.all()

    # Exclude already-done cards
    if done_card_ids:
        cards = [c for c in cards if c.id not in done_card_ids]

    groups = defaultdict(list)
    for card in cards:
        key = (card.player_name, card.card_year, card.card_set)
        groups[key].append(card)

    logger.info(f"Search needed: {len(groups)} groups, {len(cards)} cards")
    return groups


def search_and_match(scraper, player, year, card_set, cards):
    """Search SCP and match results to DB cards using card-number-first matching.
    
    Single search query: "{player} {year} {set}"
    If no results, try: "{player} {set}"
    
    Returns: dict of {card_id: scp_result} for matched cards.
    """
    queries = [
        f"{player} {year} {card_set}",
        f"{player} {card_set}",
    ]

    matched = {}
    tried = set()

    for query in queries:
        nq = ' '.join(query.lower().split())
        if nq in tried:
            continue
        tried.add(nq)

        results = scraper.search(query)
        if not results:
            continue

        # Match results to DB cards by card number
        for scp in results:
            if not any([scp.get('ungraded'), scp.get('grade_9'), scp.get('psa_10')]):
                continue
            card = match_scp_to_card(scp, cards)
            if card and card.id not in matched:
                matched[card.id] = scp

        if len(matched) >= len(cards):
            break

    return matched


def collect_via_search(db, scraper, today, done_card_ids=None, limit=None, skip_existing=False):
    """Search SCP for cards that don't have stored URLs yet."""
    groups = build_search_groups(db, done_card_ids)
    group_items = list(groups.items())
    if limit:
        group_items = group_items[:limit]

    matched_total = 0
    searched = 0
    skipped = 0

    for (player, year, card_set), cards in group_items:
        if skip_existing:
            card_ids = [c.id for c in cards]
            existing_count = db.query(MarketRate).filter(
                MarketRate.card_id.in_(card_ids),
                MarketRate.source == 'sportscardspro',
                MarketRate.date_recorded == today,
            ).count()
            if existing_count >= len(cards):
                skipped += 1
                continue

        logger.info(f"Group: {player} {year} {card_set} ({len(cards)} cards)")
        searched += 1

        matched = search_and_match(scraper, player, year, card_set, cards)

        if not matched:
            logger.warning(f"  No matches for: {player} {year} {card_set}")
            continue

        for card_id, scp in matched.items():
            url = scp.get("url") or ""
            _upsert_rate(db, card_id, scp, url, today)
            matched_total += 1

        db.commit()
        logger.info(f"  Matched {len(matched)} this group, {matched_total} total")

    logger.info(f"Search: {searched} groups searched, {skipped} skipped, {matched_total} matched")
    return matched_total


# ── Shared helpers ────────────────────────────────────────────────

def _upsert_rate(db, card_id, prices, url, today):
    """Insert or update a market rate record."""
    existing = db.query(MarketRate).filter(
        MarketRate.card_id == card_id,
        MarketRate.source == 'sportscardspro',
        MarketRate.date_recorded == today,
    ).first()

    ungraded = prices.get("ungraded")
    grade_9 = prices.get("grade_9")
    psa_10 = prices.get("psa_10")

    if existing:
        existing.ungraded_price = ungraded
        existing.grade_9_price = grade_9
        existing.psa_10_price = psa_10
        if url:
            existing.scp_product_url = url
    else:
        rate = MarketRate(
            card_id=card_id,
            source='sportscardspro',
            ungraded_price=ungraded,
            grade_9_price=grade_9,
            psa_10_price=psa_10,
            scp_product_url=url or None,
            date_recorded=today,
        )
        db.add(rate)


# ── Main entry point ─────────────────────────────────────────────

def collect_market_rates(limit=None, skip_existing=False):
    db = next(get_db())
    scraper = SportsCardsProScraper(headless=True)
    today = date.today()

    try:
        # Phase 1: Direct URL scraping for cards with stored URLs
        url_count, done_ids = collect_via_urls(db, scraper, today, skip_existing)

        # Phase 2: Search for remaining cards
        search_count = collect_via_search(db, scraper, today, done_ids, limit, skip_existing)

        logger.info(f"DONE! {url_count} via URL + {search_count} via search = {url_count + search_count} total")

    finally:
        scraper.close()
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, help='Limit number of search groups')
    parser.add_argument('--skip-existing', action='store_true', help='Skip cards that already have rates today')
    args = parser.parse_args()
    collect_market_rates(limit=args.limit, skip_existing=args.skip_existing)
