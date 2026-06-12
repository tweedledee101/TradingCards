#!/usr/bin/env python3
"""
Export active eBay Buy It Now listings to Whatnot bulk upload CSV.

Usage:
    python ebay_to_whatnot_csv.py [--output whatnot_upload.csv]

Pulls all active BIN listings from your eBay store via Trading API,
then outputs a CSV matching Whatnot's bulk import format:
  Category, Sub Category, Title, Description, Quantity, Type, Price,
  Shipping Profile, Offerable, Hazmat, Condition, Cost Per Item, SKU,
  Image URL 1..8

Upload the CSV at: https://whatnot.com/dashboard/inventory -> Upload CSV
"""
import os
import sys
import csv
import argparse
import base64
import requests
from xml.etree import ElementTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv('backend/.env')

_EBAY_NS = {'e': 'urn:ebay:apis:eBLBaseComponents'}


def _text(el, path):
    found = el.find(path, _EBAY_NS)
    return found.text if found is not None else None


def get_user_token():
    cid = os.getenv('EBAY_CLIENT_ID', '').strip()
    sec = os.getenv('EBAY_CLIENT_SECRET', '').strip()
    refresh = os.getenv('EBAY_USER_REFRESH_TOKEN', '').strip()
    if not refresh:
        return None
    b64 = base64.b64encode(f'{cid}:{sec}'.encode()).decode()
    resp = requests.post(
        'https://api.ebay.com/identity/v1/oauth2/token',
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {b64}',
        },
        data={
            'grant_type': 'refresh_token',
            'refresh_token': refresh,
            'scope': 'https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.inventory',
        },
    )
    if resp.status_code == 200:
        return resp.json().get('access_token')
    print(f"Token error: {resp.status_code} {resp.text[:200]}")
    return None


def fetch_all_active_listings(token):
    """Fetch ALL active listings with full picture URLs (paginated)."""
    all_items = []
    page = 1
    total_pages = 1

    while page <= total_pages:
        resp = requests.post(
            'https://api.ebay.com/ws/api.dll',
            headers={
                'X-EBAY-API-IAF-TOKEN': token,
                'X-EBAY-API-CALL-NAME': 'GetMyeBaySelling',
                'X-EBAY-API-SITEID': '0',
                'X-EBAY-API-COMPATIBILITY-LEVEL': '1209',
                'Content-Type': 'text/xml',
            },
            data=f'''<?xml version="1.0" encoding="utf-8"?>
            <GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
                <Version>1209</Version>
                <ActiveList>
                    <Sort>TimeLeft</Sort>
                    <Pagination>
                        <EntriesPerPage>200</EntriesPerPage>
                        <PageNumber>{page}</PageNumber>
                    </Pagination>
                </ActiveList>
            </GetMyeBaySellingRequest>''',
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"eBay API error: {resp.status_code}")
            break

        root = ElementTree.fromstring(resp.text)
        active = root.find('.//e:ActiveList', _EBAY_NS)
        if active is None:
            break

        if page == 1:
            pages_el = active.find('.//e:PaginationResult/e:TotalNumberOfPages', _EBAY_NS)
            total_pages = int(pages_el.text) if pages_el is not None else 1

        for item in active.findall('.//e:Item', _EBAY_NS):
            item_id = _text(item, 'e:ItemID')
            title = _text(item, 'e:Title')
            price = _text(item, './/e:CurrentPrice')
            qty = _text(item, 'e:QuantityAvailable') or '1'
            listing_type = _text(item, 'e:ListingType')
            # Gallery image from GetMyeBaySelling
            gallery = _text(item, './/e:PictureDetails/e:GalleryURL') or _text(item, './/e:GalleryURL') or ''

            all_items.append({
                'item_id': item_id,
                'title': title or '',
                'price': float(price) if price else 0,
                'quantity': int(qty) if qty else 1,
                'listing_type': listing_type or '',
                'gallery_url': gallery,
            })

        page += 1

    return all_items


def get_item_images(token, item_id):
    """Fetch full image URLs for a single item via GetItem."""
    resp = requests.post(
        'https://api.ebay.com/ws/api.dll',
        headers={
            'X-EBAY-API-IAF-TOKEN': token,
            'X-EBAY-API-CALL-NAME': 'GetItem',
            'X-EBAY-API-SITEID': '0',
            'X-EBAY-API-COMPATIBILITY-LEVEL': '1209',
            'Content-Type': 'text/xml',
        },
        data=f'''<?xml version="1.0" encoding="utf-8"?>
        <GetItemRequest xmlns="urn:ebay:apis:eBLBaseComponents">
            <Version>1209</Version>
            <ItemID>{item_id}</ItemID>
            <IncludeItemSpecifics>true</IncludeItemSpecifics>
            <DetailLevel>ReturnAll</DetailLevel>
        </GetItemRequest>''',
        timeout=15,
    )
    if resp.status_code != 200:
        return [], ''

    root = ElementTree.fromstring(resp.text)
    item_el = root.find('.//e:Item', _EBAY_NS)
    if item_el is None:
        return [], ''

    # Get all picture URLs
    urls = []
    pic_details = item_el.find('e:PictureDetails', _EBAY_NS)
    if pic_details is not None:
        for url_el in pic_details.findall('e:PictureURL', _EBAY_NS):
            if url_el.text:
                urls.append(url_el.text)

    # Get description
    desc = _text(item_el, 'e:Description') or ''
    # Strip HTML tags for a plain-text description
    if '<' in desc:
        import re
        desc = re.sub(r'<[^>]+>', ' ', desc)
        desc = re.sub(r'\s+', ' ', desc).strip()

    return urls[:8], desc[:500]


def to_whatnot_row(item, image_urls, description):
    """Convert an eBay listing to a Whatnot CSV row."""
    # Pad image URLs to 8 slots
    images = (image_urls + [''] * 8)[:8]

    return {
        'Category': 'Sports Cards',
        'Sub Category': 'Baseball Singles',
        'Title': item['title'][:80],
        'Description': description or item['title'],
        'Quantity': item['quantity'],
        'Type': 'Buy it Now',
        'Price': int(round(item['price'])),
        'Shipping Profile': '1-4 oz',
        'Offerable': 'TRUE',
        'Hazmat': 'Not Hazmat',
        'Condition': 'New',
        'Cost Per Item': '',
        'SKU': item['item_id'],
        'Image URL 1': images[0],
        'Image URL 2': images[1],
        'Image URL 3': images[2],
        'Image URL 4': images[3],
        'Image URL 5': images[4],
        'Image URL 6': images[5],
        'Image URL 7': images[6],
        'Image URL 8': images[7],
    }


def main():
    parser = argparse.ArgumentParser(description='Export eBay BIN listings to Whatnot CSV')
    parser.add_argument('--output', '-o', default='whatnot_upload.csv', help='Output CSV file path')
    parser.add_argument('--no-images', action='store_true', help='Skip fetching individual item images (faster, gallery only)')
    args = parser.parse_args()

    print("Getting eBay token...")
    token = get_user_token()
    if not token:
        print("ERROR: Could not get eBay token. Check EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, EBAY_USER_REFRESH_TOKEN in backend/.env")
        sys.exit(1)

    print("Fetching active listings...")
    listings = fetch_all_active_listings(token)
    print(f"  Found {len(listings)} active listings")

    # Filter to BIN only (exclude auctions)
    bin_listings = [l for l in listings if l['listing_type'] in ('FixedPriceItem', 'StoresFixedPrice', '')]
    print(f"  {len(bin_listings)} are Buy It Now")

    if not bin_listings:
        print("No BIN listings found.")
        sys.exit(0)

    # Build CSV rows
    rows = []
    for i, item in enumerate(bin_listings, 1):
        if args.no_images:
            image_urls = [item['gallery_url']] if item['gallery_url'] else []
            desc = item['title']
        else:
            print(f"  [{i}/{len(bin_listings)}] Fetching images for: {item['title'][:60]}...")
            image_urls, desc = get_item_images(token, item['item_id'])
            if not image_urls and item['gallery_url']:
                image_urls = [item['gallery_url']]

        rows.append(to_whatnot_row(item, image_urls, desc))

    # Write CSV
    fieldnames = [
        'Category', 'Sub Category', 'Title', 'Description', 'Quantity',
        'Type', 'Price', 'Shipping Profile', 'Offerable', 'Hazmat',
        'Condition', 'Cost Per Item', 'SKU',
        'Image URL 1', 'Image URL 2', 'Image URL 3', 'Image URL 4',
        'Image URL 5', 'Image URL 6', 'Image URL 7', 'Image URL 8',
    ]

    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone! Wrote {len(rows)} listings to: {args.output}")
    print(f"\nNext steps:")
    print(f"  1. Go to https://whatnot.com/dashboard/inventory")
    print(f"  2. Click the Upload CSV button (cloud icon)")
    print(f"  3. Upload {args.output}")
    print(f"  4. Review drafts, then publish")


if __name__ == '__main__':
    main()
