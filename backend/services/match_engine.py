"""
Card Match Engine - Confidence-based matching with multi-signal validation.

Architecture:
1. SCORE: Text signals from eBay title vs SCP data (free, instant)
2. REVIEW: Nova Pro reads the scoring breakdown (text, cheap)
3. RECOVER: If rejected, search SCP for the correct variant
4. SELECT: Nova picks from variant list if exact match fails
5. PROFIT: Math on the correctly matched card

Usage:
    from backend.services.match_engine import match_and_validate, find_best_scp_match

    result = match_and_validate(ebay_listing, scp_variants, db)
    # result = {
    #     'matched': True/False,
    #     'scp_variant': {...} or None,
    #     'confidence': 85,
    #     'method': 'score+review' | 'recovery' | 'nova_select',
    #     'breakdown': [...],
    # }
"""
from __future__ import annotations

import re
import json
import logging
from typing import Dict, List, Optional, Tuple

log = logging.getLogger('match_engine')

# ── SCORING WEIGHTS ──────────────────────────────────────────────────────────

SET_KEYWORDS = {
    'chrome': 15, 'heritage': 15, 'finest': 15, 'bowman': 12,
    'stadium club': 12, 'select': 12, 'prizm': 12, 'optic': 12,
    'flawless': 15, 'gilded': 15, 'immaculate': 15, 'museum': 15,
    'sapphire': 15, 'cosmic': 10, 'holiday': 10, 'ginter': 10,
    'donruss': 12, 'mosaic': 12,
}

PREMIUM_KEYWORDS = [
    'relic', 'autograph', 'auto ', 'real one', 'beam team',
    'medallion', 'patch', 'jersey', 'memorabilia',
]

LOT_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
    r'\blot\b', r'\d+\s*cards?\b', r'\d+x\b', r'\+\s*\d+\s*other',
]]

# Minimum score to auto-accept without Nova review
AUTO_ACCEPT_THRESHOLD = 80
# Below this, skip entirely (don't even ask Nova)
AUTO_REJECT_THRESHOLD = -10
# Between reject and accept, Nova reviews
REVIEW_THRESHOLD = (AUTO_REJECT_THRESHOLD, AUTO_ACCEPT_THRESHOLD)


def score_match(
    ebay_title: str,
    scp_player: str,
    scp_year: int,
    scp_number: str,
    scp_set: str,
    scp_parallel: str,
    scp_url: str = '',
) -> Tuple[int, List[str]]:
    """Score how confident we are that an eBay listing matches an SCP entry."""
    score = 0
    breakdown = []
    tl = (ebay_title or '').lower()

    # Player name
    if scp_player:
        parts = scp_player.lower().split()
        last = parts[-1] if parts else ''
        first = parts[0] if parts else ''
        if last and last in tl:
            score += 20
            breakdown.append(f'+20 player last name "{last}"')
            if first and first in tl:
                score += 5
                breakdown.append(f'+5  player first name "{first}"')
        else:
            score -= 30
            breakdown.append(f'-30 player "{scp_player}" NOT in title')

    # Year
    if scp_year:
        yr = str(scp_year)
        if yr in tl:
            score += 20
            breakdown.append(f'+20 year {yr}')
        else:
            url_lower = (scp_url or '').lower()
            penalty = -25 if (url_lower and yr not in url_lower) else -15
            score += penalty
            breakdown.append(f'{penalty} year {yr} not in title')

    # Card number
    if scp_number:
        num = scp_number.strip().lstrip('#')
        if f'#{num}' in tl or f'#{num} ' in tl or f'#{num}' in ebay_title:
            score += 15
            breakdown.append(f'+15 card number #{num}')
        elif num in tl:
            score += 5
            breakdown.append(f'+5  card number {num} loosely')
        else:
            score -= 10
            breakdown.append(f'-10 card number #{num} missing')

    # Set keywords
    ss = (scp_set or '').lower()
    for kw, weight in SET_KEYWORDS.items():
        scp_has = kw in ss
        ebay_has = kw in tl
        if scp_has and ebay_has:
            score += weight
            breakdown.append(f'+{weight} set "{kw}" in both')
        elif scp_has and not ebay_has:
            score -= weight
            breakdown.append(f'-{weight} SCP has "{kw}" not in title')
        elif ebay_has and not scp_has:
            if kw in ('flawless', 'gilded', 'immaculate', 'museum', 'sapphire'):
                score -= weight
                breakdown.append(f'-{weight} title has "{kw}" not in SCP')

    # Manufacturer
    scp_text = ss + ' ' + (scp_parallel or '').lower()
    if ('panini' in scp_text) != ('panini' in tl):
        score -= 30
        breakdown.append('-30 manufacturer mismatch (panini)')
    elif 'panini' in scp_text and 'panini' in tl:
        score += 10
        breakdown.append('+10 manufacturer match (panini)')

    # Premium keywords
    for kw in PREMIUM_KEYWORDS:
        if kw in scp_text and kw not in tl:
            score -= 25
            breakdown.append(f'-25 SCP has premium "{kw}" not in title')
        elif kw in scp_text and kw in tl:
            score += 15
            breakdown.append(f'+15 premium "{kw}" in both')

    # Parallel name
    sp = (scp_parallel or '').lower()
    if sp and sp != 'base':
        par_words = sp.split()
        hits = sum(1 for w in par_words if w in tl)
        if hits == len(par_words):
            score += 15
            breakdown.append(f'+15 all parallel words "{scp_parallel}"')
        elif hits > 0:
            score += 5
            breakdown.append(f'+5  partial parallel ({hits}/{len(par_words)})')
        else:
            score -= 10
            breakdown.append(f'-10 parallel "{scp_parallel}" missing')

    # Lot detection
    for pat in LOT_PATTERNS:
        if pat.search(tl):
            score -= 40
            breakdown.append(f'-40 lot detected')
            break

    # SCP URL year cross-check
    url_lower = (scp_url or '').lower()
    if url_lower and scp_year:
        m = re.search(r'(\d{4})', url_lower)
        if m and m.group(1) != str(scp_year):
            score -= 20
            breakdown.append(f'-20 SCP URL year {m.group(1)} != {scp_year}')

    return score, breakdown


def nova_review(ebay_title: str, scp_desc: str, score: int, breakdown: List[str]) -> Dict:
    """Ask Nova Pro to review a match based on text signals."""
    import boto3

    prompt = (
        'You are a trading card matching expert. Verify if this eBay listing '
        'matches this SportsCardsPro product.\n\n'
        f'eBay: "{ebay_title}"\n'
        f'SCP: "{scp_desc}"\n\n'
        f'Score: {score}. Breakdown:\n'
    )
    for b in breakdown:
        prompt += f'  {b}\n'
    prompt += (
        '\nIs this a CORRECT match? Check player, year, set, card number, variant.\n\n'
        'IMPORTANT: eBay sellers use different names for the same parallel. These are EQUIVALENT:\n'
        '- "Orange Chrome" = "Orange Bordered Chrome" = "Orange Chrome Parallel"\n'
        '- "Blue Speckle" = "Blue Sparkle" = "Blue Speckle Chrome"\n'
        '- "Silver Sparkle" = "Silver Sparkle Chrome" = "Chrome Silver Sparkle Refractor"\n'
        '- "Refractor" = "Chrome Refractor" (in Heritage sets, Chrome IS the refractor)\n'
        '- "Image Variation" = "Photo Variation" = "Cartoon Variation" (Heritage)\n'
        '- "Mojo" and "Mojo Refractor" are the same thing\n'
        '- "/25" or "/99" is the print run, not part of the variant name\n\n'
        'If the ONLY difference is naming style (not a fundamentally different card), '
        'it IS a correct match.\n\n'
        'A WRONG match is when they are genuinely different products:\n'
        '- "Gold Refractor" vs "Green Refractor" (different color = different card)\n'
        '- "Base" vs "Refractor" (different product type)\n'
        '- "Topps Series 1" vs "Panini Flawless" (different manufacturer/set)\n\n'
        'Answer JSON only: {"correct_match": true/false, "confidence": "high"/"medium"/"low", '
        '"reason": "brief explanation"}'
    )

    try:
        client = boto3.client('bedrock-runtime', region_name='us-east-1')
        body = {
            'messages': [{'role': 'user', 'content': [{'text': prompt}]}],
            'inferenceConfig': {'maxTokens': 200, 'temperature': 0.1}
        }
        resp = client.invoke_model(
            modelId='us.amazon.nova-pro-v1:0',
            body=json.dumps(body),
            contentType='application/json',
        )
        result = json.loads(resp['body'].read())
        text = result.get('output', {}).get('message', {}).get('content', [{}])[0].get('text', '')
        clean = text.strip().strip('`').strip()
        if clean.startswith('json'):
            clean = clean[4:].strip()
        return json.loads(clean)
    except Exception as e:
        return {'correct_match': None, 'reason': f'Nova error: {e}'}


def nova_select_variant(ebay_title: str, variants: List[Dict]) -> Optional[Dict]:
    """Ask Nova to pick the best SCP variant for an eBay listing."""
    import boto3

    # Build compact variant list
    var_list = []
    for v in variants:
        par = v.get('parallel', 'Base')
        price = v.get('ungraded', '?')
        var_list.append(f'[{par}] ${price}')
    var_str = ', '.join(var_list[:50])  # Cap at 50 to fit in prompt

    prompt = (
        f'eBay listing: "{ebay_title}"\n\n'
        f'Available SCP variants: {var_str}\n\n'
        f'Which variant is the best match? If none match, say "none".\n\n'
        f'NOTE: eBay sellers use different names for the same parallel. Examples:\n'
        f'- "Orange Chrome" = "Orange Bordered Chrome"\n'
        f'- "Blue Speckle" = "Blue Sparkle Chrome"\n'
        f'- "Mojo Refractor" = "Mojo"\n'
        f'- Print runs like /25 or /99 are NOT part of the variant name\n\n'
        f'Pick the variant that matches the card described in the eBay title. '
        f'Do NOT pick expensive rare variants (Superfractor, 1/1) unless the title explicitly names them.\n\n'
        f'Answer JSON: {{"best_match": "exact variant name or none", "reason": "why"}}'
    )

    try:
        client = boto3.client('bedrock-runtime', region_name='us-east-1')
        body = {
            'messages': [{'role': 'user', 'content': [{'text': prompt}]}],
            'inferenceConfig': {'maxTokens': 200, 'temperature': 0.1}
        }
        resp = client.invoke_model(
            modelId='us.amazon.nova-pro-v1:0',
            body=json.dumps(body),
            contentType='application/json',
        )
        result = json.loads(resp['body'].read())
        text = result.get('output', {}).get('message', {}).get('content', [{}])[0].get('text', '')
        clean = text.strip().strip('`').strip()
        if clean.startswith('json'):
            clean = clean[4:].strip()
        parsed = json.loads(clean)
        pick = (parsed.get('best_match') or '').lower().strip()
        if pick == 'none' or not pick:
            return None
        # Find the variant
        for v in variants:
            if (v.get('parallel') or 'Base').lower().strip() == pick:
                return v
        return None
    except Exception:
        return None


def recover_from_scp(
    db,
    player: str,
    year: int,
    card_number: str,
    ebay_title: str,
) -> Optional[Dict]:
    """Search SCP cache for the correct variant when initial match fails.

    1. Exact parallel match from title keywords
    2. Nova selects from available variants (only priced, non-rare)
    """
    from sqlalchemy import text as sqtext

    rows = db.execute(sqtext("""
        SELECT variants FROM scp_cache
        WHERE LOWER(player_name) = LOWER(:player)
          AND card_year = :year
          AND LOWER(card_number) = LOWER(:num)
    """), {'player': player, 'year': year, 'num': card_number}).fetchall()

    if not rows:
        return None

    # Collect all unique variants
    all_variants = []
    seen = set()
    for row in rows:
        variants = row[0] if isinstance(row[0], list) else json.loads(row[0])
        for v in variants:
            key = (v.get('parallel', ''), v.get('card_set', ''))
            if key not in seen:
                seen.add(key)
                all_variants.append(v)

    if not all_variants:
        return None

    tl = (ebay_title or '').lower()

    # Try exact parallel match from title -- require ALL words match
    # and the variant must have a price
    candidates = []
    for v in all_variants:
        par = (v.get('parallel') or 'Base').lower()
        if par == 'base':
            continue
        price = v.get('ungraded')
        if not price or float(price) <= 0:
            continue
        par_words = par.split()
        if len(par_words) >= 2 and all(w in tl for w in par_words):
            candidates.append(v)

    # If multiple candidates, pick the one with the most word overlap
    if candidates:
        best = max(candidates, key=lambda v: len((v.get('parallel') or '').split()))
        return best

    # Filter to reasonable variants for Nova (priced, not superfractor/printing plate)
    skip_words = {'superfractor', 'printing plate', '1/1'}
    priced = [
        v for v in all_variants
        if v.get('ungraded') and float(v.get('ungraded', 0)) > 0
        and not any(sw in (v.get('parallel') or '').lower() for sw in skip_words)
    ]
    if priced:
        return nova_select_variant(ebay_title, priced)

    return None


def match_and_validate(
    ebay_title: str,
    scp_card: Dict,
    scp_variant: Dict,
    db=None,
    skip_nova: bool = False,
    bin_price: float = None,
) -> Dict:
    """Full matching pipeline: score -> review -> recover -> BIN sanity check.

    Args:
        ebay_title: The eBay listing title
        scp_card: Dict with player_name, card_year, card_number
        scp_variant: The initially matched SCP variant
        db: Database session (needed for recovery)
        skip_nova: Skip Nova calls (for testing)
        bin_price: Buy It Now price from the listing (if hybrid auction/BIN)

    Returns:
        Dict with matched, scp_variant, confidence, method, breakdown
    """
    player = scp_card.get('player_name', '')
    year = scp_card.get('card_year')
    number = scp_card.get('card_number', '')

    # Step 1: Score
    s, bd = score_match(
        ebay_title, player, year, number,
        scp_variant.get('card_set', ''),
        scp_variant.get('parallel', ''),
        scp_variant.get('url', ''),
    )

    result = {
        'confidence': s,
        'breakdown': bd,
        'method': 'score',
    }

    # Auto-reject
    if s < AUTO_REJECT_THRESHOLD:
        result['matched'] = False
        result['scp_variant'] = None
        result['method'] = 'score_reject'
        # Try recovery
        if db:
            recovered = recover_from_scp(db, player, year, number, ebay_title)
            if recovered:
                result['scp_variant'] = recovered
                result['matched'] = True
                result['method'] = 'recovery'
                result['confidence'] = 50  # Recovery = medium confidence
        return result

    # Auto-accept (high score, all signals agree)
    if s >= AUTO_ACCEPT_THRESHOLD and not skip_nova:
        # Still run Nova as a sanity check on high-value matches
        scp_desc = f"{player} {year} #{number} [{scp_variant.get('card_set','')} {scp_variant.get('parallel','')}]"
        nova = nova_review(ebay_title, scp_desc, s, bd)
        if nova.get('correct_match') is False:
            result['matched'] = False
            result['scp_variant'] = None
            result['method'] = 'nova_reject'
            result['nova_reason'] = nova.get('reason', '')
            # Try recovery
            if db:
                recovered = recover_from_scp(db, player, year, number, ebay_title)
                if recovered:
                    result['scp_variant'] = recovered
                    result['matched'] = True
                    result['method'] = 'nova_reject_recovered'
                    result['confidence'] = 60
            return _apply_bin_check(result, bin_price)
        result['matched'] = True
        result['scp_variant'] = scp_variant
        result['method'] = 'score+nova_confirm'
        return _apply_bin_check(result, bin_price)

    if s >= AUTO_ACCEPT_THRESHOLD and skip_nova:
        result['matched'] = True
        result['scp_variant'] = scp_variant
        result['method'] = 'score_accept'
        return _apply_bin_check(result, bin_price)

    # Middle ground: Nova reviews
    if not skip_nova:
        scp_desc = f"{player} {year} #{number} [{scp_variant.get('card_set','')} {scp_variant.get('parallel','')}]"
        nova = nova_review(ebay_title, scp_desc, s, bd)
        if nova.get('correct_match') is True:
            result['matched'] = True
            result['scp_variant'] = scp_variant
            result['method'] = 'nova_confirm'
            result['confidence'] = s + 20  # Nova boost
            return _apply_bin_check(result, bin_price)
        else:
            result['matched'] = False
            result['scp_variant'] = None
            result['method'] = 'nova_reject'
            result['nova_reason'] = nova.get('reason', '')
            # Try recovery
            if db:
                recovered = recover_from_scp(db, player, year, number, ebay_title)
                if recovered:
                    result['scp_variant'] = recovered
                    result['matched'] = True
                    result['method'] = 'nova_reject_recovered'
                    result['confidence'] = 60
            return _apply_bin_check(result, bin_price)

    # No Nova, middle score = flag for review
    result['matched'] = True
    result['scp_variant'] = scp_variant
    result['method'] = 'score_flagged'
    result['flagged'] = True
    return _apply_bin_check(result, bin_price)


def _apply_bin_check(result: Dict, bin_price: float = None) -> Dict:
    """Apply BIN price sanity check to a match result.

    If the SCP price is way above the BIN price, flag it as suspicious.
    Don't reject -- just flag so the user knows to verify.
    """
    if not result.get('matched') or not result.get('scp_variant') or not bin_price:
        return result

    scp_price = float(result['scp_variant'].get('ungraded') or 0)
    if scp_price <= 0:
        return result

    suspicious, reason = bin_price_sanity_check(scp_price, bin_price)
    if suspicious:
        result['bin_warning'] = reason
        result['flagged'] = True
        result['confidence'] = max(result.get('confidence', 0) - 20, 0)

    return result


def bin_price_sanity_check(scp_price: float, bin_price: float) -> Tuple[bool, str]:
    """Check if the SCP price makes sense given the listing's BIN price.

    If a seller offers BIN at $10 but SCP says $70, the SCP price is
    likely stale or we matched the wrong variant. The seller who has
    the card in hand knows the market better than our cache.

    Returns (suspicious, reason).
    """
    if not bin_price or bin_price <= 0 or not scp_price or scp_price <= 0:
        return False, ''

    ratio = scp_price / bin_price

    if ratio > 3.0:
        return True, f'SCP ${scp_price:.2f} is {ratio:.1f}x the BIN ${bin_price:.2f} -- price likely stale or wrong variant'
    if ratio > 2.0:
        return True, f'SCP ${scp_price:.2f} is {ratio:.1f}x the BIN ${bin_price:.2f} -- verify SCP price'

    return False, ''
