"""Quick test: does the opportunity analyzer find deals now?"""
import sys
sys.path.insert(0, "/home/tweedledee101/TradingCards")

from backend.services.opportunity_analyzer import OpportunityAnalyzer
from backend.utils.database import SessionLocal

db = SessionLocal()
analyzer = OpportunityAnalyzer()

opps = analyzer.find_opportunities(db, max_budget=500, limit=20)
print(f"Found {len(opps)} opportunities\n")

for i, opp in enumerate(opps[:15], 1):
    arb = opp['arbitrage']
    p = opp.get('parallel') or 'Base'
    g = f"{opp.get('grade_company','')} {opp.get('grade_value','')}" if opp.get('grade_company') else 'Raw'
    src = arb.get('market_source', '?')
    print(f"{i:2d}. {opp['player_name']:20s} {opp['card_year']} {opp['card_set']:15s} {p:12s} {g}")
    print(f"    Buy: ${arb['buy_price']:7.2f}  Sell: ${arb['sell_price']:7.2f}  "
          f"Profit: ${arb['net_profit']:6.2f}  ROI: {arb['roi']:5.1f}%  Source: {src}")
    if arb.get('scp_ungraded'):
        print(f"    SCP: Ungraded=${arb['scp_ungraded']:.2f}  Grade9=${arb.get('scp_grade_9') or 0:.2f}  PSA10=${arb.get('scp_psa_10') or 0:.2f}")
    print()

db.close()
