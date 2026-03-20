from backend.utils.database import SessionLocal
from backend.models import ActiveListing

db = SessionLocal()
listings = db.query(ActiveListing).filter(
    (ActiveListing.listing_url == None) | (ActiveListing.listing_url == '')
).all()

for l in listings:
    parts = l.ebay_item_id.split('|')
    legacy_id = parts[1] if len(parts) > 1 else l.ebay_item_id
    l.listing_url = f"https://www.ebay.com/itm/{legacy_id}"

db.commit()
print(f"Updated {len(listings)} listings with URLs")
db.close()
