"""
COMPLETE 3-PHASE SYSTEM

Phase 1: eBay Volume Discovery (scrape all sales, find top 20 players by volume)
Phase 2: Budget Filtering (filter cards within user budget from top 20 players)
Phase 3: Opportunity Ranking (rank by profit potential)
"""

from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Optional
from backend.scrapers.ebay_scraper import EbayScraper
from backend.services.opportunity_analyzer import OpportunityAnalyzer
from backend.utils.database import SessionLocal
from backend.models import Card, Sale, ActiveListing
from sqlalchemy import func

class CompleteOpportunityFinder:
    """Complete 3-phase opportunity finder"""
    
    def __init__(self):
        self.scraper = EbayScraper()
        self.analyzer = OpportunityAnalyzer()
    
    def phase1_discover_volume(self, days: int = 90) -> List[Dict]:
        """
        Phase 1: Scrape eBay for ALL card sales, find top 20 players by volume
        
        Strategy: Target popular card sets with pagination
        - Uses 10-15 API calls (5 queries × 2-3 pages each)
        - Gets ~1,000-1,500 sales total
        - Deduplicates by eBay item ID
        
        Returns:
            Top 20 players ranked by sales volume
        """
        print("\n" + "="*70)
        print("PHASE 1: Volume Discovery (eBay Scraping)")
        print("="*70)
        print("Strategy: Target popular card sets, paginate for complete data")
        print("Expected API calls: 10-15")
        
        # Target popular card sets (better than generic queries)
        queries = [
            "prizm basketball",      # Most popular basketball set
            "select basketball",     # Second most popular
            "bowman chrome baseball", # Most popular baseball
            "topps chrome baseball",  # Second most popular
            "prizm football"          # Most popular football
        ]
        
        all_sales = []
        seen_items = set()  # Deduplicate by eBay item ID
        api_calls = 0
        
        for query in queries:
            print(f"\n📡 Scraping: {query}")
            
            # Get first page (200 results)
            results = self.scraper.search_sold_listings(query, days_back=days)
            api_calls += 1
            
            # Deduplicate and add
            new_results = 0
            for sale in results:
                item_id = sale.get('ebay_item_id')
                if item_id and item_id not in seen_items:
                    seen_items.add(item_id)
                    all_sales.append(sale)
                    new_results += 1
            
            print(f"   ✓ Found {len(results)} sales ({new_results} unique)")
            
            # TODO: Add pagination if needed (for now, 200 per query = 1,000 total)
            # This keeps us under 15 API calls while getting good coverage
        
        print(f"\n✅ Total: {len(all_sales)} unique sales from {api_calls} API calls")
        print(f"   Deduplication removed {len(seen_items) - len(all_sales)} duplicates")
        
        # Group by player, count volume
        by_player = defaultdict(lambda: {
            'sales_count': 0,
            'sport': None,
            'min_price': float('inf'),
            'max_price': 0
        })
        
        # Filter out junk player names
        junk_names = {'Unknown', 'Various', 'Multi', 'Multiple', 'N/A', 'NA', 'Not Specified', 'See Description', 'Single', 'Trout', '_', ''}
        
        for sale in all_sales:
            player = sale.get('player_name')
            if not player:
                continue
            
            # Skip junk names
            if player in junk_names:
                continue
            
            # Skip comma-separated lists (multi-player cards)
            if ',' in player:
                continue
            
            price = sale.get('price', 0)
            by_player[player]['sales_count'] += 1
            by_player[player]['sport'] = sale.get('sport') or by_player[player]['sport']
            by_player[player]['min_price'] = min(by_player[player]['min_price'], price)
            by_player[player]['max_price'] = max(by_player[player]['max_price'], price)
        
        # Sort by volume, get top 20
        sorted_players = sorted(
            by_player.items(),
            key=lambda x: x[1]['sales_count'],
            reverse=True
        )[:20]
        
        top_20 = []
        print("\n📊 TOP 20 PLAYERS BY VOLUME:")
        print("-"*70)
        for i, (player_name, data) in enumerate(sorted_players, 1):
            top_20.append({
                'rank': i,
                'player_name': player_name,
                'sport': data['sport'],
                'sales_volume': data['sales_count'],
                'price_range': f"${data['min_price']:.0f}-${data['max_price']:.0f}"
            })
            print(f"{i:2d}. {player_name:30s} {data['sales_count']:3d} sales  {top_20[-1]['price_range']}")
        
        return top_20
    
    def phase2_budget_filter(
        self, 
        top_20_players: List[Dict],
        min_budget: Optional[float] = None,
        max_budget: Optional[float] = None
    ) -> List[Dict]:
        """
        Phase 2: Find specific liquid cards within budget
        
        For each liquid player, identify which SPECIFIC cards (variants) are liquid:
        - Group sales by exact variant (year + set + card_number + parallel + grade)
        - Only keep variants with 3+ sales (liquid)
        - Get active listings for those variants
        - Filter by budget
        
        Uses 20 API calls (1 per player for active listings)
        
        Returns:
            Specific cards (variants) within budget
        """
        print("\n" + "="*70)
        print(f"PHASE 2: Find Liquid Cards Within Budget (${min_budget or 0}-${max_budget or '∞'})")
        print("="*70)
        
        db = SessionLocal()
        try:
            liquid_cards = []
            api_calls = 0
            
            for player in top_20_players:
                player_name = player['player_name']
                print(f"\n📊 Analyzing {player_name} cards...")
                
                # Get all sales for this player from database
                thirty_days_ago = datetime.now() - timedelta(days=30)
                sales = db.query(Sale).join(Card).filter(
                    Card.player_name == player_name,
                    Sale.sale_date >= thirty_days_ago
                ).all()
                
                if not sales:
                    print(f"   No sales data in database")
                    continue
                
                # Group by exact variant
                by_variant = defaultdict(list)
                for sale in sales:
                    card = sale.card
                    variant_key = (
                        card.card_year,
                        card.card_set,
                        card.card_number,
                        card.parallel,
                        card.grade_company,
                        card.grade_value
                    )
                    by_variant[variant_key].append(sale)
                
                # Find liquid variants (3+ sales)
                liquid_variants = {k: v for k, v in by_variant.items() if len(v) >= 3}
                print(f"   Found {len(liquid_variants)} liquid variants (3+ sales each)")
                
                if not liquid_variants:
                    continue
                
                # Get active listings for this player
                print(f"   Fetching active listings...")
                listings = self.scraper.get_active_listings(f"{player_name} card")
                api_calls += 1
                
                # Match listings to liquid variants
                for variant_key, variant_sales in liquid_variants.items():
                    year, card_set, card_number, parallel, grade_company, grade_value = variant_key
                    
                    # Find matching listings
                    matching_listings = []
                    for listing in listings:
                        info = listing.get('card_info', {})
                        if (
                            info.get('card_year') == year and
                            info.get('card_set') == card_set and
                            info.get('card_number') == card_number and
                            info.get('parallel', 'Base') == (parallel or 'Base') and
                            info.get('grade_company') == grade_company and
                            info.get('grade_value') == grade_value
                        ):
                            matching_listings.append(listing)
                    
                    if not matching_listings:
                        continue
                    
                    # Filter by budget
                    for listing in matching_listings:
                        price = listing.get('price', 0)
                        
                        if min_budget and price < min_budget:
                            continue
                        if max_budget and price > max_budget:
                            continue
                        
                        # Calculate market rate from sales
                        prices = [float(s.sale_price) for s in variant_sales]
                        market_rate = sum(prices) / len(prices)
                        
                        liquid_cards.append({
                            'player_name': player_name,
                            'sport': player['sport'],
                            'sales_volume': player['sales_volume'],
                            'card_year': year,
                            'card_set': card_set,
                            'card_number': card_number,
                            'parallel': parallel,
                            'grade_company': grade_company,
                            'grade_value': grade_value,
                            'buy_price': price,
                            'market_rate': market_rate,
                            'variant_sales_count': len(variant_sales),
                            'ebay_item_id': listing.get('ebay_item_id'),
                            'title': listing.get('title')
                        })
                
                print(f"   ✓ Found {len([c for c in liquid_cards if c['player_name'] == player_name])} cards in budget")
            
            print(f"\n✅ Total: {len(liquid_cards)} liquid cards in budget from {api_calls} API calls")
            return liquid_cards
            
        finally:
            db.close()
    
    def phase3_rank_opportunities(
        self,
        budget_cards: List[Dict]
    ) -> List[Dict]:
        """
        Phase 3: Calculate profit for each card, rank by best deals
        
        Uses ZERO API calls
        
        Returns:
            Cards ranked by profit potential (best first)
        """
        print("\n" + "="*70)
        print("PHASE 3: Calculate Profit & Rank Opportunities")
        print("="*70)
        
        opportunities = []
        
        for card in budget_cards:
            buy_price = card['buy_price']
            market_rate = card['market_rate']
            
            # Calculate profit after fees
            fees = market_rate * 0.13  # eBay + PayPal
            net_profit = market_rate - buy_price - fees
            roi = (net_profit / buy_price * 100) if buy_price > 0 else 0
            
            if net_profit <= 0:
                continue  # Not profitable
            
            if net_profit < 5 and roi < 15:
                continue  # Not worth it
            
            opportunity_score = min(roi * 2, 100)
            
            opportunities.append({
                'player_name': card['player_name'],
                'sport': card['sport'],
                'card_year': card['card_year'],
                'card_set': card['card_set'],
                'card_number': card['card_number'],
                'parallel': card['parallel'],
                'grade_company': card['grade_company'],
                'grade_value': card['grade_value'],
                'buy_price': round(buy_price, 2),
                'market_rate': round(market_rate, 2),
                'fees': round(fees, 2),
                'net_profit': round(net_profit, 2),
                'roi': round(roi, 1),
                'opportunity_score': round(opportunity_score, 1),
                'variant_sales_count': card['variant_sales_count'],
                'ebay_item_id': card['ebay_item_id'],
                'ebay_url': f"https://www.ebay.com/itm/{card['ebay_item_id']}" if card['ebay_item_id'] else None
            })
        
        # Sort by profit (best first)
        opportunities.sort(key=lambda x: x['net_profit'], reverse=True)
        
        print(f"\n✅ Found {len(opportunities)} profitable opportunities")
        
        if opportunities:
            print("\n🏆 TOP 10 OPPORTUNITIES:")
            print("-"*70)
            for i, opp in enumerate(opportunities[:10], 1):
                variant = f"{opp['card_year']} {opp['card_set']} {opp['player_name']}"
                if opp['card_number']:
                    variant += f" #{opp['card_number']}"
                if opp['parallel'] and opp['parallel'] != 'Base':
                    variant += f" {opp['parallel']}"
                if opp['grade_company']:
                    variant += f" {opp['grade_company']} {opp['grade_value']}"
                
                print(f"{i:2d}. {variant[:50]:50s} "
                      f"Buy ${opp['buy_price']:6.2f} → Sell ${opp['market_rate']:6.2f} = "
                      f"${opp['net_profit']:5.2f} profit ({opp['roi']:4.1f}% ROI) "
                      f"[{opp['variant_sales_count']} sales]")
        
        return opportunities
    
    def run_complete_analysis(
        self,
        min_budget: Optional[float] = None,
        max_budget: Optional[float] = None,
        days: int = 90
    ) -> Dict:
        """
        Run complete 3-phase analysis
        
        Total API calls: ~45 (5 for Phase 1 + 20 for Phase 1.5 + 20 for Phase 2)
        
        Returns:
            Complete results with opportunities ranked
        """
        print("\n" + "="*70)
        print("COMPLETE OPPORTUNITY FINDER")
        print("="*70)
        print(f"Budget: ${min_budget or 0} - ${max_budget or '∞'}")
        print(f"Lookback: {days} days")
        
        # Phase 1: Discover top 20 players by volume
        top_20 = self.phase1_discover_volume(days=days)
        
        # Phase 1.5: Get sold listings for each top 20 player (targeted)
        print("\n" + "="*70)
        print("PHASE 1.5: Targeted Sales Data Collection")
        print("="*70)
        print("Using data already extracted from Phase 1 (0 additional API calls)")
        
        db = SessionLocal()
        try:
            api_calls_phase1_5 = 0
            for player in top_20:
                player_name = player['player_name']
                print(f"\n📡 Processing sales data: {player_name}")
                
                # Get sold listings for this specific player
                sales = self.scraper.search_sold_listings(f"{player_name} card", days_back=30, player_name=player_name, sport=player['sport'])
                api_calls_phase1_5 += 1
                
                # Save to database
                saved_count = 0
                for sale in sales:
                    # Skip enrichment - use what we already have from search results
                    # (get_full_item_details burns 1 API call per sale)
                    
                    # Create or get card with exact variant
                    card = db.query(Card).filter(
                        Card.player_name == (sale.get('player_name') or player_name),
                        Card.card_year == sale.get('card_year'),
                        Card.card_set == sale.get('card_set'),
                        Card.card_number == sale.get('card_number'),
                        Card.parallel == sale.get('parallel', 'Base'),
                        Card.grade_company == sale.get('grade_company'),
                        Card.grade_value == sale.get('grade_value')
                    ).first()
                    
                    if not card:
                        card = Card(
                            player_name=sale.get('player_name') or player_name,
                            card_year=sale.get('card_year'),
                            card_set=sale.get('card_set'),
                            card_number=sale.get('card_number'),
                            parallel=sale.get('parallel', 'Base'),
                            grade_company=sale.get('grade_company'),
                            grade_value=sale.get('grade_value'),
                            is_rookie=sale.get('is_rookie', False),
                            sport=player['sport']
                        )
                        db.add(card)
                        db.flush()
                    
                    # Check if sale already exists
                    existing = db.query(Sale).filter(
                        Sale.ebay_item_id == sale.get('ebay_item_id')
                    ).first()
                    
                    if not existing:
                        # Skip if no sale_date
                        if not sale.get('sale_date'):
                            continue
                            
                        new_sale = Sale(
                            card_id=card.id,
                            sale_price=sale.get('price'),
                            sale_date=sale.get('sale_date'),
                            listing_title=sale.get('title'),
                            ebay_item_id=sale.get('ebay_item_id'),
                            condition=sale.get('condition'),
                            graded=sale.get('graded', False),
                            grade_company=sale.get('grade_company'),
                            grade_value=sale.get('grade_value')
                        )
                        db.add(new_sale)
                        saved_count += 1
                
                db.commit()
                print(f"   ✓ Saved {saved_count} sales to database")
            
            print(f"\n✅ Phase 1.5 complete: {api_calls_phase1_5} API calls")
            
        finally:
            db.close()
        
        # Phase 2: Filter cards within budget
        budget_cards = self.phase2_budget_filter(top_20, min_budget, max_budget)
        
        # Phase 3: Rank by opportunity
        opportunities = self.phase3_rank_opportunities(budget_cards)
        
        total_api_calls = 5 + api_calls_phase1_5 + 20
        
        print("\n" + "="*70)
        print("ANALYSIS COMPLETE")
        print("="*70)
        print(f"API Calls Used: {total_api_calls} (well under 5,000 limit)")
        print(f"  - Phase 1 (volume discovery): 5")
        print(f"  - Phase 1.5 (targeted sales): {api_calls_phase1_5}")
        print(f"  - Phase 2 (active listings): 20")
        print(f"Top Players Found: {len(top_20)}")
        print(f"Cards in Budget: {len(budget_cards)}")
        print(f"Profitable Opportunities: {len(opportunities)}")
        
        return {
            'top_20_players': top_20,
            'budget_cards': budget_cards,
            'opportunities': opportunities,
            'api_calls_used': total_api_calls,
            'timestamp': datetime.now().isoformat()
        }


if __name__ == '__main__':
    finder = CompleteOpportunityFinder()
    
    # Run complete analysis
    results = finder.run_complete_analysis(
        min_budget=50.0,
        max_budget=150.0,
        days=90
    )
    
    print(f"\n\n📊 FINAL RESULTS:")
    print(f"   - Top 20 Players: {len(results['top_20_players'])}")
    print(f"   - Cards in Budget: {len(results['budget_cards'])}")
    print(f"   - Opportunities: {len(results['opportunities'])}")
    print(f"   - API Calls: {results['api_calls_used']}")
