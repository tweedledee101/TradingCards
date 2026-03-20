import json, urllib.request

resp = urllib.request.urlopen("http://localhost:8000/api/opportunities")
data = json.loads(resp.read())

print(f"Total opportunities: {len(data['opportunities'])}")
print()
for o in data["opportunities"][:5]:
    bl = o.get("buy_listings", [])
    print(f"{o['player_name']} - {o['card_year']} {o['card_set']}")
    print(f"  Parallel: {o.get('parallel')}  Card#: {o.get('card_number')}")
    print(f"  Profit: ${o['arbitrage']['net_profit']:.2f}  ROI: {o['arbitrage']['roi']:.0f}%")
    print(f"  Buy Listings: {len(bl)}")
    for l in bl[:4]:
        print(f"    ${l['price']:.2f} | +${l['net_profit']:.2f} | {l['url']}")
    print()
