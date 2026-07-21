"""
eBay Live Storefront - pulls active listings directly from eBay.

No database needed. Uses the seller's OAuth refresh token to get
live inventory from eBay's Trading API.
"""
import os
import base64
import requests
from xml.etree import ElementTree
from fastapi import APIRouter, Query
from typing import Optional

from backend.utils.player_extractor import player_extractor

router = APIRouter()

_EBAY_NS = {'e': 'urn:ebay:apis:eBLBaseComponents'}


def _guess_player_name(title: str) -> Optional[str]:
    """Match a listing title against the tracked-player list (targets.yaml).

    Only returns a name if it's one we actually track, so a hit here always
    has real Card/Sale data behind it - no point showing a stats section
    for a player we don't follow.
    """
    if not title:
        return None
    match = player_extractor.extract_player(title)
    return match[0] if match else None


def _get_user_token():
    """Get a fresh user access token from the refresh token."""
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
    return None


def _fetch_ebay_listings(token, page=1, per_page=25):
    """Fetch active listings from eBay Trading API."""
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
                    <EntriesPerPage>{per_page}</EntriesPerPage>
                    <PageNumber>{page}</PageNumber>
                </Pagination>
            </ActiveList>
        </GetMyeBaySellingRequest>''',
        timeout=15,
    )
    if resp.status_code != 200:
        return [], 0

    root = ElementTree.fromstring(resp.text)
    active = root.find('.//e:ActiveList', _EBAY_NS)
    if active is None:
        return [], 0

    total_el = active.find('.//e:TotalNumberOfEntries', _EBAY_NS)
    total = int(total_el.text) if total_el is not None else 0

    cards = []
    for item in active.findall('.//e:Item', _EBAY_NS):
        item_id = _text(item, 'e:ItemID')
        title = _text(item, 'e:Title')
        price = _text(item, './/e:CurrentPrice')
        currency = item.find('.//e:CurrentPrice', _EBAY_NS)
        currency_id = currency.get('currencyID', 'USD') if currency is not None else 'USD'
        qty = _text(item, 'e:QuantityAvailable')
        image_url = (_text(item, './/e:PictureDetails/e:GalleryURL') or _text(item, './/e:GalleryURL') or '').replace('s-l140', 's-l400')
        url = f'https://www.ebay.com/itm/{item_id}' if item_id else None

        cards.append({
            'id': item_id,
            'title': title,
            'price': float(price) if price else None,
            'currency': currency_id,
            'quantity': int(qty) if qty else 1,
            'image_url': image_url or None,
            'ebay_url': url,
        })

    return cards, total


def _text(el, path):
    """Extract text from XML element."""
    found = el.find(path, _EBAY_NS)
    return found.text if found is not None else None


@router.get("/shop/ebay")
def get_ebay_listings(
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=100),
):
    """Public endpoint: browse seller's eBay listings. No auth required."""
    token = _get_user_token()
    if not token:
        return {'total': 0, 'cards': [], 'error': 'eBay connection not configured'}

    cards, total = _fetch_ebay_listings(token, page=page, per_page=limit)

    if search:
        term = search.lower()
        cards = [c for c in cards if term in (c.get('title') or '').lower()]
        total = len(cards)

    return {
        'total': total,
        'page': page,
        'limit': limit,
        'cards': cards,
    }


@router.get("/shop/ebay/stats")
def get_ebay_stats():
    """Public endpoint: seller stats."""
    token = _get_user_token()
    if not token:
        return {'cards_listed': 0, 'total_ask_value': 0}

    cards, total = _fetch_ebay_listings(token, page=1, per_page=100)
    total_value = sum(c.get('price', 0) or 0 for c in cards)

    return {
        'cards_listed': total,
        'total_ask_value': round(total_value, 2),
    }


@router.get("/shop/ebay/{item_id}")
def get_ebay_item_detail(item_id: str):
    """Public endpoint: full detail for a single eBay listing (for the Shop detail view)."""
    token = _get_user_token()
    if not token:
        return {'error': 'eBay connection not configured'}

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
            <IncludeWatchCount>true</IncludeWatchCount>
            <DetailLevel>ReturnAll</DetailLevel>
        </GetItemRequest>''',
        timeout=15,
    )
    if resp.status_code != 200:
        return {'error': 'Could not load listing'}

    root = ElementTree.fromstring(resp.text)
    item = root.find('.//e:Item', _EBAY_NS)
    if item is None:
        return {'error': 'Listing not found'}

    specifics = {}
    for ns_el in item.findall('.//e:ItemSpecifics/e:NameValueList', _EBAY_NS):
        name = _text(ns_el, 'e:Name')
        value = _text(ns_el, 'e:Value')
        if name:
            specifics[name] = value

    images = [
        el.text for el in item.findall('.//e:PictureDetails/e:PictureURL', _EBAY_NS)
        if el.text
    ]

    title = _text(item, 'e:Title')
    return {
        'id': item_id,
        'title': title,
        'description': _text(item, 'e:Description'),
        'condition': _text(item, 'e:ConditionDisplayName') or specifics.get('Card Condition'),
        'watch_count': _text(item, 'e:WatchCount'),
        'quantity_available': _text(item, 'e:QuantityAvailable'),
        'images': images,
        'specifics': specifics,
        'ebay_url': f'https://www.ebay.com/itm/{item_id}',
        'guessed_player_name': _guess_player_name(title),
    }
