"""Comp Verification Service

After we identify what an eBay listing actually IS, verify its true market value
by looking up the correct SCP comp for that specific card — not the search target.

The problem this solves:
- Pipeline searches for "Aaron Judge 2025 Topps Chrome" (SCP says $250 for Gold /50)
- Finds an eBay listing titled "2025 Topps Chrome Aaron Judge Gold Wave /50"
- Old pipeline: assumes $250 comp because title matched "Gold"
- New pipeline: extracts the actual card identity, looks up Gold Wave /50 specifically
  in SCP cache, finds real comp is $25. Skips the bad opportunity.

Flow:
1. extract_card_identity(title, item_specifics) -> CardIdentity
2. find_matching_scp_comp(identity, db) -> verified price or None
3. If no cached comp, flag for manual review or SCP lookup
"""
import re
from dataclasses import dataclass, field
from typing import Optional, List
from sqlalchemy import text


@dataclass
class CardIdentity:
    """Extracted identity of a card from an eBay listing."""
    player_name: str
    year: Optional[int] = None
    manufacturer: Optional[str] = None  # Topps, Bowman, Panini, etc.
    card_set: Optional[str] = None  # Chrome, Heritage, Prizm, etc.
    card_number: Optional[str] = None
    parallel: Optional[str] = None  # Gold Wave, Blue Refractor, etc.
    serial_limit: Optional[int] = None  # /50, /99, /150, etc.
    is_auto: bool = False
    is_rc: bool = False
    is_graded: bool = False
    grade: Optional[str] = None
    confidence: float = 0.0  # 0-1 how confident we are in the identification


MANUFACTURERS = ['topps', 'bowman', 'panini', 'donruss', 'prizm', 'select',
                 'mosaic', 'optic', 'upper deck', 'fleer', 'leaf']

SETS = ['chrome', 'heritage', 'update', 'series 1', 'series 2', 'inception',
        'stadium club', 'sapphire', 'sterling', 'finest', 'gypsy queen',
        'allen & ginter', 'archives', 'gallery', "bowman's best", 'chrome black',
        'platinum', 'diamond kings', 'absolute', 'contenders', 'immaculate']

PARALLEL_PATTERNS = [
    # Numbered refractors (order matters - more specific first)
    r'(gold wave)\s*(?:refractor)?',
    r'(sky blue)\s*(?:border|refractor)?',
    r'(rose gold lava)\s*(?:refractor)?',
    r'(blue lava)\s*(?:refractor)?',
    r'(green shimmer)\s*(?:refractor)?',
    r'(gold shimmer)\s*(?:refractor)?',
    r'(orange shimmer)\s*(?:refractor)?',
    r'(aqua ray\s*wave)\s*(?:refractor)?',
    r'(blue ray\s*wave)\s*(?:refractor)?',
    r'(ray\s*wave)\s*(?:refractor)?',
    r'(negative)\s*(?:refractor)?',
    r'(x-fractor)',
    r'(mojo)\s*(?:refractor)?',
    r'(independence day)',
    r'(black)\s*(?:refractor)',
    r'(gold)\s*(?:refractor)',
    r'(green)\s*(?:refractor)',
    r'(blue)\s*(?:refractor)',
    r'(red)\s*(?:refractor)',
    r'(orange)\s*(?:refractor)',
    r'(purple)\s*(?:refractor)',
    r'(pink)\s*(?:refractor)',
    r'(aqua)\s*(?:refractor)',
    r'(sepia)\s*(?:refractor)?',
    r'(sonar)\s*(?:refractor)?',
    r'(speckle)\s*(?:refractor)?',
    r'(geometric)\s*(?:refractor)?',
    r'(teal)\s*(?:refractor)?',
    # Non-refractor parallels
    r'(golden mirror)',
    r'(sunflower seeds)',
    r'(cracked ice)',
    r'(camo)',
    r'(foil)',
    # Standalone colors (Bowman often uses "Blue /150" without "Refractor")
    r'\b(blue)\b(?!\s*(?:refractor|lava|ray|sonar))',
    r'\b(green)\b(?!\s*(?:refractor|shimmer|geometric))',
    r'\b(gold)\b(?!\s*(?:refractor|wave|shimmer|mirror))',
    r'\b(red)\b(?!\s*(?:refractor))',
    r'\b(orange)\b(?!\s*(?:refractor|shimmer))',
    r'\b(purple)\b(?!\s*(?:refractor))',
    r'\b(pink)\b(?!\s*(?:refractor))',
    r'\b(aqua)\b(?!\s*(?:refractor|ray))',
    # Generic fallback
    r'(refractor)',
]


def extract_card_identity(title: str, item_specifics: dict = None) -> CardIdentity:
    """Extract what card this actually is from the eBay listing title + specifics.

    Minimum required: player_name + manufacturer + year
    Everything else improves confidence.
    """
    tl = title.lower() if title else ''
    identity = CardIdentity(player_name='')

    # Year: 4-digit year between 2018-2027
    year_m = re.search(r'\b(20[12]\d)\b', tl)
    if year_m:
        identity.year = int(year_m.group(1))

    # Manufacturer
    for mfr in MANUFACTURERS:
        if mfr in tl:
            identity.manufacturer = mfr.title()
            break

    # Card set
    for s in SETS:
        if s in tl:
            identity.card_set = s.title()
            break

    # Card number: #123, #USC94, #BCP-29, etc.
    num_m = re.search(r'#([A-Z]*-?[A-Z]*\d+[A-Z]*)', title, re.IGNORECASE)
    if num_m:
        identity.card_number = num_m.group(1)

    # Serial limit: /50, /99, /150, etc.
    serial_m = re.search(r'/(\d+)', tl)
    if serial_m:
        identity.serial_limit = int(serial_m.group(1))

    # Auto
    identity.is_auto = bool(re.search(r'\b(auto|autograph|signed)\b', tl))

    # RC
    identity.is_rc = bool(re.search(r'\b(rc|rookie)\b', tl))

    # Graded
    grade_m = re.search(r'\b(psa|bgs|sgc|cgc)\s*(\d+\.?\d*)\b', tl)
    if grade_m:
        identity.is_graded = True
        identity.grade = f"{grade_m.group(1).upper()} {grade_m.group(2)}"

    # Parallel (most specific match wins)
    for pattern in PARALLEL_PATTERNS:
        m = re.search(pattern, tl)
        if m:
            identity.parallel = m.group(1).strip().title()
            break

    # Override with item specifics if available (structured > title parsing)
    if item_specifics:
        if item_specifics.get('parallel'):
            identity.parallel = item_specifics['parallel']
        if item_specifics.get('card_number'):
            identity.card_number = item_specifics['card_number']
        if item_specifics.get('card_year'):
            identity.year = int(item_specifics['card_year'])

    # Confidence: based on how many fields we extracted
    fields_found = sum([
        bool(identity.year),
        bool(identity.manufacturer),
        bool(identity.card_set),
        bool(identity.card_number),
        bool(identity.parallel),
        bool(identity.serial_limit),
    ])
    identity.confidence = min(fields_found / 6.0, 1.0)

    return identity


def find_matching_scp_comp(identity: CardIdentity, db, player_name: str) -> Optional[dict]:
    """Look up the correct SCP comp for this specific card identity.

    Returns dict with 'price', 'url', 'volume', 'sales_this_year' or None.
    """
    if not player_name or not identity.year:
        return None

    # Load all variants for this player+year from SCP cache
    rows = db.execute(text("""
        SELECT id, player_name, card_year, card_number, variants
        FROM scp_cache
        WHERE player_name ILIKE :player
          AND card_year = :year
    """), {'player': f'%{player_name}%', 'year': identity.year}).fetchall()

    if not rows:
        return None

    best_match = None
    best_score = 0

    for row in rows:
        variants = row.variants if isinstance(row.variants, list) else __import__('json').loads(row.variants)
        for v in variants:
            score = _score_variant_match(identity, v, row.card_number)
            if score > best_score:
                best_score = score
                best_match = {
                    'price': float(v.get('ungraded') or 0),
                    'url': v.get('url', ''),
                    'volume': v.get('volume', ''),
                    'sales_this_year': int(v.get('sales_this_year') or 0),
                    'parallel': v.get('parallel', 'Base'),
                    'card_set': v.get('card_set', ''),
                    'match_score': score,
                }

    # Require minimum match score to avoid bad comps
    if best_match and best_score >= 3:
        return best_match
    return None


def _score_variant_match(identity: CardIdentity, scp_variant: dict, scp_card_number: str) -> int:
    """Score how well an SCP variant matches the identified eBay card.

    Higher = better match. Need 3+ to be considered valid.
    """
    score = 0
    scp_parallel = (scp_variant.get('parallel') or 'Base').lower()
    scp_set = (scp_variant.get('card_set') or '').lower()

    # Parallel match (most important for pricing)
    if identity.parallel:
        id_par = identity.parallel.lower()
        if id_par == scp_parallel:
            score += 3  # Exact parallel match is worth the most
        elif id_par in scp_parallel or scp_parallel in id_par:
            score += 1  # Partial match (risky)
    elif scp_parallel == 'base':
        score += 2  # Both are base

    # Card number match
    if identity.card_number and scp_card_number:
        if identity.card_number.lower() == scp_card_number.lower():
            score += 2
        elif identity.card_number.lower() in scp_card_number.lower():
            score += 1

    # Serial limit match (confirms the right parallel)
    if identity.serial_limit and scp_parallel:
        serial_str = f"/{identity.serial_limit}"
        # Check if the SCP variant name or metadata mentions this serial
        scp_full = f"{scp_parallel} {scp_variant.get('url', '')}".lower()
        if serial_str in scp_full or str(identity.serial_limit) in scp_full:
            score += 2

    # Card set match
    if identity.card_set and scp_set:
        if identity.card_set.lower() in scp_set or scp_set in identity.card_set.lower():
            score += 1

    # Penalize graded vs ungraded mismatch
    if identity.is_graded:
        score -= 2  # We're comparing to ungraded SCP price

    return score


def verify_opportunity(listing: dict, search_variant: dict, db) -> Optional[dict]:
    """Full verification: identify the card, find its real comp, check profit.

    Returns opportunity dict with verified price, or None if not profitable.
    """
    title = listing.get('title', '')
    item_specifics = listing.get('item_specifics', {})

    # Step 1: What IS this card?
    identity = extract_card_identity(title, item_specifics)
    if identity.confidence < 0.33:
        return None  # Can't identify it well enough

    # Step 2: Find the correct SCP comp
    player = search_variant.get('player_name', '')
    comp = find_matching_scp_comp(identity, db, player)

    if not comp:
        # Couldn't find a matching comp — use search variant price only if
        # the parallel matches exactly
        if identity.parallel and search_variant.get('parallel'):
            if identity.parallel.lower() == search_variant['parallel'].lower():
                comp = {
                    'price': search_variant['scp_price'],
                    'parallel': search_variant['parallel'],
                    'match_score': 3,
                }
            else:
                return None  # Different parallel, no comp — skip
        else:
            return None

    # Step 3: Check profitability with VERIFIED price
    buy_price = listing.get('price', 0)
    shipping = listing.get('shipping', 5.0)
    scp_price = comp['price']

    if scp_price <= 0:
        return None

    net_sell = scp_price * (1 - 0.13)
    profit = net_sell - buy_price - shipping
    roi = (profit / (buy_price + shipping)) * 100 if (buy_price + shipping) > 0 else 0

    if profit < 5.0:
        return None

    return {
        'verified_scp_price': scp_price,
        'verified_parallel': comp.get('parallel', ''),
        'profit': round(profit, 2),
        'roi': round(roi, 1),
        'match_score': comp.get('match_score', 0),
        'identity': identity,
        'buy_price': buy_price,
        'shipping': shipping,
    }
