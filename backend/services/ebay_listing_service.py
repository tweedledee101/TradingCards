"""
eBay Listing Service - create and manage eBay listings from inventory.

Requires eBay OAuth user token (not just app token). The user must authorize
the app via OAuth consent flow to get a user access token with sell scope.

eBay APIs used:
- Inventory API: create inventory items + offers
- Trading API (legacy): for features not in new APIs

Prerequisites:
- User OAuth token with scope: sell.inventory, sell.fulfillment
- eBay developer account with Trading API access
- Fulfillment policy, payment policy, return policy IDs

This is the bridge between your inventory DB and live eBay listings.
Flow: Inventory row -> build listing payload -> eBay API -> update inventory with ebay_item_id
"""
from __future__ import annotations

import requests
from typing import Dict, Optional
from datetime import datetime


EBAY_SELL_API = 'https://api.ebay.com/sell'
EBAY_INVENTORY_API = f'{EBAY_SELL_API}/inventory/v1'


class EbayListingService:
    """Create and manage eBay listings from inventory data."""

    def __init__(self, user_access_token: str):
        """Initialize with a user OAuth token (not app token).

        The user must have authorized the app with sell.inventory scope.
        """
        self.token = user_access_token
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Content-Language': 'en-US',
        }

    def create_listing_from_inventory(
        self,
        card: Dict,
        price: float,
        condition: str = 'LIKE_NEW',
        quantity: int = 1,
        description: str = None,
        image_urls: list = None,
        fulfillment_policy_id: str = None,
        payment_policy_id: str = None,
        return_policy_id: str = None,
    ) -> Dict:
        """Create a full eBay listing from an inventory card dict.

        Args:
            card: Dict with player_name, card_year, card_set, card_number, parallel
            price: Listing price in USD
            condition: LIKE_NEW, VERY_GOOD, GOOD, ACCEPTABLE
            quantity: Number available (usually 1 for singles)
            description: HTML description (auto-generated if None)
            image_urls: List of image URLs for the listing
            fulfillment_policy_id: eBay shipping policy ID
            payment_policy_id: eBay payment policy ID
            return_policy_id: eBay return policy ID

        Returns:
            Dict with listing_id, ebay_url, status
        """
        # Step 1: Create inventory item
        sku = self._generate_sku(card)
        inv_result = self._create_inventory_item(sku, card, condition, quantity, description, image_urls)
        if not inv_result.get('success'):
            return inv_result

        # Step 2: Create offer (connects inventory item to a listing)
        offer_result = self._create_offer(
            sku, price, card,
            fulfillment_policy_id=fulfillment_policy_id,
            payment_policy_id=payment_policy_id,
            return_policy_id=return_policy_id,
        )
        if not offer_result.get('success'):
            return offer_result

        # Step 3: Publish the offer (makes it live)
        publish_result = self._publish_offer(offer_result['offer_id'])
        return publish_result

    def _generate_sku(self, card: Dict) -> str:
        """Generate a unique SKU from card identity."""
        parts = [
            str(card.get('card_year', '')),
            (card.get('card_set') or '')[:20].replace(' ', '-'),
            (card.get('card_number') or ''),
            (card.get('parallel') or 'Base')[:15].replace(' ', '-'),
        ]
        sku = '-'.join(p for p in parts if p)
        # Add timestamp for uniqueness
        sku += f'-{int(datetime.now().timestamp())}'
        return sku[:50]  # eBay SKU max 50 chars

    def _create_inventory_item(
        self, sku: str, card: Dict, condition: str,
        quantity: int, description: str, image_urls: list,
    ) -> Dict:
        """Create an inventory item on eBay."""
        title = self._build_title(card)
        if not description:
            description = self._build_description(card)

        payload = {
            'availability': {
                'shipToLocationAvailability': {
                    'quantity': quantity,
                }
            },
            'condition': condition,
            'product': {
                'title': title,
                'description': description,
                'aspects': self._build_aspects(card),
                'imageUrls': image_urls[:12] if image_urls else [],
            },
        }

        resp = requests.put(
            f'{EBAY_INVENTORY_API}/inventory_item/{sku}',
            headers=self.headers,
            json=payload,
            timeout=15,
        )

        if resp.status_code in (200, 201, 204):
            return {'success': True, 'sku': sku}
        else:
            return {'success': False, 'error': f'Inventory item failed: HTTP {resp.status_code}', 'detail': resp.text[:300]}

    def _create_offer(
        self, sku: str, price: float, card: Dict,
        fulfillment_policy_id: str = None,
        payment_policy_id: str = None,
        return_policy_id: str = None,
    ) -> Dict:
        """Create an offer (price + policies) for an inventory item."""
        payload = {
            'sku': sku,
            'marketplaceId': 'EBAY_US',
            'format': 'FIXED_PRICE',
            'listingDescription': self._build_description(card),
            'pricingSummary': {
                'price': {
                    'value': str(round(price, 2)),
                    'currency': 'USD',
                }
            },
            'categoryId': '261328',  # Trading Card Singles
            'listingPolicies': {},
        }

        if fulfillment_policy_id:
            payload['listingPolicies']['fulfillmentPolicyId'] = fulfillment_policy_id
        if payment_policy_id:
            payload['listingPolicies']['paymentPolicyId'] = payment_policy_id
        if return_policy_id:
            payload['listingPolicies']['returnPolicyId'] = return_policy_id

        resp = requests.post(
            f'{EBAY_SELL_API}/inventory/v1/offer',
            headers=self.headers,
            json=payload,
            timeout=15,
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            return {'success': True, 'offer_id': data.get('offerId')}
        else:
            return {'success': False, 'error': f'Offer creation failed: HTTP {resp.status_code}', 'detail': resp.text[:300]}

    def _publish_offer(self, offer_id: str) -> Dict:
        """Publish an offer to make it a live listing."""
        resp = requests.post(
            f'{EBAY_SELL_API}/inventory/v1/offer/{offer_id}/publish',
            headers=self.headers,
            timeout=15,
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            listing_id = data.get('listingId', '')
            return {
                'success': True,
                'listing_id': listing_id,
                'ebay_url': f'https://www.ebay.com/itm/{listing_id}',
                'offer_id': offer_id,
            }
        else:
            return {'success': False, 'error': f'Publish failed: HTTP {resp.status_code}', 'detail': resp.text[:300]}

    def _build_title(self, card: Dict) -> str:
        """Build an eBay listing title from card data (max 80 chars)."""
        parts = []
        if card.get('card_year'):
            parts.append(str(card['card_year']))
        if card.get('card_set'):
            parts.append(card['card_set'])
        if card.get('player_name'):
            parts.append(card['player_name'])
        if card.get('card_number'):
            parts.append(f"#{card['card_number']}")
        if card.get('parallel') and card['parallel'] != 'Base':
            parts.append(card['parallel'])
        title = ' '.join(parts)
        return title[:80]

    def _build_description(self, card: Dict) -> str:
        """Build HTML description for the listing."""
        lines = [f"<b>{card.get('card_year', '')} {card.get('card_set', '')}</b>"]
        lines.append(f"<br>Player: {card.get('player_name', '')}")
        if card.get('card_number'):
            lines.append(f"<br>Card #: {card['card_number']}")
        if card.get('parallel') and card['parallel'] != 'Base':
            lines.append(f"<br>Parallel: {card['parallel']}")
        lines.append("<br><br>Ships in penny sleeve + top loader in bubble mailer.")
        lines.append("<br>Combined shipping available.")
        return '\n'.join(lines)

    def _build_aspects(self, card: Dict) -> Dict:
        """Build eBay item aspects (structured attributes)."""
        aspects = {
            'Sport': ['Baseball'],
            'Card Manufacturer': [card.get('card_set', '').split()[0] if card.get('card_set') else 'Topps'],
        }
        if card.get('card_year'):
            aspects['Year'] = [str(card['card_year'])]
        if card.get('player_name'):
            aspects['Player/Athlete'] = [card['player_name']]
        if card.get('card_number'):
            aspects['Card Number'] = [str(card['card_number'])]
        if card.get('parallel') and card['parallel'] != 'Base':
            aspects['Parallel/Variety'] = [card['parallel']]
        if card.get('card_set'):
            aspects['Set'] = [card['card_set']]
        return aspects
