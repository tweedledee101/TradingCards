#!/usr/bin/env python3
"""
Scrape Active eBay Listings for Liquid Cards

Finds cards available NOW on eBay that are:
1. Liquid (proven sellers)
2. Priced below market average
3. Profitable after fees
"""
from backend.utils.database import SessionLocal
from backend.models import Card, Sale
from backend.scrapers.ebay_scraper import EbayScraper
from sqlalchemy import func
from datetime import datetime, timedelta
import time

def get_liquid_cards(min_sales=3, days=30, limit=20):
    """Get top liquid cards"""
    db = SessionLocal()
    cutoff = datetime.now() - timedelta(days=days)
    
    cards = db.query(
        Card.player_name,
        Card.card_year,
        Card.card_set,
        Card.card_number,
        func.count(Sale.id).label('sales_count'),
        func.avg(Sale.sale_price).label('avg_price')
    ).join(Sale).filter(
        Card.sport == 'Baseball',
        Card.card_number.isnot(None),
        Sale.sale_date >= cutoff
    ).group_by(
        Card.player_name,
        Card.card_year,
        Card.card_set,
        Card.card_number
    ).having(
        func.count(Sale.id) >= min_sales
    ).order_by(
        func.count(Sale.id).desc()
    ).limit(limit).all()
    
    db.close()
    return cards

def scrape_active_listings(card, scraper):
    """Scrape active eBay listings for a card"""
    query = f"{card.player_name} {card.card_year} {card.card_set} #{card.card_number}"
    
    try:
        # Get active listings
        listings = scraper.get_active_listings(query)
        return listings
    except Exception as e:
        print(f"  Error scraping: {e}")
        return []

def find_opportunities(card, listings, margin=0.15):
    """Find listings below market price"""
    if not listings or card.avg_price is None:
        return []
    
    market_price = float(card.avg_price)
    target_price = market_price * (1 - margin)  # 15% below market
    
    opportunities = []
    for listing in listings:
        try:
            price = float(listing.get('price', 0))
            if price > 0 and price <= target_price:
                profit = market_price - price - (price * 0.13)  # After 13% fees
                roi = (profit / price) * 100 if price > 0 else 0
                
                # Build eBay URL
                item_id = listing.get('ebay_item_id', '')
                # Extract numeric ID from format like "v1|267588102450|0"
                numeric_id = item_id.split('|')[1] if '|' in item_id else item_id
                url = f"https://www.ebay.com/itm/{numeric_id}" if numeric_id else 'N/A'
                
                opportunities.append({
                    'title': listing.get('title', 'Unknown'),
                    'price': price,
                    'market_price': market_price,
                    'profit': profit,
                    'roi': roi,
                    'url': url,
                    'item_id': item_id
                })
        except (ValueError, TypeError):
            continue
    
    return opportunities

if __name__ == '__main__':
    print("=" * 80)
    print("ACTIVE LISTING OPPORTUNITY FINDER")
    print("=" * 80)
    
    # Get liquid cards
    print("\nFetching liquid cards...")
    liquid_cards = get_liquid_cards(min_sales=3, days=30, limit=20)
    print(f"Found {len(liquid_cards)} liquid cards\n")
    
    # Initialize scraper
    scraper = EbayScraper()
    
    all_opportunities = []
    
    for i, card in enumerate(liquid_cards, 1):
        print(f"{i}/{len(liquid_cards)} {card.player_name} {card.card_year} {card.card_set} #{card.card_number}")
        print(f"  Market avg: ${card.avg_price:.2f} ({card.sales_count} sales)")
        
        # Scrape active listings
        listings = scrape_active_listings(card, scraper)
        print(f"  Found {len(listings)} active listings")
        
        # Find opportunities
        opportunities = find_opportunities(card, listings, margin=0.15)
        
        if opportunities:
            print(f"  ✓ {len(opportunities)} opportunities found!")
            for opp in opportunities:
                print(f"    ${opp['price']:.2f} → ${opp['market_price']:.2f} = ${opp['profit']:.2f} profit ({opp['roi']:.1f}% ROI)")
                print(f"    Title: {opp['title'][:80]}")
                print(f"    Link: {opp['url']}")
                all_opportunities.append({
                    'card': f"{card.player_name} {card.card_year} {card.card_set} #{card.card_number}",
                    **opp
                })
        else:
            print(f"  ✗ No opportunities")
        
        print()
        time.sleep(2)  # Rate limiting
    
    # Summary
    print("=" * 80)
    print(f"SUMMARY: Found {len(all_opportunities)} total opportunities")
    print("=" * 80)
    
    if all_opportunities:
        # Sort by ROI
        all_opportunities.sort(key=lambda x: x['roi'], reverse=True)
        
        print("\nTop 10 Opportunities by ROI:\n")
        for i, opp in enumerate(all_opportunities[:10], 1):
            print(f"{i}. {opp['card']}")
            print(f"   Buy: ${opp['price']:.2f} | Sell: ${opp['market_price']:.2f} | Profit: ${opp['profit']:.2f} ({opp['roi']:.1f}% ROI)")
            print(f"   Title: {opp['title'][:100]}")
            print(f"   Link: {opp['url']}")
            print()
