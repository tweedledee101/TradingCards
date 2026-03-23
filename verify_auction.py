#!/usr/bin/env python3
"""
Verify eBay items are actually auctions.

Calls the eBay Browse API for each item in the auction opportunities table
and checks buyingOptions to confirm it's really an auction.

Usage:
    python3 verify_auction.py
    python3 verify_auction.py --item-id 188166755927
"""
import argparse
import requests
import time
from backend.utils.database import SessionLocal
from backend.utils.token_manager import token_manager
from backend.models import Opportunity
from backend.config.settings import config

def verify_item(item_id: str, headers: dict, base_url: str) -> dict:
    """Check a single eBay item's buyingOptions."""
    # eBay item IDs from search come as v1|123456|0 format
    # Try both formats
    for eid in [f"v1|{item_id}|0", item_id]:
        try:
            resp = requests.get(
                f"{base_url}/item/{eid}",
                headers=headers,
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    'item_id': item_id,
                    'title': data.get('title', ''),
                    'buying_options': data.get('buyingOptions', []),
                    'price': data.get('price', {}).get('value'),
                    'current_bid': data.get('currentBidPrice', {}).get('value') if data.get('currentBidPrice') else None,
                    'bid_count': data.get('bidCount', 0),
                    'item_end_date': data.get('itemEndDate'),
                    'status': 'found',
                }
            elif resp.status_code == 404:
                continue
        except Exception as e:
            return {'item_id': item_id, 'status': 'error', 'error': str(e)}
        time.sleep(0.5)

    return {'item_id': item_id, 'status': 'not_found'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--item-id', type=str, help='Verify a single eBay item ID')
    args = parser.parse_args()

    base_url = "https://api.ebay.com/buy/browse/v1" if not config.EBAY_USE_SANDBOX else "https://api.sandbox.ebay.com/buy/browse/v1"
    headers = {
        "Authorization": f"Bearer {token_manager.get_token()}",
        "Content-Type": "application/json"
    }

    if args.item_id:
        result = verify_item(args.item_id, headers, base_url)
        print(f"\nItem: {result.get('item_id')}")
        print(f"Status: {result.get('status')}")
        if result.get('status') == 'found':
            print(f"Title: {result.get('title')}")
            print(f"Buying Options: {result.get('buying_options')}")
            print(f"Price: ${result.get('price')}")
            print(f"Current Bid: ${result.get('current_bid')}")
            print(f"Bid Count: {result.get('bid_count')}")
            print(f"End Date: {result.get('item_end_date')}")
            is_auction = 'AUCTION' in result.get('buying_options', [])
            is_bin = 'FIXED_PRICE' in result.get('buying_options', [])
            if is_auction and not is_bin:
                print(">> PURE AUCTION")
            elif is_auction and is_bin:
                print(">> HYBRID (Auction + BIN)")
            elif is_bin and not is_auction:
                print(">> PURE BIN -- SHOULD NOT BE IN AUCTION RESULTS")
            else:
                print(f">> UNKNOWN: {result.get('buying_options')}")
    else:
        # Verify all auction opportunities in DB
        db = SessionLocal()
        opps = db.query(Opportunity).filter(Opportunity.listing_type == 'auction').all()
        print(f"Verifying {len(opps)} auction opportunities...\n")

        mismatches = 0
        for opp in opps:
            eid = opp.ebay_item_id
            if not eid:
                print(f"  SKIP: {opp.player_name} -- no eBay item ID")
                continue

            result = verify_item(eid, headers, base_url)
            buying = result.get('buying_options', [])
            is_auction = 'AUCTION' in buying
            is_bin = 'FIXED_PRICE' in buying

            status = 'OK'
            if result.get('status') == 'not_found':
                status = 'ENDED/REMOVED'
            elif not is_auction:
                status = 'NOT AN AUCTION'
                mismatches += 1
            elif is_bin:
                status = 'HYBRID'

            tag = 'PASS' if status == 'OK' else status
            print(f"  [{tag}] {opp.player_name} #{opp.card_number} -- ${opp.buy_price} -- {buying}")
            time.sleep(0.5)

        db.close()
        print(f"\n{'='*60}")
        print(f"Total: {len(opps)} | Mismatches: {mismatches}")
        if mismatches == 0:
            print("All auction opportunities verified as actual auctions.")
        else:
            print(f"WARNING: {mismatches} items are NOT auctions!")
