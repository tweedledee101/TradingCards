#!/usr/bin/env python3
"""
eBay-Only Opportunity Finder

Uses eBay sold listings to calculate market price and liquidity,
then finds active listings below that price.

Usage:
    python3 find_ebay_only_opportunities.py --max-budget 1000 --min-profit 10 --min-sales 10
"""
from backend.scrapers.ebay_scraper import EbayScraper
from backend.utils.database import SessionLocal
from backend.models import Card
import argparse
import time
from statistics import mean, stdev

def get_liquid_cards(min_sales=10, days=30):
    """Get cards with high sales volume from database"""
    db = SessionLocal()
    
    # Get cards with card numbers (specific variations)
    cards = db.query(Card).filter(
        Card.card_number.isnot(None)
    ).limit(100).all()
    
    db.close()
    return cards

def analyze_sold_listings(scraper, search_query, days_back=30, min_consistency=0.50):
    """Analyze sold listings to get market data, trimming outliers"""
    try:
        sold = scraper.search_sold_listings(search_query, days_back=days_back)
        
        if len(sold) < 5:
            return None
        
        prices = sorted([float(s.get('price', 0)) for s in sold if s.get('price')])
        prices = [p for p in prices if p > 0]
        
        if len(prices) < 5:
            return None
        
        # Trim top/bottom 10% to remove graded outliers and damaged cards
        trim = max(1, len(prices) // 10)
        trimmed = prices[trim:-trim] if len(prices) > 4 else prices
        
        if len(trimmed) < 3:
            return None
        
        avg_price = mean(trimmed)
        median_price = trimmed[len(trimmed) // 2]
        price_stdev = stdev(trimmed) if len(trimmed) > 1 else 0
        consistency = 1 - (price_stdev / avg_price) if avg_price > 0 else 0
        
        if consistency < min_consistency:
            return None
        
        return {
            'avg_price': avg_price,
            'median_price': median_price,
            'sales_count': len(prices),
            'consistency': consistency,
            'sales_per_week': len(prices) / (days_back / 7)
        }
    except Exception as e:
        print(f"  Error analyzing sold: {e}")
        return None

def find_opportunities(scraper, search_query, market_data, max_budget=1000, min_profit=10, min_roi=20):
    """Find active listings below market price"""
    try:
        active = scraper.get_active_listings(search_query)
        
        opportunities = []
        
        for listing in active:
            try:
                price = float(listing.get('price', 0))
                
                if price <= 0 or price > max_budget:
                    continue
                
                profit = market_data['median_price'] - price - (price * 0.13)
                roi = (profit / price) * 100 if price > 0 else 0
                
                if profit >= min_profit and roi >= min_roi:
                    item_id = listing.get('ebay_item_id', '')
                    numeric_id = item_id.split('|')[1] if '|' in item_id else item_id
                    url = f"https://www.ebay.com/itm/{numeric_id}" if numeric_id else 'N/A'
                    
                    opportunities.append({
                        'title': listing.get('title', 'Unknown'),
                        'price': price,
                        'market_price': market_data['median_price'],
                        'profit': profit,
                        'roi': roi,
                        'url': url,
                        'sales_count': market_data['sales_count'],
                        'sales_per_week': market_data['sales_per_week'],
                        'consistency': market_data['consistency']
                    })
            except (ValueError, TypeError):
                continue
        
        return opportunities
    except Exception as e:
        print(f"  Error finding opportunities: {e}")
        return []

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Find eBay arbitrage opportunities using sold data')
    parser.add_argument('--max-budget', type=float, default=1000, help='Maximum card price (default: $1000)')
    parser.add_argument('--min-profit', type=float, default=10, help='Minimum profit after fees (default: $10)')
    parser.add_argument('--min-roi', type=float, default=20, help='Minimum ROI percentage (default: 20%%)')
    parser.add_argument('--min-sales', type=int, default=10, help='Minimum sales in 30 days (default: 10)')
    parser.add_argument('--days', type=int, default=30, help='Days of sold history (default: 30)')
    parser.add_argument('--min-consistency', type=float, default=0.50, help='Min price consistency 0-1 (default: 0.50)')
    args = parser.parse_args()

    print("=" * 80)
    print("EBAY-ONLY OPPORTUNITY FINDER")
    print("=" * 80)
    print(f"\nBudget: Up to ${args.max_budget:.0f}")
    print(f"Min Profit: ${args.min_profit:.2f} after 13% eBay fees")
    print(f"Min ROI: {args.min_roi:.0f}%")
    print(f"Min Sales: {args.min_sales} sales in {args.days} days")
    print(f"Min Consistency: {args.min_consistency*100:.0f}%\n")

    scraper = EbayScraper()
    
    # Get cards from database
    print("Fetching cards from database...")
    cards = get_liquid_cards(min_sales=args.min_sales, days=args.days)
    print(f"Found {len(cards)} cards to check\n")
    
    all_opportunities = []
    
    for i, card in enumerate(cards, 1):
        # Build search query
        query_parts = [card.player_name, str(card.card_year), card.card_set, f"#{card.card_number}"]
        if card.parallel and card.parallel != 'Base':
            query_parts.append(card.parallel)
        
        search_query = ' '.join(query_parts)
        
        print(f"{i}/{len(cards)} {search_query}")
        
        # Analyze sold listings
        market_data = analyze_sold_listings(scraper, search_query, days_back=args.days, min_consistency=args.min_consistency)
        
        if not market_data:
            print(f"  ✗ Not enough sold data")
            print()
            continue
        
        if market_data['sales_count'] < args.min_sales:
            print(f"  ✗ Only {market_data['sales_count']} sales (need {args.min_sales})")
            print()
            continue
        
        print(f"  Market: ${market_data['avg_price']:.2f} avg, {market_data['sales_count']} sales, {market_data['sales_per_week']:.1f}/week")
        
        # Find opportunities
        opportunities = find_opportunities(scraper, search_query, market_data, 
                                          max_budget=args.max_budget, 
                                          min_profit=args.min_profit, 
                                          min_roi=args.min_roi)
        
        if opportunities:
            print(f"  ✓ {len(opportunities)} OPPORTUNITIES!")
            for opp in opportunities:
                print(f"    ${opp['price']:.2f} → ${opp['market_price']:.2f} = ${opp['profit']:.2f} ({opp['roi']:.1f}% ROI)")
                print(f"    {opp['title'][:80]}")
                print(f"    {opp['url']}")
                all_opportunities.append({
                    'search': search_query,
                    **opp
                })
        else:
            print(f"  ✗ No opportunities with ${args.min_profit:.0f}+ profit & {args.min_roi:.0f}%+ ROI")
        
        print()
        time.sleep(2)
    
    print("=" * 80)
    print(f"SUMMARY: Found {len(all_opportunities)} opportunities")
    print("=" * 80)
    
    if all_opportunities:
        all_opportunities.sort(key=lambda x: x['profit'], reverse=True)
        
        print("\nTop 20 by Profit:\n")
        for i, opp in enumerate(all_opportunities[:20], 1):
            print(f"{i}. {opp['search']}")
            print(f"   Buy: ${opp['price']:.2f} | Market: ${opp['market_price']:.2f} | Profit: ${opp['profit']:.2f} ({opp['roi']:.1f}% ROI)")
            print(f"   Liquidity: {opp['sales_count']} sales, {opp['sales_per_week']:.1f}/week, {opp['consistency']*100:.0f}% consistent")
            print(f"   {opp['title'][:100]}")
            print(f"   {opp['url']}")
            print()
