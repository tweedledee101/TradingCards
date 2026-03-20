import json, sys

with open("/tmp/opps.json") as f:
    data = json.load(f)

opps = data.get("opportunities", [])
print(f"Total opportunities: {len(opps)}")
print()

bp = {}
for o in opps:
    bp.setdefault(o["player_name"], []).append(o)

for p in sorted(bp):
    cards = bp[p]
    profits = [c["arbitrage"]["net_profit"] for c in cards]
    rois = [c["arbitrage"]["roi"] for c in cards]
    print(f"  {p}: {len(cards)} opps | profit ${min(profits):.2f}-${max(profits):.2f} | ROI {min(rois):.0f}%-{max(rois):.0f}%")

print()
print("Top 10 by profit:")
top = sorted(opps, key=lambda x: x["arbitrage"]["net_profit"], reverse=True)[:10]
for i, o in enumerate(top, 1):
    a = o["arbitrage"]
    print(f"  {i}. {o['player_name']} {o['card_year']} {o['card_set']} {o.get('parallel','')}")
    print(f"     Buy ${a['buy_price']:.2f} -> Sell ${a['sell_price']:.2f} -> Profit ${a['net_profit']:.2f} ({a['roi']:.0f}% ROI)")
