"""
Auction Scanner - Find ending-soon auctions with profit potential

Workflow (mirrors how you actually make money):
  1. Search eBay for auctions ending within N hours for each player
  2. Extract card identity from title
  3. Look up SCP market rate for that card
  4. Calculate: SCP ungraded - current bid - 13% fees = potential profit
  5. Output auctions sorted by end time with profit potential

Usage:
    python3 -m backend.auction_scanner
    python3 -m backend.auction_scanner --hours 12 --min-profit 10
"""
import argparse
import json
import logging
import requests
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from pathlib import Path

from backend.scrapers.ebay_scraper import EbayScraper
from backend.scrapers.sportscardspro_scraper import SportsCardsProScraper
from backend.utils.token_manager import token_manager
from backend.utils.listing_filter import is_noise_listing

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

FEE_RATE = 0.13
DATA_DIR = Path(__file__).parent.parent / 'data'


def _fetch_auctions(player_name: str, hours: int = 24) -> List[Dict]:
    """Fetch auctions ending within `hours` for a player, sorted by end time."""
    headers = {
        'Authorization': f'Bearer {token_manager.get_token()}',
        'Content-Type': 'application/json'
    }
    base_url = 'https://api.ebay.com/buy/browse/v1'

    params = {
        'q': f'{player_name} card',
        'filter': 'buyingOptions:{AUCTION}',
        'sort': 'endTimeSoonest',
        'limit': 200
    }

    try:
        resp = requests.get(
            f'{base_url}/item_summary/search',
            headers=headers, params=params, timeout=30
        )
        if resp.status_code == 401:
            token_manager._refresh_token()
            headers['Authorization'] = f'Bearer {token_manager.get_token()}'
            resp = requests.get(
                f'{base_url}/item_summary/search',
                headers=headers, params=params, timeout=30
            )
        resp.raise_for_status()
        time.sleep(0.5)
    except Exception as e:
        logger.error(f"eBay API error for {player_name}: {e}")
        return []

    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(hours=hours)
    scraper = EbayScraper.__new__(EbayScraper)  # borrow extraction methods only

    auctions = []
    for item in resp.json().get('itemSummaries', []):
        end_str = item.get('itemEndDate')
        if not end_str:
            continue
        end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
        if end_dt > cutoff:
            break  # sorted by endTimeSoonest, so we're done

        title = item.get('title', '')
        if not title or is_noise_listing(title):
            continue

        bid_price = float(item.get('currentBidPrice', {}).get('value', 0))
        if bid_price <= 0:
            continue

        card_info = scraper._extract_card_info(title, item.get('condition'))
        if not card_info.get('card_year') or not card_info.get('card_set'):
            continue

        # Shipping cost
        shipping = 0.0
        for opt in item.get('shippingOptions', []):
            cost = opt.get('shippingCost', {}).get('value')
            if cost:
                shipping = float(cost)
                break

        # Image
        image_url = None
        for img in item.get('additionalImages', []):
            image_url = img.get('imageUrl')
            break
        if not image_url:
            img = item.get('image', {})
            image_url = img.get('imageUrl') if img else None

        hours_left = (end_dt - now).total_seconds() / 3600

        auctions.append({
            'player_name': player_name,
            'title': title,
            'card_year': card_info.get('card_year'),
            'card_set': card_info.get('card_set'),
            'card_number': card_info.get('card_number'),
            'parallel': card_info.get('parallel', 'Base'),
            'grade_company': card_info.get('grade_company'),
            'grade_value': card_info.get('grade_value'),
            'is_rookie': card_info.get('is_rookie', False),
            'current_bid': bid_price,
            'bid_count': item.get('bidCount', 0),
            'shipping': shipping,
            'end_time': end_str,
            'hours_left': round(hours_left, 1),
            'ebay_url': item.get('itemWebUrl', ''),
            'ebay_item_id': item.get('legacyItemId', ''),
            'image_url': image_url,
            'condition': item.get('condition'),
        })

    return auctions


def _lookup_scp(scp_scraper, auction: Dict) -> Optional[Dict]:
    """Look up SCP market rate for an auction's card."""
    rate = scp_scraper.get_market_rate(
        player_name=auction['player_name'],
        card_year=auction['card_year'],
        card_set=auction['card_set'],
        card_number=auction['card_number'],
        parallel=auction['parallel'],
    )
    return rate


def _calc_profit(auction: Dict, scp_rate: Dict) -> Optional[Dict]:
    """Calculate profit potential. Returns enriched auction dict or None."""
    # Pick sell price based on grade
    grade_val = auction.get('grade_value')
    if grade_val and grade_val >= 10 and scp_rate.get('psa_10'):
        sell_price = scp_rate['psa_10']
        price_tier = 'PSA 10'
    elif grade_val and grade_val >= 9 and scp_rate.get('grade_9'):
        sell_price = scp_rate['grade_9']
        price_tier = 'Grade 9'
    elif scp_rate.get('ungraded'):
        sell_price = scp_rate['ungraded']
        price_tier = 'Ungraded'
    else:
        return None

    total_cost = auction['current_bid'] + auction['shipping']
    fees = sell_price * FEE_RATE
    net_profit = sell_price - total_cost - fees
    roi = (net_profit / total_cost * 100) if total_cost > 0 else 0

    # Flag suspicious matches: SCP price wildly above current bid
    flagged = False
    flag_reason = None
    if total_cost > 0 and sell_price / total_cost > 10:
        flagged = True
        flag_reason = f'SCP ${sell_price:.0f} is {sell_price/total_cost:.0f}x the current bid - possible mismatch'

    auction['scp_sell_price'] = round(sell_price, 2)
    auction['scp_price_tier'] = price_tier
    auction['scp_ungraded'] = scp_rate.get('ungraded')
    auction['scp_grade_9'] = scp_rate.get('grade_9')
    auction['scp_psa_10'] = scp_rate.get('psa_10')
    auction['scp_url'] = scp_rate.get('url')
    auction['fees'] = round(fees, 2)
    auction['total_cost'] = round(total_cost, 2)
    auction['net_profit'] = round(net_profit, 2)
    auction['roi'] = round(roi, 1)
    auction['flagged'] = flagged
    auction['flag_reason'] = flag_reason
    return auction


def scan(players: List[str], hours: int = 24, min_profit: float = 10.0) -> List[Dict]:
    """
    Main scan: pull auctions for all players, validate against SCP, return profitable ones.
    """
    logger.info(f"Scanning auctions ending within {hours}h for {len(players)} players (min profit ${min_profit})")

    # Phase 1: Pull all auctions from eBay
    all_auctions = []
    for player in players:
        auctions = _fetch_auctions(player, hours=hours)
        logger.info(f"  {player}: {len(auctions)} auctions ending within {hours}h")
        all_auctions.extend(auctions)
        time.sleep(0.3)

    logger.info(f"Total auctions found: {len(all_auctions)}")
    if not all_auctions:
        return []

    # Sort by end time so most urgent are first
    all_auctions.sort(key=lambda a: a['end_time'])

    # Phase 2: SCP lookup for each unique card
    scp = SportsCardsProScraper(headless=True)
    opportunities = []
    scp_cache = {}  # avoid duplicate lookups

    try:
        for i, auction in enumerate(all_auctions):
            # Cache key: player + year + set + number + parallel
            cache_key = (
                auction['player_name'],
                auction['card_year'],
                auction['card_set'],
                auction.get('card_number'),
                auction['parallel'],
            )

            if cache_key in scp_cache:
                scp_rate = scp_cache[cache_key]
            else:
                scp_rate = _lookup_scp(scp, auction)
                scp_cache[cache_key] = scp_rate
                # Only sleep after actual SCP page loads
                time.sleep(0.5)

            if not scp_rate:
                continue

            result = _calc_profit(auction, scp_rate)
            if result and result['net_profit'] >= min_profit:
                opportunities.append(result)
                logger.info(
                    f"  [{i+1}/{len(all_auctions)}] {auction['player_name']} "
                    f"{auction['card_year']} {auction['card_set']} {auction['parallel']} "
                    f"- Bid ${auction['current_bid']:.2f}, SCP ${result['scp_sell_price']:.2f}, "
                    f"Profit ${result['net_profit']:.2f}, {result['hours_left']}h left"
                )

    finally:
        scp.close()

    opportunities.sort(key=lambda x: x['hours_left'])
    logger.info(f"Found {len(opportunities)} profitable auctions (${min_profit}+ profit)")
    return opportunities


def save_results(opportunities: List[Dict], path: Path = None):
    """Save scan results to JSON cache."""
    if path is None:
        path = DATA_DIR / 'auction_scan.json'
    path.parent.mkdir(exist_ok=True)
    data = {
        'scanned_at': datetime.now(timezone.utc).isoformat(),
        'count': len(opportunities),
        'opportunities': opportunities,
    }
    path.write_text(json.dumps(data, indent=2, default=str))
    logger.info(f"Saved {len(opportunities)} opportunities to {path}")


def get_players() -> List[str]:
    """Get player list from database."""
    from backend.utils.database import SessionLocal
    from backend.models import Card
    from sqlalchemy import distinct
    db = SessionLocal()
    try:
        names = [r[0] for r in db.query(distinct(Card.player_name)).order_by(Card.player_name).all()]
        return names
    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scan eBay auctions for profitable opportunities')
    parser.add_argument('--hours', type=int, default=24, help='Auction ending window in hours (default: 24)')
    parser.add_argument('--min-profit', type=float, default=10.0, help='Minimum net profit (default: $10)')
    parser.add_argument('--players', nargs='+', help='Specific players (default: all from DB)')
    parser.add_argument('--no-save', action='store_true', help='Skip saving to cache file')
    args = parser.parse_args()

    players = args.players or get_players()
    results = scan(players, hours=args.hours, min_profit=args.min_profit)

    if not args.no_save:
        save_results(results)

    if results:
        print(f"\n{'='*90}")
        print(f"AUCTIONS WITH PROFIT POTENTIAL (ending within {args.hours}h, ${args.min_profit}+ profit)")
        print(f"{'='*90}")
        for r in results:
            print(f"\n  {r['player_name']} - {r['card_year']} {r['card_set']} {r['parallel']}")
            print(f"  Current Bid: ${r['current_bid']:.2f} ({r['bid_count']} bids) | Ends in {r['hours_left']}h")
            print(f"  SCP {r['scp_price_tier']}: ${r['scp_sell_price']:.2f} | Net Profit: ${r['net_profit']:.2f} | ROI: {r['roi']:.0f}%")
            print(f"  {r['ebay_url']}")
    else:
        print(f"\nNo auctions found with ${args.min_profit}+ profit potential ending within {args.hours}h")
