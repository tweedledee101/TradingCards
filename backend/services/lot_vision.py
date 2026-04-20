"""
Lot Vision Pipeline - Detect, isolate, identify, and price cards in lot photos.

Pipeline:
1. DETECT: Find individual card regions in lot photo (Nova multimodal or OpenCV)
2. CROP: Extract each card as a separate image
3. IDENTIFY: Send each cropped card to Collectors Edge API for identification
4. PRICE: Look up SCP price for each identified card
5. EVALUATE: Sum visible value, compare to lot price, decide if worth buying

Conservative approach: only count cards you can SEE and IDENTIFY.
Hidden/obscured cards = $0. If visible value alone justifies the price, buy.

Sources: eBay lots, Facebook Marketplace lots, local card show lots (photo intake)

Usage:
    from backend.services.lot_vision import analyze_lot
    result = analyze_lot(image_urls=['https://...'], lot_price=50.00)

    # Or from CLI:
    python -m backend.services.lot_vision --image-url "https://..." --lot-price 50
"""
from __future__ import annotations

import io
import json
import os
import re
import requests
import tempfile
from typing import List, Dict, Optional, Tuple
from datetime import datetime


MIN_LOT_PROFIT = 15.0
FEE_RATE = 0.13
MAX_CARDS_PER_IMAGE = 20
MAX_IMAGES_PER_LOT = 8


def analyze_lot(
    image_urls: List[str],
    lot_price: float,
    shipping: float = 0.0,
    source: str = 'unknown',
    db=None,
    use_ce: bool = True,
    verbose: bool = False,
) -> Dict:
    """Full lot analysis pipeline.

    Args:
        image_urls: URLs of lot photos
        lot_price: Listed price for the entire lot
        shipping: Shipping cost
        source: Where the lot is from (ebay, facebook, etc.)
        db: SQLAlchemy session for SCP lookups
        use_ce: Use Collectors Edge API for card identification
        verbose: Print progress

    Returns analysis dict with cards_identified, visible_value, profit, etc.
    """
    all_cards: List[Dict] = []
    detection_stats = {'images_processed': 0, 'cards_detected': 0, 'cards_identified': 0}

    for img_url in (image_urls or [])[:MAX_IMAGES_PER_LOT]:
        if verbose:
            print(f"  Processing image: {img_url[:80]}...")

        # Step 1: Detect card regions
        regions = detect_card_regions(img_url, verbose=verbose)
        detection_stats['images_processed'] += 1
        detection_stats['cards_detected'] += len(regions)

        if not regions:
            # Fallback: treat entire image as one card (single card lot photo)
            regions = [{'bbox': None, 'image_url': img_url, 'method': 'full_image'}]

        # Step 2-3: For each detected card, identify it
        for region in regions[:MAX_CARDS_PER_IMAGE]:
            card_img_url = region.get('cropped_url') or region.get('image_url') or img_url

            if use_ce:
                identity = identify_card_via_ce(card_img_url, verbose=verbose)
            else:
                identity = identify_card_via_nova(card_img_url, verbose=verbose)

            if identity and identity.get('player_name'):
                identity['source_image'] = img_url
                identity['detection_method'] = region.get('method', 'unknown')
                all_cards.append(identity)
                detection_stats['cards_identified'] += 1

    # Step 4: Price each identified card
    if db and all_cards:
        all_cards = price_cards(all_cards, db, verbose=verbose)

    # Step 5: Evaluate
    return evaluate_lot(all_cards, lot_price, shipping, source, detection_stats)


def detect_card_regions(image_url: str, verbose: bool = False) -> List[Dict]:
    """Detect individual card regions in a lot photo.

    Uses Amazon Nova multimodal to describe what cards are visible
    and approximately where they are in the image.

    Returns list of detected regions with image URLs or crop coordinates.
    """
    # For now, use Nova to enumerate visible cards without cropping.
    # Each "region" is the full image + the card description Nova found.
    # Future: add OpenCV contour detection or Rekognition for actual bounding boxes.

    try:
        cards = _nova_detect_cards(image_url)
        if verbose and cards:
            print(f"    Nova detected {len(cards)} card(s)")
        return [
            {
                'image_url': image_url,
                'card_hint': card,
                'method': 'nova_multimodal',
            }
            for card in cards
        ]
    except Exception as e:
        if verbose:
            print(f"    Detection error: {e}")
        return []


def _nova_detect_cards(image_url: str) -> List[Dict]:
    """Ask Nova to enumerate individual cards visible in a lot photo."""
    try:
        from backend.services.vision_card_extract import extract_card_from_image
    except ImportError:
        return []

    prompt = (
        "This image shows a lot/bundle of multiple trading cards. "
        "List EVERY individual card you can identify. For each card provide:\n"
        "- player_name\n"
        "- card_year (4-digit year)\n"
        "- card_set (e.g. Topps Chrome, Bowman, Prizm)\n"
        "- card_number (if visible)\n"
        "- parallel (e.g. Refractor, Gold, Base)\n"
        "- confidence (high/medium/low based on how clearly you can read it)\n\n"
        "Return ONLY a JSON array. If you can only see one card, return an array with one object. "
        "Skip any card you cannot read clearly."
    )

    result = extract_card_from_image(image_url, custom_prompt=prompt)
    if not result:
        return []

    if isinstance(result, list):
        return [r for r in result if isinstance(r, dict) and r.get('player_name')]
    elif isinstance(result, dict) and result.get('player_name'):
        return [result]
    return []


def identify_card_via_ce(image_url: str, verbose: bool = False) -> Optional[Dict]:
    """Identify a single card using Collectors Edge API.

    CE returns structured data: player, year, set, variant, pricing.
    More accurate than Nova for card identification because it's trained
    specifically on trading cards.
    """
    try:
        from backend.utils.collectors_edge_result import call_ce_identify_api, ce_extracted_from_api_json
    except ImportError:
        if verbose:
            print("    CE API not available, falling back to Nova")
        return identify_card_via_nova(image_url, verbose=verbose)

    try:
        # Download image
        resp = requests.get(image_url, timeout=15)
        if resp.status_code != 200:
            return None

        api_json = call_ce_identify_api(resp.content, timeout=120)
        if not api_json:
            return None

        extracted = ce_extracted_from_api_json(api_json)
        identity = extracted.get('identity', {})

        return {
            'player_name': identity.get('player'),
            'card_year': identity.get('year'),
            'card_set': identity.get('set'),
            'card_number': identity.get('card_number'),
            'parallel': identity.get('variant') or 'Base',
            'confidence': 'high' if identity.get('player') else 'low',
            'identification_source': 'collectors_edge',
            'ce_pricing': extracted.get('pricing', {}),
        }
    except Exception as e:
        if verbose:
            print(f"    CE identification error: {e}")
        return None


def identify_card_via_nova(image_url: str, verbose: bool = False) -> Optional[Dict]:
    """Identify a single card using Amazon Nova multimodal."""
    try:
        from backend.services.vision_card_extract import extract_card_from_image
    except ImportError:
        return None

    result = extract_card_from_image(image_url)
    if not result:
        return None

    if isinstance(result, dict):
        return {
            'player_name': result.get('player_name'),
            'card_year': result.get('card_year') or result.get('year'),
            'card_set': result.get('card_set') or result.get('set'),
            'card_number': result.get('card_number') or result.get('number'),
            'parallel': result.get('parallel') or result.get('variant') or 'Base',
            'confidence': result.get('confidence', 'medium'),
            'identification_source': 'nova',
        }
    return None


def price_cards(cards: List[Dict], db, verbose: bool = False) -> List[Dict]:
    """Look up SCP prices for each identified card."""
    from backend.services.scp_db_match import find_scp_match_in_db

    for card in cards:
        player = card.get('player_name')
        year = card.get('card_year')
        number = card.get('card_number')
        parallel = card.get('parallel', 'Base')
        card_set = card.get('card_set', '')

        if not player or not number:
            card['scp_price'] = None
            continue

        try:
            year = int(year) if year else None
        except (TypeError, ValueError):
            year = None

        scp = find_scp_match_in_db(db, player, year, number, parallel, card_set)
        if scp and scp.get('scp_price'):
            card['scp_price'] = float(scp['scp_price'])
            card['scp_url'] = scp.get('scp_url')
            if verbose:
                print(f"    Priced: {player} {year} #{number} [{parallel}] = ${card['scp_price']:.2f}")
        else:
            card['scp_price'] = None
            # Try CE pricing if available
            ce_pricing = card.get('ce_pricing', {})
            if ce_pricing.get('median'):
                card['scp_price'] = float(ce_pricing['median'])
                card['price_source'] = 'collectors_edge'
                if verbose:
                    print(f"    CE priced: {player} {year} #{number} = ${card['scp_price']:.2f}")

    return cards


def evaluate_lot(
    cards: List[Dict],
    lot_price: float,
    shipping: float,
    source: str,
    detection_stats: Dict,
) -> Dict:
    """Evaluate whether a lot is worth buying based on identified card values."""
    priced_cards = [c for c in cards if c.get('scp_price')]
    visible_value = sum(c['scp_price'] for c in priced_cards)
    lot_cost = lot_price + shipping
    net_after_fees = visible_value * (1 - FEE_RATE)
    profit = net_after_fees - lot_cost

    total_identified = len(cards)
    pct_priced = len(priced_cards) / max(total_identified, 1)

    if pct_priced >= 0.7 and total_identified >= 3:
        confidence = 'high'
    elif pct_priced >= 0.4 or total_identified >= 2:
        confidence = 'medium'
    else:
        confidence = 'low'

    # Build per-card breakdown for the UI
    card_breakdown = []
    for c in cards:
        card_breakdown.append({
            'player_name': c.get('player_name'),
            'card_year': c.get('card_year'),
            'card_set': c.get('card_set'),
            'card_number': c.get('card_number'),
            'parallel': c.get('parallel'),
            'scp_price': c.get('scp_price'),
            'confidence': c.get('confidence', 'medium'),
            'identification_source': c.get('identification_source', 'unknown'),
        })

    return {
        'source': source,
        'lot_price': round(lot_price, 2),
        'shipping': round(shipping, 2),
        'lot_cost': round(lot_cost, 2),
        'cards_identified': total_identified,
        'cards_priced': len(priced_cards),
        'visible_value': round(visible_value, 2),
        'net_after_fees': round(net_after_fees, 2),
        'estimated_profit': round(profit, 2),
        'worth_buying': profit >= MIN_LOT_PROFIT,
        'confidence': confidence,
        'card_breakdown': card_breakdown,
        'detection_stats': detection_stats,
        'note': (
            f'{len(priced_cards)}/{total_identified} cards priced from {detection_stats["images_processed"]} image(s). '
            f'Visible value ${visible_value:.2f}. Hidden cards treated as $0.'
        ),
        'analyzed_at': datetime.utcnow().isoformat(),
    }


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Lot Vision Pipeline')
    parser.add_argument('--image-url', required=True, help='URL of lot photo')
    parser.add_argument('--lot-price', type=float, required=True, help='Listed price for the lot')
    parser.add_argument('--shipping', type=float, default=0.0)
    parser.add_argument('--source', default='manual', help='Where the lot is from')
    parser.add_argument('--no-ce', action='store_true', help='Skip Collectors Edge, use Nova only')
    parser.add_argument('--verbose', '-v', action='store_true')
    args = parser.parse_args()

    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend', '.env'))
    from contextlib import closing
    from backend.utils.database import SessionLocal

    print(f'Analyzing lot: ${args.lot_price:.2f} + ${args.shipping:.2f} shipping')
    print(f'Source: {args.source}')
    print(f'Image: {args.image_url[:80]}')
    print()

    with closing(SessionLocal()) as db:
        result = analyze_lot(
            image_urls=[args.image_url],
            lot_price=args.lot_price,
            shipping=args.shipping,
            source=args.source,
            db=db,
            use_ce=not args.no_ce,
            verbose=args.verbose,
        )

    print(f'\n{"="*60}')
    print(f'LOT ANALYSIS RESULT')
    print(f'{"="*60}')
    print(f'Cards identified: {result["cards_identified"]}')
    print(f'Cards priced:     {result["cards_priced"]}')
    print(f'Visible value:    ${result["visible_value"]:.2f}')
    print(f'Lot cost:         ${result["lot_cost"]:.2f}')
    print(f'Net after fees:   ${result["net_after_fees"]:.2f}')
    print(f'Est. profit:      ${result["estimated_profit"]:.2f}')
    print(f'Worth buying:     {"YES" if result["worth_buying"] else "NO"}')
    print(f'Confidence:       {result["confidence"]}')

    if result['card_breakdown']:
        print(f'\nCard breakdown:')
        for c in result['card_breakdown']:
            price = f'${c["scp_price"]:.2f}' if c.get('scp_price') else 'unpriced'
            print(f'  {price:>10} | {c.get("player_name", "?")} {c.get("card_year", "?")} {c.get("card_set", "")} #{c.get("card_number", "?")} [{c.get("parallel", "Base")}]')
