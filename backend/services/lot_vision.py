"""
Lot Vision Analysis - Identify individual cards in lot/multi-card listing photos.

Trading card lots are currently skipped by the pipeline (is_lot() filter). But lots
often contain high-value cards buried in filler. This module uses multimodal vision
(Amazon Nova or similar) to:

1. Identify individual cards visible in lot photos
2. Look up SCP prices for each identified card
3. Calculate whether the visible value justifies the lot price
4. Conservative: only count cards you can SEE, treat hidden cards as $0

Usage:
    from backend.services.lot_vision import analyze_lot_listing
    result = analyze_lot_listing(image_urls, lot_price)

Architecture:
    - Does NOT gate the pipeline. Runs post-pipeline on flagged lots.
    - Uses the same vision_card_extract + scp_db_match as vision_retry.
    - Stores results in opportunities with listing_type='lot' and
      verification_detail containing per-card breakdown.
"""
from __future__ import annotations

import os
import re
from typing import List, Dict, Optional, Tuple


# Minimum visible value to consider a lot worth buying
# (lot_price must be < visible_value * (1 - FEE_RATE) - MIN_PROFIT)
MIN_LOT_PROFIT = 15.0
FEE_RATE = 0.13


def identify_cards_in_image(image_url: str, model: str = None) -> List[Dict]:
    """Use multimodal vision to identify individual cards visible in a lot photo.

    Returns a list of card identities found in the image:
    [{'player_name': ..., 'card_year': ..., 'card_set': ..., 'card_number': ...,
      'parallel': ..., 'confidence': 'high'|'medium'|'low', 'position': 'top-left'|...}]
    """
    try:
        from backend.services.vision_card_extract import extract_card_from_image
    except ImportError:
        return []

    # For lots, we need a different prompt than single-card extraction
    lot_prompt = (
        "This image shows multiple trading cards (a lot/bundle). "
        "For EACH individual card you can clearly identify, provide: "
        "player name, year, card set/product, card number, and parallel/variant. "
        "Only include cards where you can read the text clearly. "
        "If a card is partially obscured or you cannot read it, skip it. "
        "Return as a JSON array of objects."
    )

    result = extract_card_from_image(image_url, custom_prompt=lot_prompt)
    if not result:
        return []

    # Parse the response into individual card identities
    cards = []
    if isinstance(result, list):
        for item in result:
            if isinstance(item, dict) and item.get('player_name'):
                cards.append({
                    'player_name': item.get('player_name'),
                    'card_year': item.get('card_year') or item.get('year'),
                    'card_set': item.get('card_set') or item.get('set'),
                    'card_number': item.get('card_number') or item.get('number'),
                    'parallel': item.get('parallel') or item.get('variant') or 'Base',
                    'confidence': item.get('confidence', 'medium'),
                })
    elif isinstance(result, dict) and result.get('player_name'):
        cards.append({
            'player_name': result.get('player_name'),
            'card_year': result.get('card_year'),
            'card_set': result.get('card_set'),
            'card_number': result.get('card_number'),
            'parallel': result.get('parallel', 'Base'),
            'confidence': result.get('confidence', 'medium'),
        })

    return cards


def price_identified_cards(cards: List[Dict], db) -> List[Dict]:
    """Look up SCP prices for each identified card. Returns cards with pricing added."""
    from backend.services.scp_db_match import find_scp_match_in_db

    priced = []
    for card in cards:
        player = card.get('player_name')
        year = card.get('card_year')
        number = card.get('card_number')
        parallel = card.get('parallel', 'Base')
        card_set = card.get('card_set', '')

        if not player or not number:
            card['scp_price'] = None
            card['price_source'] = None
            priced.append(card)
            continue

        try:
            year = int(year) if year else None
        except (TypeError, ValueError):
            year = None

        scp = find_scp_match_in_db(db, player, year, number, parallel, card_set)
        if scp and scp.get('scp_price'):
            card['scp_price'] = float(scp['scp_price'])
            card['price_source'] = 'scp'
            card['scp_url'] = scp.get('scp_url')
        else:
            card['scp_price'] = None
            card['price_source'] = None

        priced.append(card)

    return priced


def analyze_lot_listing(
    image_urls: List[str],
    lot_price: float,
    shipping: float = 0.0,
    db=None,
) -> Dict:
    """Full lot analysis: vision -> pricing -> profit calculation.

    Returns:
        {
            'cards_identified': [...],
            'cards_priced': int,
            'visible_value': float,
            'lot_cost': float,
            'estimated_profit': float,
            'worth_buying': bool,
            'confidence': 'high'|'medium'|'low',
            'note': str,
        }
    """
    all_cards = []
    for url in (image_urls or [])[:5]:  # Max 5 images per lot
        cards = identify_cards_in_image(url)
        all_cards.extend(cards)

    if not all_cards:
        return {
            'cards_identified': [],
            'cards_priced': 0,
            'visible_value': 0,
            'lot_cost': lot_price + shipping,
            'estimated_profit': -(lot_price + shipping),
            'worth_buying': False,
            'confidence': 'low',
            'note': 'No cards identified in lot photos',
        }

    # Price the identified cards
    if db:
        all_cards = price_identified_cards(all_cards, db)

    priced_cards = [c for c in all_cards if c.get('scp_price')]
    visible_value = sum(c['scp_price'] for c in priced_cards)
    lot_cost = lot_price + shipping
    net_after_fees = visible_value * (1 - FEE_RATE)
    profit = net_after_fees - lot_cost

    # Confidence based on how many cards we could price
    total_identified = len(all_cards)
    pct_priced = len(priced_cards) / max(total_identified, 1)
    if pct_priced >= 0.7 and total_identified >= 3:
        confidence = 'high'
    elif pct_priced >= 0.4:
        confidence = 'medium'
    else:
        confidence = 'low'

    return {
        'cards_identified': all_cards,
        'cards_priced': len(priced_cards),
        'cards_total': total_identified,
        'visible_value': round(visible_value, 2),
        'lot_cost': round(lot_cost, 2),
        'net_after_fees': round(net_after_fees, 2),
        'estimated_profit': round(profit, 2),
        'worth_buying': profit >= MIN_LOT_PROFIT,
        'confidence': confidence,
        'note': (
            f'{len(priced_cards)}/{total_identified} cards priced. '
            f'Visible value ${visible_value:.2f} (conservative -- hidden cards = $0).'
        ),
    }
