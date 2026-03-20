"""Validate top opportunities - check if SCP rates actually match the cards."""
import json, urllib.request
from backend.utils.database import SessionLocal
from backend.models import Card, Sale, ActiveListing, MarketRate

db = SessionLocal()

resp = urllib.request.urlopen("http://localhost:8000/api/opportunities")
data = json.loads(resp.read())

print(f"Validating top {min(10, len(data['opportunities']))} opportunities...\n")

for opp in data["opportunities"][:10]:
    cid = opp["card_id"]
    card = db.query(Card).get(cid)
    mr = db.query(MarketRate).filter(MarketRate.card_id == cid).first()
    sales = db.query(Sale).filter(Sale.card_id == cid).all()
    listings = db.query(ActiveListing).filter(ActiveListing.card_id == cid).all()

    sale_prices = [float(s.sale_price) for s in sales]
    listing_prices = sorted([float(l.listing_price) for l in listings])

    print(f"{'='*70}")
    print(f"{opp['card_year']} {opp['card_set']} {opp['player_name']} {opp['parallel']}")
    print(f"  Card ID: {cid}")
    print(f"  SCP Ungraded: ${mr.ungraded_price if mr else 'NONE'}")
    print(f"  Sales ({len(sales)}): {['${:.2f}'.format(p) for p in sorted(sale_prices)]}")
    print(f"  Listings ({len(listings)}): {['${:.2f}'.format(p) for p in listing_prices[:5]]}")
    print(f"  Opp says: Buy ${opp['arbitrage']['buy_price']:.2f} -> Sell ${opp['arbitrage']['sell_price']:.2f} -> Profit ${opp['arbitrage']['net_profit']:.2f}")

    # Sanity check: does the SCP rate make sense vs actual sales?
    if mr and sale_prices:
        avg_sale = sum(sale_prices) / len(sale_prices)
        scp = float(mr.ungraded_price) if mr.ungraded_price else 0
        if scp > 0 and avg_sale > 0:
            ratio = scp / avg_sale
            if ratio > 3:
                print(f"  *** WARNING: SCP ${scp:.2f} is {ratio:.1f}x the avg sale ${avg_sale:.2f} - likely WRONG MATCH")
            elif ratio < 0.33:
                print(f"  *** WARNING: SCP ${scp:.2f} is only {ratio:.1f}x the avg sale ${avg_sale:.2f}")
            else:
                print(f"  OK: SCP/avg ratio = {ratio:.1f}x")
    print()

db.close()
