"""
Run Opportunity Analyzer on Existing Data

Analyzes sales and active listings to find arbitrage opportunities.
"""

from backend.utils.database import SessionLocal
from backend.services.opportunity_analyzer import OpportunityAnalyzer
import json

db = SessionLocal()
analyzer = OpportunityAnalyzer()

print("Analyzing existing eBay sales for opportunities...")
print("=" * 70)

# Find all opportunities (no filters)
opportunities = analyzer.find_opportunities(
    db=db,
    limit=100  # Get up to 100 opportunities
)

print("\n" + "=" * 70)
print(f"Found {len(opportunities)} opportunities")
print("=" * 70)

# Show top 10
print("\nTop 10 Opportunities:")
for i, opp in enumerate(opportunities[:10], 1):
    print(f"\n{i}. {opp['player_name']} - {opp['card_year']} {opp['card_set']}")
    print(f"   Buy: ${opp['arbitrage']['buy_price']}")
    print(f"   Sell: ${opp['arbitrage']['sell_price']}")
    print(f"   Profit: ${opp['arbitrage']['net_profit']} ({opp['arbitrage']['roi']}% ROI)")
    print(f"   Confidence: {opp['confidence']}")
    print(f"   Score: {opp['opportunity_score']}/100")

db.close()

print("\nNext: Start frontend to see opportunities")
print("  cd frontend && npm run dev")
