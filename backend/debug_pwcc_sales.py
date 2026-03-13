"""Debug PWCC sales in database"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.utils.database import SessionLocal
from backend.models import Card, Sale
from sqlalchemy import and_

db = SessionLocal()

cutoff = datetime.now() - timedelta(days=7)

print("PWCC Sales in last 7 days:")
print("=" * 60)

sales = db.query(Sale).filter(
    and_(
        Sale.source == 'pwcc',
        Sale.sale_date >= cutoff
    )
).all()

print(f"Total PWCC sales: {len(sales)}\n")

for sale in sales:
    card = db.query(Card).get(sale.card_id)
    if card:
        print(f"Player: {card.player_name}")
        print(f"  Card: {card.card_year} {card.card_set}")
        print(f"  Price: ${sale.sale_price}")
        print(f"  Date: {sale.sale_date}")
        print()

# Group by player
from collections import defaultdict
by_player = defaultdict(list)

for sale in sales:
    card = db.query(Card).get(sale.card_id)
    if card and card.player_name:
        by_player[card.player_name].append(float(sale.sale_price))

print("\nGrouped by player:")
print("=" * 60)
for player, prices in by_player.items():
    print(f"{player}: {len(prices)} sales, avg ${sum(prices)/len(prices):.2f}")

db.close()
