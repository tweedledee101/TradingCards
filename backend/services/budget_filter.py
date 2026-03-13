"""
Phase 2: Budget + Opportunity Filtering

Takes ALL players from Phase 1 (sorted by volume) and finds 20 that have:
- Opportunity cards within user's budget range (min/max)
- Cards that are profitable arbitrage opportunities

Iterates through players in volume order until 20 with opportunities are found.
"""

from typing import List, Dict, Optional
from backend.utils.database import SessionLocal
from backend.models import Card
from backend.services.opportunity_analyzer import OpportunityAnalyzer

class BudgetFilter:
    """Filter players by budget and find opportunity cards"""
    
    def __init__(self):
        self.analyzer = OpportunityAnalyzer()
    
    def find_opportunities(
        self, 
        top_players: List[Dict],
        min_budget: Optional[float] = None,
        max_budget: Optional[float] = None,
        target_count: int = 20
    ) -> List[Dict]:
        """
        Find players with opportunity cards within budget
        
        Args:
            top_players: ALL players from Phase 1 (sorted by volume)
            min_budget: Minimum price (optional)
            max_budget: Maximum price (optional)
            target_count: Number of players to find (default 20)
            
        Returns:
            Up to 20 players with their opportunity cards
        """
        db = SessionLocal()
        try:
            results = []
            
            for player in top_players:
                player_name = player['player_name']
                
                # Find opportunity cards for this player within budget
                opportunities = self._find_player_opportunities(
                    db, 
                    player_name,
                    min_budget,
                    max_budget
                )
                
                if opportunities:
                    results.append({
                        'player_name': player_name,
                        'sport': player['sport'],
                        'sales_volume': player['sales_volume'],
                        'opportunities': opportunities
                    })
                    
                    print(f"  ✓ {len(results):2d}. {player_name:25s} - {len(opportunities)} opportunities")
                    
                    if len(results) >= target_count:
                        break
            
            return results
            
        finally:
            db.close()
    
    def _find_player_opportunities(
        self, 
        db, 
        player_name: str,
        min_budget: Optional[float],
        max_budget: Optional[float]
    ) -> List[Dict]:
        """
        Find all opportunity cards for a player within budget
        
        Returns:
            List of opportunity cards (empty if none found)
        """
        # Get all cards for this player
        cards = db.query(Card).filter(Card.player_name == player_name).all()
        
        opportunities = []
        for card in cards:
            # Analyze card for opportunity
            opp = self.analyzer.analyze_card(db, card.id)
            
            if not opp:
                continue
            
            buy_price = opp['arbitrage']['buy_price']
            
            # Check budget constraints
            if min_budget and buy_price < min_budget:
                continue
            if max_budget and buy_price > max_budget:
                continue
            
            opportunities.append(opp)
        
        return opportunities

if __name__ == '__main__':
    from backend.services.volume_discovery import VolumeDiscovery
    
    print("PHASE 2: Budget + Opportunity Filtering")
    print("=" * 70)
    
    # Get Phase 1 results
    print("\n[Step 1] Getting ALL players by volume...")
    discovery = VolumeDiscovery()
    all_players = discovery.discover_by_volume(days=90, limit=1000)
    print(f"✓ Found {len(all_players)} players with market interest")
    
    # Apply budget + opportunity filter
    min_budget = 50.0
    max_budget = 150.0
    print(f"\n[Step 2] Finding players with opportunities between ${min_budget}-${max_budget}...")
    print("Analyzing for profitable arbitrage...\n")
    
    budget_filter = BudgetFilter()
    results = budget_filter.find_opportunities(
        all_players,
        min_budget=min_budget,
        max_budget=max_budget,
        target_count=20
    )
    
    print("\n" + "=" * 70)
    print(f"RESULT: Found {len(results)} players with opportunities")
    print("=" * 70)
    
    if results:
        print("\nSample opportunities:")
        for i, player in enumerate(results[:3], 1):
            print(f"\n{i}. {player['player_name']} ({player['sport']})")
            print(f"   Sales Volume: {player['sales_volume']}")
            print(f"   Opportunities: {len(player['opportunities'])}")
            for opp in player['opportunities'][:2]:
                print(f"     - Buy ${opp['arbitrage']['buy_price']} → Sell ${opp['arbitrage']['sell_price']} = ${opp['arbitrage']['net_profit']} profit")
    else:
        print("\n⚠️  No opportunities found in this budget range")
        print("Try adjusting budget or adding more data to database")
