"""
Weekly Scorecard - pulls eBay activity and computes week-over-week performance.

Metrics tracked:
- Total inventory value (ask price of all active listings)
- Inventory tier breakdown (under $5, $5-25, $25-100, $100+)
- Sales count + revenue
- Purchases count + spend
- Bid win rate
- Sell-through rate
- Week-over-week changes
"""
import os
import base64
import requests
from xml.etree import ElementTree
from datetime import date, timedelta
from decimal import Decimal
from statistics import median
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from backend.models import WeeklySnapshot

NS = {'e': 'urn:ebay:apis:eBLBaseComponents'}


def _get_user_token() -> Optional[str]:
    cid = os.getenv('EBAY_CLIENT_ID', '').strip()
    sec = os.getenv('EBAY_CLIENT_SECRET', '').strip()
    refresh = os.getenv('EBAY_USER_REFRESH_TOKEN', '').strip()
    if not refresh:
        return None
    b64 = base64.b64encode(f'{cid}:{sec}'.encode()).decode()
    resp = requests.post(
        'https://api.ebay.com/identity/v1/oauth2/token',
        headers={'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': f'Basic {b64}'},
        data={
            'grant_type': 'refresh_token',
            'refresh_token': refresh,
            'scope': 'https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.account https://api.ebay.com/oauth/api_scope/sell.fulfillment',
        },
        timeout=15,
    )
    if resp.status_code == 200:
        return resp.json().get('access_token')
    return None


def _call_trading(token: str, call_name: str, body: str):
    return requests.post(
        'https://api.ebay.com/ws/api.dll',
        headers={
            'X-EBAY-API-IAF-TOKEN': token,
            'X-EBAY-API-CALL-NAME': call_name,
            'X-EBAY-API-SITEID': '0',
            'X-EBAY-API-COMPATIBILITY-LEVEL': '1209',
            'Content-Type': 'text/xml',
        },
        data=body,
        timeout=20,
    )


def _text(el, path):
    found = el.find(path, NS)
    return found.text if found is not None else None


def _pull_active_listings(token: str) -> List[Dict]:
    items = []
    for page in range(1, 5):  # up to 400 listings
        resp = _call_trading(token, 'GetMyeBaySelling', f'''<?xml version="1.0" encoding="utf-8"?>
        <GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
            <Version>1209</Version>
            <ActiveList>
                <Pagination><EntriesPerPage>100</EntriesPerPage><PageNumber>{page}</PageNumber></Pagination>
            </ActiveList>
        </GetMyeBaySellingRequest>''')
        root = ElementTree.fromstring(resp.text)
        active = root.find('.//e:ActiveList', NS)
        if not active:
            break
        for item in active.findall('.//e:Item', NS):
            price = _text(item, './/e:CurrentPrice')
            items.append({
                'title': _text(item, 'e:Title'),
                'price': float(price) if price else 0,
            })
        total_pages = _text(active, './/e:PaginationResult/e:TotalNumberOfPages')
        if total_pages and page >= int(total_pages):
            break
    return items


def _pull_sold(token: str) -> List[Dict]:
    resp = _call_trading(token, 'GetMyeBaySelling', '''<?xml version="1.0" encoding="utf-8"?>
    <GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
        <Version>1209</Version>
        <SoldList>
            <Sort>EndTime</Sort>
            <Pagination><EntriesPerPage>100</EntriesPerPage><PageNumber>1</PageNumber></Pagination>
        </SoldList>
    </GetMyeBaySellingRequest>''')
    root = ElementTree.fromstring(resp.text)
    sold = root.find('.//e:SoldList', NS)
    if not sold:
        return []
    items = []
    for item in sold.findall('.//e:OrderTransaction', NS):
        tx = item.find('e:Transaction', NS) or item
        it = item.find('.//e:Item', NS) or item
        price = _text(tx, './/e:TransactionPrice') or _text(it, './/e:CurrentPrice')
        items.append({
            'title': _text(it, 'e:Title'),
            'price': float(price) if price else 0,
            'date': (_text(tx, './/e:CreatedDate') or '')[:10],
        })
    return items


def _pull_unsold(token: str) -> List[Dict]:
    resp = _call_trading(token, 'GetMyeBaySelling', '''<?xml version="1.0" encoding="utf-8"?>
    <GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
        <Version>1209</Version>
        <UnsoldList>
            <Pagination><EntriesPerPage>100</EntriesPerPage><PageNumber>1</PageNumber></Pagination>
        </UnsoldList>
    </GetMyeBaySellingRequest>''')
    root = ElementTree.fromstring(resp.text)
    unsold = root.find('.//e:UnsoldList', NS)
    if not unsold:
        return []
    return [{'title': _text(i, 'e:Title')} for i in unsold.findall('.//e:Item', NS)]


def _pull_won(token: str) -> List[Dict]:
    resp = _call_trading(token, 'GetMyeBayBuying', '''<?xml version="1.0" encoding="utf-8"?>
    <GetMyeBayBuyingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
        <Version>1209</Version>
        <WonList>
            <Sort>EndTime</Sort>
            <Pagination><EntriesPerPage>100</EntriesPerPage><PageNumber>1</PageNumber></Pagination>
        </WonList>
    </GetMyeBayBuyingRequest>''')
    root = ElementTree.fromstring(resp.text)
    won = root.find('.//e:WonList', NS)
    if not won:
        return []
    items = []
    for item in won.findall('.//e:OrderTransaction', NS):
        tx = item.find('e:Transaction', NS) or item
        it = item.find('.//e:Item', NS) or item
        price = _text(tx, './/e:TransactionPrice') or _text(it, './/e:CurrentPrice')
        items.append({
            'title': _text(it, 'e:Title'),
            'price': float(price) if price else 0,
            'date': (_text(tx, './/e:CreatedDate') or '')[:10],
        })
    return items


def _pull_lost(token: str) -> List[Dict]:
    resp = _call_trading(token, 'GetMyeBayBuying', '''<?xml version="1.0" encoding="utf-8"?>
    <GetMyeBayBuyingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
        <Version>1209</Version>
        <LostList>
            <Sort>EndTime</Sort>
            <Pagination><EntriesPerPage>100</EntriesPerPage><PageNumber>1</PageNumber></Pagination>
        </LostList>
    </GetMyeBayBuyingRequest>''')
    root = ElementTree.fromstring(resp.text)
    lost = root.find('.//e:LostList', NS)
    if not lost:
        return []
    return [{'title': _text(i, 'e:Title'), 'price': float(_text(i, './/e:CurrentPrice') or 0)}
            for i in lost.findall('.//e:Item', NS)]


def _pull_watchlist(token: str) -> int:
    resp = _call_trading(token, 'GetMyeBayBuying', '''<?xml version="1.0" encoding="utf-8"?>
    <GetMyeBayBuyingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
        <Version>1209</Version>
        <WatchList>
            <Pagination><EntriesPerPage>1</EntriesPerPage><PageNumber>1</PageNumber></Pagination>
        </WatchList>
    </GetMyeBayBuyingRequest>''')
    root = ElementTree.fromstring(resp.text)
    watch = root.find('.//e:WatchList', NS)
    if not watch:
        return 0
    total = _text(watch, './/e:TotalNumberOfEntries')
    return int(total) if total else 0


def generate_weekly_scorecard(db: Session, account_id: int = 1) -> Dict:
    """
    Pull all eBay data, compute this week's metrics, store snapshot,
    and return scorecard with week-over-week comparison.
    """
    token = _get_user_token()
    if not token:
        return {'error': 'eBay connection not configured'}

    # Determine current week (Monday-Sunday)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    # Pull all data
    active = _pull_active_listings(token)
    sold = _pull_sold(token)
    unsold = _pull_unsold(token)
    won = _pull_won(token)
    lost = _pull_lost(token)
    watchlist_count = _pull_watchlist(token)

    # Compute inventory metrics
    prices = [i['price'] for i in active if i['price'] > 0]
    total_ask = sum(prices)
    med_price = median(prices) if prices else 0

    under_5 = len([p for p in prices if p < 5])
    _5_to_25 = len([p for p in prices if 5 <= p < 25])
    _25_to_100 = len([p for p in prices if 25 <= p < 100])
    over_100 = len([p for p in prices if p >= 100])

    # Sales metrics
    sold_count = len(sold)
    total_revenue = sum(s['price'] for s in sold)
    avg_sale = total_revenue / sold_count if sold_count else 0

    # Sell-through
    total_ended = sold_count + len(unsold)
    sell_through = (sold_count / total_ended * 100) if total_ended > 0 else 0

    # Purchase metrics
    bought_count = len(won)
    total_spent = sum(w['price'] for w in won)
    avg_buy = total_spent / bought_count if bought_count else 0

    # Bid metrics
    lost_count = len(lost)
    total_bids = bought_count + lost_count
    win_rate = (bought_count / total_bids * 100) if total_bids > 0 else 0

    # Net profit estimate (revenue after fees - doesn't account for COGS perfectly)
    net_profit = total_revenue * 0.87 - total_spent

    # Store/update snapshot
    existing = db.query(WeeklySnapshot).filter(
        WeeklySnapshot.account_id == account_id,
        WeeklySnapshot.week_start == week_start,
    ).first()

    snap_data = dict(
        active_listings=len(active),
        total_inventory_ask=Decimal(str(round(total_ask, 2))),
        listings_under_5=under_5,
        listings_5_to_25=_5_to_25,
        listings_25_to_100=_25_to_100,
        listings_over_100=over_100,
        median_listing_price=Decimal(str(round(med_price, 2))),
        items_sold=sold_count,
        total_revenue=Decimal(str(round(total_revenue, 2))),
        avg_sale_price=Decimal(str(round(avg_sale, 2))),
        sell_through_pct=Decimal(str(round(sell_through, 1))),
        items_bought=bought_count,
        total_spent=Decimal(str(round(total_spent, 2))),
        avg_buy_price=Decimal(str(round(avg_buy, 2))),
        bids_won=bought_count,
        bids_lost=lost_count,
        win_rate_pct=Decimal(str(round(win_rate, 1))),
        watchlist_count=watchlist_count,
        net_profit_est=Decimal(str(round(net_profit, 2))),
        raw_data={
            'sold_titles': [s['title'] for s in sold[:20]],
            'won_titles': [w['title'] for w in won[:20]],
            'top_listings': [{'title': a['title'], 'price': a['price']}
                            for a in sorted(active, key=lambda x: x['price'], reverse=True)[:10]],
        },
    )

    if existing:
        for k, v in snap_data.items():
            setattr(existing, k, v)
        db.commit()
        db.refresh(existing)
        snap = existing
    else:
        snap = WeeklySnapshot(
            account_id=account_id,
            week_start=week_start,
            week_end=week_end,
            **snap_data,
        )
        db.add(snap)
        db.commit()
        db.refresh(snap)

    # Get previous week for comparison
    prev_week_start = week_start - timedelta(days=7)
    prev = db.query(WeeklySnapshot).filter(
        WeeklySnapshot.account_id == account_id,
        WeeklySnapshot.week_start == prev_week_start,
    ).first()

    # Build scorecard response
    def delta(current, previous, field):
        c = float(getattr(snap, field) or 0)
        p = float(getattr(previous, field) or 0) if previous else 0
        return {'current': c, 'previous': p, 'change': round(c - p, 2)}

    scorecard = {
        'week_start': week_start.isoformat(),
        'week_end': week_end.isoformat(),
        'has_previous': prev is not None,
        'inventory': {
            'active_listings': delta(snap, prev, 'active_listings'),
            'total_ask_value': delta(snap, prev, 'total_inventory_ask'),
            'median_price': delta(snap, prev, 'median_listing_price'),
            'tiers': {
                'under_5': under_5,
                'tier_5_25': _5_to_25,
                'tier_25_100': _25_to_100,
                'over_100': over_100,
            },
        },
        'sales': {
            'items_sold': delta(snap, prev, 'items_sold'),
            'total_revenue': delta(snap, prev, 'total_revenue'),
            'avg_sale_price': delta(snap, prev, 'avg_sale_price'),
            'sell_through_pct': delta(snap, prev, 'sell_through_pct'),
        },
        'buying': {
            'items_bought': delta(snap, prev, 'items_bought'),
            'total_spent': delta(snap, prev, 'total_spent'),
            'avg_buy_price': delta(snap, prev, 'avg_buy_price'),
            'win_rate_pct': delta(snap, prev, 'win_rate_pct'),
        },
        'watchlist_count': watchlist_count,
        'net_profit_est': delta(snap, prev, 'net_profit_est'),
        'top_listings': snap_data['raw_data']['top_listings'],
    }

    return scorecard


def get_scorecard_history(db: Session, weeks: int = 8, account_id: int = 1) -> List[Dict]:
    """Get historical weekly snapshots for trending charts."""
    snapshots = db.query(WeeklySnapshot).filter(
        WeeklySnapshot.account_id == account_id,
    ).order_by(WeeklySnapshot.week_start.desc()).limit(weeks).all()

    return [{
        'week_start': s.week_start.isoformat(),
        'active_listings': s.active_listings,
        'total_inventory_ask': float(s.total_inventory_ask or 0),
        'items_sold': s.items_sold,
        'total_revenue': float(s.total_revenue or 0),
        'items_bought': s.items_bought,
        'total_spent': float(s.total_spent or 0),
        'net_profit_est': float(s.net_profit_est or 0),
        'median_listing_price': float(s.median_listing_price or 0),
        'sell_through_pct': float(s.sell_through_pct or 0),
        'listings_over_100': s.listings_over_100,
    } for s in reversed(snapshots)]
