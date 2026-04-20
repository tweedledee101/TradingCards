"""
Unified marketplace adapter for cross-platform trading card arbitrage.

Abstracts platform-specific scrapers behind a common interface so the
opportunity pipeline can search multiple marketplaces with one call.

Supported platforms:
- eBay (Browse API) -- primary, highest volume
- COMC (Playwright) -- fixed price, structured data, 5% buyer fee
- Mercari (API/web) -- casual sellers, mispriced cards, 10% seller fee

Future:
- Whatnot (live auctions)
- Fanatics Live
- MySlabs (graded cards)
- Facebook Groups (manual intake)

Fee schedule (used for profit calculations):
    Platform    Buyer Fee    Seller Fee    Notes
    eBay        0%           13%           Best sell-through, highest reach
    COMC        5%           20%           Set-and-forget, slow sell-through
    Mercari     0%           10%           Free shipping common, casual sellers
    Whatnot     0%           9.5%+2.9%     Live auction format
    Facebook    0%           0%            No fees, manual trust
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class MarketplaceListing:
    """Normalized listing from any marketplace."""
    title: str
    price: float
    url: str
    source: str  # 'ebay', 'comc', 'mercari', 'whatnot', etc.
    image_url: str = ''
    item_id: str = ''
    player_name: Optional[str] = None
    card_year: Optional[int] = None
    card_set: Optional[str] = None
    card_number: Optional[str] = None
    parallel: Optional[str] = None
    condition: Optional[str] = None
    shipping: float = 0.0
    listing_type: str = 'fixed'  # 'fixed', 'auction', 'live'
    end_time: Optional[str] = None
    seller: Optional[str] = None
    extra: Dict = field(default_factory=dict)


# Platform fee rates for profit calculations
PLATFORM_FEES = {
    'ebay': {'buyer': 0.0, 'seller': 0.13},
    'comc': {'buyer': 0.05, 'seller': 0.20},
    'mercari': {'buyer': 0.0, 'seller': 0.10},
    'whatnot': {'buyer': 0.0, 'seller': 0.124},  # 9.5% + 2.9%
    'facebook': {'buyer': 0.0, 'seller': 0.0},
    'myslabs': {'buyer': 0.0, 'seller': 0.08},
    'goldin': {'buyer': 0.20, 'seller': 0.0},  # 20% buyer's premium
    'pwcc': {'buyer': 0.20, 'seller': 0.0},
    'heritage': {'buyer': 0.20, 'seller': 0.0},
    'tcgplayer': {'buyer': 0.0, 'seller': 0.1025},
    'alt': {'buyer': 0.0, 'seller': 0.03},
}


def calculate_arbitrage(
    buy_price: float,
    buy_platform: str,
    sell_price: float,
    sell_platform: str = 'ebay',
    shipping_cost: float = 5.0,
) -> Dict:
    """Calculate cross-platform arbitrage profit.

    Args:
        buy_price: Listing price on buy platform
        buy_platform: Where you're buying ('mercari', 'comc', etc.)
        sell_price: Expected sell price (SCP, comps, etc.)
        sell_platform: Where you'll sell (default 'ebay')
        shipping_cost: Estimated shipping to buyer

    Returns dict with total_cost, net_revenue, profit, roi.
    """
    buy_fees = PLATFORM_FEES.get(buy_platform, {'buyer': 0, 'seller': 0})
    sell_fees = PLATFORM_FEES.get(sell_platform, {'buyer': 0, 'seller': 0.13})

    total_cost = buy_price * (1 + buy_fees['buyer'])
    gross_revenue = sell_price
    seller_fee = gross_revenue * sell_fees['seller']
    net_revenue = gross_revenue - seller_fee - shipping_cost
    profit = net_revenue - total_cost

    return {
        'buy_price': round(buy_price, 2),
        'buy_platform': buy_platform,
        'buy_fee': round(buy_price * buy_fees['buyer'], 2),
        'total_cost': round(total_cost, 2),
        'sell_price': round(sell_price, 2),
        'sell_platform': sell_platform,
        'seller_fee': round(seller_fee, 2),
        'shipping_cost': round(shipping_cost, 2),
        'net_revenue': round(net_revenue, 2),
        'profit': round(profit, 2),
        'roi': round((profit / total_cost) * 100, 1) if total_cost > 0 else 0,
    }


def search_all_marketplaces(
    query: str,
    platforms: List[str] = None,
    max_per_platform: int = 20,
) -> List[MarketplaceListing]:
    """Search multiple marketplaces for the same card query.

    Args:
        query: Card search string
        platforms: List of platform names to search (default: all available)
        max_per_platform: Max results per platform

    Returns combined list of MarketplaceListing from all platforms.
    """
    if platforms is None:
        platforms = ['mercari', 'comc', 'goldin']  # eBay handled separately by pipeline

    results: List[MarketplaceListing] = []

    for platform in platforms:
        try:
            if platform == 'mercari':
                from backend.scrapers.mercari_scraper import search_mercari
                items = search_mercari(query, max_results=max_per_platform)
                for item in items:
                    results.append(MarketplaceListing(
                        title=item.get('title', ''),
                        price=item.get('price', 0),
                        url=item.get('url', ''),
                        source='mercari',
                        image_url=item.get('image_url', ''),
                        item_id=item.get('item_id', ''),
                        shipping=0 if item.get('shipping_included') else 5.0,
                        seller=item.get('seller', ''),
                    ))

            elif platform == 'comc':
                from backend.scrapers.comc_scraper import search_comc
                items = search_comc(query, max_results=max_per_platform)
                for item in items:
                    results.append(MarketplaceListing(
                        title=item.get('title', ''),
                        price=item.get('price', 0),
                        url=item.get('url', ''),
                        source='comc',
                        image_url=item.get('image_url', ''),
                        player_name=item.get('player_name'),
                        card_year=item.get('card_year'),
                        card_set=item.get('card_set'),
                        card_number=item.get('card_number'),
                    ))

            elif platform == 'goldin':
                from backend.scrapers.goldin_scraper import search_goldin
                items = search_goldin(query, max_results=max_per_platform, status='active')
                for item in items:
                    results.append(MarketplaceListing(
                        title=item.get('title', ''),
                        price=item.get('total_with_premium', item.get('price', 0)),
                        url=item.get('url', ''),
                        source='goldin',
                        image_url=item.get('image_url', ''),
                        item_id=item.get('item_id', ''),
                        card_year=item.get('card_year'),
                        card_number=item.get('card_number'),
                        listing_type='auction',
                        end_time=item.get('end_time'),
                    ))

        except ImportError as e:
            print(f'Skipping {platform}: {e}')
        except Exception as e:
            print(f'Error searching {platform}: {e}')

    return results


def find_cross_platform_arbitrage(
    query: str,
    scp_db,
    platforms: List[str] = None,
    sell_platform: str = 'ebay',
    min_profit: float = 10.0,
    max_buy_price: float = 200.0,
) -> List[Dict]:
    """Search multiple platforms and find arbitrage vs SCP prices.

    The core use case: find cards listed below market on Mercari/COMC,
    buy them, sell on eBay at SCP price.
    """
    listings = search_all_marketplaces(query, platforms=platforms)

    opportunities = []
    for listing in listings:
        if listing.price <= 0 or listing.price > max_buy_price:
            continue

        # Try to get SCP price for this card
        # (simplified -- full pipeline would use the multi-pass matching)
        from sqlalchemy import text
        scp_row = None
        if listing.player_name and listing.card_number and listing.card_year:
            scp_row = scp_db.execute(text("""
                SELECT (v->>'ungraded')::numeric as price, v->>'volume' as volume
                FROM scp_cache sc, jsonb_array_elements(sc.variants) v
                WHERE sc.player_name ILIKE :p AND sc.card_year = :y AND sc.card_number ILIKE :n
                AND (v->>'ungraded')::numeric > 0
                ORDER BY (v->>'ungraded')::numeric DESC LIMIT 1
            """), {'p': listing.player_name, 'y': listing.card_year,
                   'n': str(listing.card_number)}).first()

        if not scp_row:
            continue

        arb = calculate_arbitrage(
            buy_price=listing.price,
            buy_platform=listing.source,
            sell_price=float(scp_row.price),
            sell_platform=sell_platform,
        )

        if arb['profit'] >= min_profit:
            opportunities.append({
                'listing': {
                    'title': listing.title,
                    'price': listing.price,
                    'url': listing.url,
                    'source': listing.source,
                    'image_url': listing.image_url,
                },
                'scp_price': float(scp_row.price),
                'scp_volume': scp_row.volume,
                **arb,
            })

    return sorted(opportunities, key=lambda x: x['profit'], reverse=True)
