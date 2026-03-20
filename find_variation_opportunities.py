#!/usr/bin/env python3
"""
Find eBay Opportunities Using Variation Data

Matches active eBay listings to specific card variations (with SportsCardsPro prices)
to find real arbitrage opportunities.

Usage:
    python3 find_variation_opportunities.py --max-budget 1000 --min-profit 10 --min-roi 20
"""
from backend.utils.database import SessionLocal
from backend.models import Card
from backend.scrapers.ebay_scraper import EbayScraper
import time
import argparse

def get_variations_with_prices(max_budget=1000, limit=100):
    """Get card variations within budget"""
    db = SessionLocal()

    cards = db.query(Card).filter(
        Card.ungraded_price.isnot(None),
        Card.ungraded_price >= 20,
        Card.ungraded_price <= max_budget,
        Card.card_number.isnot(None)
    ).order_by(
        Card.ungraded_price.asc()
    ).limit(limit).all()

    db.close()
    return cards

def search_ebay_for_variation(card, scraper):
    """Search eBay for a specific card variation"""
    query_parts = [card.player_name, str(card.card_year), card.card_set]

    if card.card_number:
        query_parts.append(f"#{card.card_number}")

    if card.parallel and card.parallel != 'Base':
        query_parts.append(card.parallel)

    query = ' '.join(query_parts)

    try:
        listings = scraper.get_active_listings(query)
        return listings
    except Exception as e:
        print(f"  Error: {e}")
        return []

def match_listing_to_variation(listing_title, card):
    """Check if listing matches the specific variation"""
    title_lower = listing_title.lower()

    if card.player_name.lower() not in title_lower:
        return False

    if card.card_number and card.card_number.lower() not in title_lower:
        return False

    if card.parallel and card.parallel != 'Base':
        parallel_lower = card.parallel.lower()
        parallel_keywords = parallel_lower.split()
        if not all(kw in title_lower for kw in parallel_keywords):
            return False
    else:
        parallel_keywords = ['refractor', 'prizm', 'wave', 'shimmer', 'mojo',
                            'auto', 'autograph', 'numbered', '/']
        if any(kw in title_lower for kw in parallel_keywords):
            return False

    return True

def find_opportunities(card, listings, min_profit=10, min_roi=20):
    """Find listings with minimum profit and ROI after fees"""
    if not listings or not card.ungraded_price:
        return []

    market_price = float(card.ungraded_price)

    opportunities = []

    for listing in listings:
        if not match_listing_to_variation(listing.get('title', ''), card):
            continue

        try:
            price = float(listing.get('price', 0))
            if price > 0:
                profit = market_price - price - (price * 0.13)
                roi = (profit / price) * 100 if price > 0 else 0

                if profit >= min_profit and roi >= min_roi:
                    item_id = listing.get('ebay_item_id', '')
                    numeric_id = item_id.split('|')[1] if '|' in item_id else item_id
                    url = f"https://www.ebay.com/itm/{numeric_id}" if numeric_id else 'N/A'

                    opportunities.append({
                        'title': listing.get('title', 'Unknown'),
                        'price': price,
                        'market_price': market_price,
                        'profit': profit,
                        'roi': roi,
                        'url': url
                    })
        except (ValueError, TypeError):
            continue

    return opportunities

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Find eBay arbitrage opportunities')
    parser.add_argument('--max-budget', type=float, default=1000, help='Maximum card price (default: $1000)')
    parser.add_argument('--min-profit', type=float, default=10, help='Minimum profit after fees (default: $10)')
    parser.add_argument('--min-roi', type=float, default=20, help='Minimum ROI percentage (default: 20%%)')
    parser.add_argument('--limit', type=int, default=100, help='Max variations to check (default: 100)')
    args = parser.parse_args()

    print("=" * 80)
    print("VARIATION-SPECIFIC OPPORTUNITY FINDER")
    print("=" * 80)
    print(f"\nBudget: Up to ${args.max_budget:.0f}")
    print(f"Min Profit: ${args.min_profit:.2f} after 13% eBay fees")
    print(f"Min ROI: {args.min_roi:.0f}%\n")

    print("Fetching card variations with prices...")
    variations = get_variations_with_prices(max_budget=args.max_budget, limit=args.limit)
    print(f"Found {len(variations)} variations to check ($20-${args.max_budget:.0f} range)\n")

    scraper = EbayScraper()
    all_opportunities = []

    for i, card in enumerate(variations, 1):
        variation_name = f"{card.parallel}" if card.parallel != 'Base' else "Base"
        print(f"{i}/{len(variations)} {card.player_name} {card.card_year} {card.card_set} #{card.card_number} [{variation_name}]")
        print(f"  SCP Price: ${card.ungraded_price:.2f}")

        listings = search_ebay_for_variation(card, scraper)
        print(f"  Found {len(listings)} eBay listings")

        opportunities = find_opportunities(card, listings, min_profit=args.min_profit, min_roi=args.min_roi)

        if opportunities:
            print(f"  ✓ {len(opportunities)} MATCHES with ${args.min_profit:.0f}+ profit & {args.min_roi:.0f}%+ ROI!")
            for opp in opportunities:
                print(f"    ${opp['price']:.2f} → ${opp['market_price']:.2f} = ${opp['profit']:.2f} ({opp['roi']:.1f}% ROI)")
                print(f"    {opp['title'][:80]}")
                print(f"    {opp['url']}")
                all_opportunities.append({
                    'card': f"{card.player_name} {card.card_year} {card.card_set} #{card.card_number}",
                    'variation': variation_name,
                    **opp
                })
        else:
            print(f"  ✗ No matches with ${args.min_profit:.0f}+ profit & {args.min_roi:.0f}%+ ROI")

        print()
        time.sleep(2)

    print("=" * 80)
    print(f"SUMMARY: Found {len(all_opportunities)} real opportunities")
    print("=" * 80)

    if all_opportunities:
        all_opportunities.sort(key=lambda x: x['profit'], reverse=True)

        print("\nTop 10 Opportunities by Profit:\n")
        for i, opp in enumerate(all_opportunities[:10], 1):
            print(f"{i}. {opp['card']} [{opp['variation']}]")
            print(f"   Buy: ${opp['price']:.2f} | Market: ${opp['market_price']:.2f} | Profit: ${opp['profit']:.2f} ({opp['roi']:.1f}% ROI)")
            print(f"   {opp['title'][:100]}")
            print(f"   {opp['url']}")
            print()
    else:
        print(f"\nNo opportunities found with:")
        print(f"  - Budget: ${args.max_budget:.0f}")
        print(f"  - Min Profit: ${args.min_profit:.2f}")
        print(f"  - Min ROI: {args.min_roi:.0f}%")
