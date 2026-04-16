#!/usr/bin/env python3
"""
eBay-First Auction Opportunity Pipeline

Flips the standard pipeline on its head:
1. Search eBay for auctions ending within X hours (broad by year + sport)
2. Filter for quality: serialed, auto, rookie, card number present
3. Validate against SCP: DB lookup first, Selenium fallback
4. Profit check: SCP * 0.87 - (bid + shipping) >= $10

Usage:
    python3 find_auction_opportunities.py
    python3 find_auction_opportunities.py --hours 24 --min-profit 15
    python3 find_auction_opportunities.py --years 2024,2025 --sport baseball
"""
import argparse
import re
import time
from contextlib import closing
from datetime import datetime
import shutil
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from backend.scrapers.ebay_scraper import EbayScraper
from backend.scrapers.sportscardspro_scraper import SportsCardsProScraper
from backend.utils.job_tracker import JobTracker
from backend.utils.logger import get_logger
from sqlalchemy import func, or_
from backend.utils.database import SessionLocal
from backend.utils.listing_card_identity import card_number_tokens_from_free_text
from backend.models import Opportunity, Card, MarketRate
from backend.services.scp_db_match import find_scp_match_in_db

log = get_logger('auction_finder')

FEE_RATE = 0.13
DEFAULT_SHIPPING = 5.00
MIN_PROFIT = 10.00

# Quality signals -- auction must have at least one
SERIAL_PATTERN = re.compile(r'/\d{1,4}\b')
AUTO_KEYWORDS = ['auto', 'autograph', 'signed', 'on card auto', 'on-card auto']
ROOKIE_KEYWORDS = ['rc', 'rookie', '1st bowman', 'first bowman']

# Junk filters (same as BIN pipeline)
JUNK_PATTERNS = [
    'you pick', 'pick your', 'complete your set', 'pick a card',
    'choose your', 'pick em', "pick 'em", 'buy 3 get',
    'lot of', 'mystery', 'repack', 'break',
    'digital', 'bunt'
]
REPRINT_PATTERNS = [
    'replica', 'reprint', 'rp', 'project 2020', 'project 70', 'project70',
    'shoebox treasures', 'sticker', 'die-cut replica', 'custom card',
    'novelty', 'art card', 'aceo'
]
FACTORY_SET_PATTERNS = [
    'complete set', 'complete sets', 'factory set', 'factory sealed',
    'hobby set', 'retail set', '582 montgomery', 'montgomery club',
    'walmart exclusive', 'target exclusive'
]

# Volume terms that mean the card is dead
LOW_VOLUME = ['rare', '1 sale per year', '2 sales per year']

# Step 2 drops (no_year / no_card_number / no_player) → bounded post-pipeline vision sample
# (merged into vision_post_pipeline_queue_sample). Uses image URLs already on the listing from
# Browse search + GET /item only when that item call ran for missing #/player/year (no extra
# API round-trips solely for vision).
STEP2_VISION_CAP_PER_REASON = 25

# Minimum BIN comps required to trust eBay-derived market price
MIN_COMPS = 3
# Minimum sold comps from 130point to trust the price
MIN_SOLD_COMPS = 3


def _auction_http_gallery_urls(auction: dict) -> list:
    """Browse + merged item-detail gallery; only http(s) URLs, max 15."""
    vu = list(auction.get('image_urls') or [])
    iu = (auction.get('image_url') or '').strip()
    if iu.startswith('http') and iu not in vu:
        vu.insert(0, iu)
    return [u for u in vu if isinstance(u, str) and u.strip().startswith('http')][:15]


def _merge_auction_gallery_from_item_details(auction: dict, details: dict) -> None:
    """Merge GET /item gallery into auction (same shape as Step 2 primary detail path)."""
    if not details:
        return
    extras = details.get('image_urls') or []
    base = list(auction.get('image_urls') or [])
    seen: set = set()
    merged: list = []
    for u in base + extras:
        if u and u not in seen:
            seen.add(u)
            merged.append(u)
    auction['image_urls'] = merged
    if merged:
        auction['image_url'] = merged[0]


def _append_step2_vision_sample(
    auction: dict,
    title: str,
    skip_key: str,
    queue: list,
    counts: dict,
    cap_per_reason: int,
) -> None:
    """Under cap and HTTP gallery already present → queue for vision_retry after the run (no new eBay calls here)."""
    if counts.get(skip_key, 0) >= cap_per_reason:
        return
    urls = _auction_http_gallery_urls(auction)
    if not urls:
        return
    counts[skip_key] = counts.get(skip_key, 0) + 1
    queue.append(
        {
            'reason': f'step2_{skip_key}',
            'step2_skip': skip_key,
            'ebay_item_id': auction.get('ebay_item_id'),
            'title': title[:240],
            'image_urls': urls,
            'note': (
                'Step 2 dropped (incomplete player/year/# from text); '
                'vision may read identity from photos. Does not gate ingest.'
            ),
        }
    )


def gather_card_number_candidates(title: str, aspects: dict, extra_text: str = None) -> list:
    """Ordered unique candidates: eBay Card Number aspects, then title/description tokens (#, Card No., CN:, …)."""
    seen = set()
    out = []

    def add(x):
        if not x:
            return
        s = str(x).strip()
        if not s:
            return
        k = s.lower()
        if k not in seen:
            seen.add(k)
            out.append(s)

    for key in ('Card Number', 'Card No', 'Card No.'):
        if key in aspects and aspects[key]:
            add(aspects[key])
    for t in card_number_tokens_from_free_text(title or ''):
        add(t)
    for t in card_number_tokens_from_free_text(extra_text or ''):
        add(t)
    return out


def pick_card_number_with_catalog(
    candidates: list,
    db,
    player_name: str,
    year: int,
    sport: str,
    cache: dict,
):
    """If several # tokens exist, prefer one that exists in cards for player+year+sport."""
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    if not player_name or not year or db is None:
        return candidates[0]
    key = (player_name.lower().strip(), int(year), (sport or '').lower())
    if key not in cache:
        rows = db.query(Card.card_number).filter(
            func.lower(Card.player_name) == player_name.lower().strip(),
            Card.card_year == year,
            Card.card_number.isnot(None),
            or_(
                Card.sport.is_(None),
                func.lower(Card.sport) == (sport or '').lower(),
            ),
        ).distinct().all()
        cache[key] = {str(r[0]).strip().lower(): str(r[0]).strip() for r in rows if r[0]}
    cmap = cache[key]
    if not cmap:
        return candidates[0]
    for c in candidates:
        cl = c.lower()
        if cl in cmap:
            return cmap[cl]
    return candidates[0]


def load_known_players(years: list = None, sport: str = 'baseball'):
    """Load player names from MLB Stats API + DB fallback.
    
    MLB API gives ~1,400 players/year (every 40-man roster).
    DB adds any names not covered (custom targets, etc.).
    Names are normalized (accents stripped) for matching.
    """
    import requests
    import unicodedata

    names = set()

    # MLB Stats API -- free, no auth
    if sport == 'baseball' and years:
        for year in years:
            try:
                resp = requests.get(
                    f'https://statsapi.mlb.com/api/v1/sports/1/players?season={year}',
                    timeout=10
                )
                if resp.status_code == 200:
                    people = resp.json().get('people', [])
                    for p in people:
                        name = p.get('fullName')
                        if name:
                            names.add(name)
                            # Also add accent-stripped version
                            stripped = unicodedata.normalize('NFD', name)
                            stripped = ''.join(c for c in stripped if unicodedata.category(c) != 'Mn')
                            if stripped != name:
                                names.add(stripped)
            except Exception as e:
                log.warn(f'MLB API failed for {year}: {e}', category='mlb_api')

    # DB fallback -- catches custom targets not in MLB rosters
    db = SessionLocal()
    try:
        players = db.query(Card.player_name).distinct().all()
        for p in players:
            if p[0]:
                names.add(p[0])
    finally:
        db.close()

    # Sort longest names first so "Juan Soto" matches before "Juan"
    return sorted(names, key=len, reverse=True)


def extract_player_name(title: str, aspects: dict, known_players: list) -> str:
    """Match player name against known DB players first, then check aspects."""
    import unicodedata
    title_lower = title.lower().replace('.', '')
    # Also build accent-stripped version of title for matching
    title_stripped = unicodedata.normalize('NFD', title_lower)
    title_stripped = ''.join(c for c in title_stripped if unicodedata.category(c) != 'Mn')

    # Pass 1: match against known players from DB/MLB API
    for player in known_players:
        player_lower = player.lower().replace('.', '')
        if player_lower in title_lower or player_lower in title_stripped:
            return player

    # Pass 2: check eBay item aspects (only populated from get_full_item_details)
    for key in ['Player', 'Player/Athlete', 'Athlete', 'Player Name']:
        if key in aspects and aspects[key]:
            return aspects[key]

    return None


# Release / copyright years on card listings (not jersey numbers).
_YEAR_IN_TEXT_RE = re.compile(r'\b(19[89]\d|20\d{2})\b')


def _clamp_card_listing_year(y):
    if y is None:
        return None
    try:
        y = int(y)
    except (TypeError, ValueError):
        return None
    now = datetime.utcnow().year
    if 1980 <= y <= now + 1:
        return y
    return None


def _first_year_in_text(text: str) -> int:
    """First plausible 4-digit card year in text (title or description)."""
    if not text:
        return None
    m = _YEAR_IN_TEXT_RE.search(text)
    while m:
        y = _clamp_card_listing_year(int(m.group(1)))
        if y is not None:
            return y
        m = _YEAR_IN_TEXT_RE.search(text, m.end())
    return None


def extract_year(title: str, aspects: dict, extra_text: str = None) -> int:
    """Extract year from eBay Year aspect, then title, then optional description blob."""
    if 'Year' in aspects:
        try:
            y = int(str(aspects['Year']).strip())
            y = _clamp_card_listing_year(y)
            if y is not None:
                return y
        except (ValueError, TypeError):
            pass

    y = _first_year_in_text(title or '')
    if y is not None:
        return y
    if extra_text:
        return _first_year_in_text(extra_text)
    return None


def infer_year_if_unique_in_catalog(db, player_name: str, card_number: str, sport: str):
    """If exactly one card_year exists for player+# (+sport), use it (year is not in title)."""
    if not db or not player_name or not card_number:
        return None
    rows = db.query(Card.card_year).filter(
        func.lower(Card.player_name) == player_name.lower().strip(),
        func.lower(Card.card_number) == str(card_number).lower().strip(),
        or_(Card.sport.is_(None), func.lower(Card.sport) == (sport or '').lower()),
    ).distinct().all()
    years = sorted({r[0] for r in rows if r[0] is not None})
    if len(years) == 1:
        return years[0]
    return None


def _set_match_tokens(s: str) -> set:
    if not s:
        return set()
    raw = re.sub(r'[^a-z0-9\s]+', ' ', (s or '').lower())
    return {w for w in raw.split() if len(w) > 2}


def resolve_year_from_set_hint(
    db, player_name: str, card_number: str, sport: str, set_hint: str,
):
    """When player+# exists in multiple years, pick year whose card_set best overlaps eBay Set/title set."""
    if not db or not player_name or not card_number or not set_hint:
        return None
    sh = (set_hint or '').strip()
    if sh.lower() in ('unknown', 'base', ''):
        return None
    rows = db.query(Card.card_year, Card.card_set).filter(
        func.lower(Card.player_name) == player_name.lower().strip(),
        func.lower(Card.card_number) == str(card_number).lower().strip(),
        Card.card_year.isnot(None),
        Card.card_set.isnot(None),
        or_(
            Card.sport.is_(None),
            func.lower(Card.sport) == (sport or '').lower(),
        ),
    ).distinct().all()
    hint_tok = _set_match_tokens(sh)
    if not hint_tok:
        return None
    scores = {}
    for cy, cs in rows:
        if not cy or not cs:
            continue
        overlap = hint_tok & _set_match_tokens(cs)
        if not overlap:
            continue
        score = len(overlap) / max(len(hint_tok), 1)
        if score > scores.get(cy, 0):
            scores[cy] = score
    if not scores:
        return None
    best = max(scores.values())
    if best < 0.35:
        return None
    winners = [y for y, sc in scores.items() if sc == best]
    if len(winners) == 1:
        return winners[0]
    return None


def has_quality_signal(title: str, aspects: dict) -> bool:
    """Check if auction has at least one quality signal: serialed, auto, or rookie."""
    title_lower = title.lower()

    if SERIAL_PATTERN.search(title):
        return True

    if any(kw in title_lower for kw in AUTO_KEYWORDS):
        return True

    if any(kw in title_lower for kw in ROOKIE_KEYWORDS):
        return True

    # Check aspects
    parallel = aspects.get('Parallel/Variety', aspects.get('Parallel', '')).lower()
    if parallel and parallel != 'base':
        return True

    features = aspects.get('Features', '').lower()
    if 'autograph' in features or 'rookie' in features:
        return True

    return False


def is_lot(title: str) -> bool:
    """Detect multi-card lots. Multiple card numbers or lot language."""
    # Multiple # signs = multiple cards
    hashes = re.findall(r'#[A-Za-z0-9-]+', title)
    if len(hashes) >= 2:
        return True
    # Lot patterns: "3 cards", "(3)", leading digit + player name
    if re.search(r'\b\d+\s*(card|cards|card lot|lot)\b', title, re.IGNORECASE):
        return True
    # "X & Y & Z" pattern with set names
    if title.count(' & ') >= 2:
        return True
    return False


def is_junk(title: str) -> bool:
    """Check if listing is junk/reprint/factory set/lot."""
    title_lower = title.lower()
    if any(j in title_lower for j in JUNK_PATTERNS):
        return True
    if any(r in title_lower for r in REPRINT_PATTERNS):
        return True
    if any(f in title_lower for f in FACTORY_SET_PATTERNS):
        return True
    if is_lot(title):
        return True
    return False


def _scp_url_has_card_number(url: str, card_number: str) -> bool:
    """Check if SCP URL contains the expected card number."""
    if not url or not card_number:
        return False
    url_lower = url.lower()
    cn_lower = card_number.lower()
    # SCP URLs use formats like: player-name-139, player-name-fma-cc
    return f'-{cn_lower}' in url_lower or url_lower.endswith(cn_lower)


# Words that don't help distinguish parallels
_NOISE_WORDS = {'the', 'of', 'and', 'a', 'an', 'in', 'on', 'for', 'to', 'is',
                'card', 'cards', 'baseball', 'topps', 'panini', 'bowman',
                'chrome', 'update', 'series', 'heritage', 'tier', 'one',
                'museum', 'collection', 'tribute', 'finest', 'inception',
                'gallery', 'stadium', 'club', 'sterling', 'best', 'draft',
                'prizm', 'select', 'mosaic', 'donruss', 'optic',
                'variation', 'variations', 'parallel', 'variety'}


def _parallel_words(text: str) -> set:
    """Extract meaningful parallel-identifying words from text."""
    return {w for w in re.findall(r'[a-z]+', text.lower()) if w not in _NOISE_WORDS and len(w) > 1}


def _find_parallel_in_text(text: str, scp_variants: list) -> dict:
    """Given eBay text (title/description), find which SCP variant it matches.
    
    Pass 2A: Check if ALL words of an SCP parallel appear in the eBay text (original strict match).
    Pass 2B: Score each SCP variant by word overlap with eBay text, pick best if unambiguous.
    """
    text_lower = text.lower()
    
    # Sort variants by parallel name length (longest first) to avoid
    # "Gold" matching before "Gold Refractor"
    sorted_variants = sorted(scp_variants, key=lambda v: len(v.get('parallel') or ''), reverse=True)
    
    # Pass 2A: strict -- ALL words of SCP parallel appear in eBay text
    for variant in sorted_variants:
        parallel = (variant.get('parallel') or 'Base')
        if parallel == 'Base':
            continue
        parallel_lower = parallel.lower()
        words = parallel_lower.split()
        if all(w in text_lower for w in words):
            return variant
    
    # Pass 2B: fuzzy word overlap scoring
    ebay_words = _parallel_words(text)
    if not ebay_words:
        return None
    
    scored = []
    for variant in sorted_variants:
        parallel = (variant.get('parallel') or 'Base')
        if parallel == 'Base':
            continue
        scp_words = _parallel_words(parallel)
        if not scp_words:
            continue
        overlap = ebay_words & scp_words
        if not overlap:
            continue
        # Score: fraction of SCP words found in eBay text
        score = len(overlap) / len(scp_words)
        # Require at least 1 meaningful word match and >50% overlap
        if score >= 0.5 and len(overlap) >= 1:
            scored.append((score, len(overlap), variant))
    
    if not scored:
        return None
    
    # Sort by score desc, then overlap count desc
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    
    # If top match is clearly better than second, use it
    if len(scored) == 1:
        return scored[0][2]
    if scored[0][0] > scored[1][0]:
        return scored[0][2]
    # If tied on score, pick the one with more overlapping words
    if scored[0][1] > scored[1][1]:
        return scored[0][2]
    
    # Ambiguous -- don't guess
    return None


def _extract_ebay_signals(title: str, aspects: dict) -> dict:
    """Extract matching signals from eBay listing: RC, Auto, Relic, print run."""
    title_lower = title.lower()
    signals = {
        'is_rc': bool(re.search(r'\brc\b|\brookie\b', title_lower)),
        'is_auto': any(kw in title_lower for kw in AUTO_KEYWORDS),
        'is_relic': bool(re.search(r'\brelic\b|\bpatch\b|\bjersey\b|\bgame.?used\b', title_lower)),
        'print_run': None,
    }
    # /25, /50, /99 etc.
    pr_match = re.search(r'/(\d+)\b', title)
    if pr_match:
        signals['print_run'] = int(pr_match.group(1))
    # Aspects
    features = (aspects.get('Features', '') or '').lower()
    if 'autograph' in features:
        signals['is_auto'] = True
    if 'rookie' in features:
        signals['is_rc'] = True
    if 'relic' in features or 'patch' in features:
        signals['is_relic'] = True
    return signals


def _match_by_signals(scp_variants: list, ebay_signals: dict) -> dict:
    """Pass 3: Narrow SCP variants using RC/Auto/Relic/print_run signals.
    
    Returns best match if we can narrow to 1 candidate, or the
    lowest-priced candidate (flagged) if 2-3 remain. None if too ambiguous.
    """
    candidates = list(scp_variants)  # start with all priced variants
    
    # Filter by Auto: if eBay says auto, only keep SCP autos (and vice versa)
    ebay_auto = ebay_signals.get('is_auto', False)
    auto_filtered = [v for v in candidates if v.get('is_auto', False) == ebay_auto]
    if auto_filtered:
        candidates = auto_filtered
    
    # Filter by Relic: if eBay says relic, only keep SCP entries with relic-like set/title
    ebay_relic = ebay_signals.get('is_relic', False)
    if ebay_relic:
        relic_filtered = [v for v in candidates
                         if any(kw in (v.get('set_text') or v.get('card_set') or v.get('raw_title') or '').lower()
                                for kw in ['relic', 'patch', 'jersey', 'material', 'game used'])]
        if relic_filtered:
            candidates = relic_filtered
        else:
            # eBay says relic but no SCP relic variants -- can't match
            return None
    
    # Filter by RC: if eBay says RC, prefer SCP RCs
    ebay_rc = ebay_signals.get('is_rc', False)
    if ebay_rc:
        rc_filtered = [v for v in candidates if v.get('is_rc', False)]
        if rc_filtered:
            candidates = rc_filtered
    
    # Filter by print run: /25 should match /25
    ebay_pr = ebay_signals.get('print_run')
    if ebay_pr:
        pr_filtered = [v for v in candidates if v.get('print_run') == ebay_pr]
        if pr_filtered:
            candidates = pr_filtered
    
    if len(candidates) == 1:
        return candidates[0]
    
    if 2 <= len(candidates) <= 3:
        # Pick lowest-priced (conservative estimate), will be flagged
        candidates.sort(key=lambda v: v.get('ungraded') or 9999)
        return candidates[0]
    
    # Too many candidates -- can't narrow down
    return None


def _get_scp_variants(scp_scraper, db, player_name: str, card_year: int,
                      card_set: str, card_number: str) -> list:
    """Get SCP variants for a card. Checks cache first, Selenium fallback.
    
    Returns list of priced SCP variant dicts, or empty list.
    Caches results for 24 hours.
    """
    from backend.models import SCPCache
    from datetime import datetime, timedelta
    import json

    # scp_cache columns: player_name VARCHAR(255), card_number VARCHAR(50)
    _pn = (player_name or "").strip()
    _cn = (card_number or "").strip()
    if not _cn:
        return [], False

    cache_ok = len(_pn) <= 255 and len(_cn) <= 50

    # Check cache (24h TTL); skip if identity too long (e.g. whole roster misparsed as one "player")
    if cache_ok:
        cache_cutoff = datetime.now() - timedelta(hours=24)
        cached = db.query(SCPCache).filter(
            SCPCache.player_name.ilike(_pn),
            SCPCache.card_year == card_year,
            SCPCache.card_number.ilike(_cn),
            SCPCache.created_at > cache_cutoff
        ).first()

        if cached:
            variants = cached.variants if isinstance(cached.variants, list) else json.loads(cached.variants)
            priced = [v for v in variants if v.get('ungraded')]
            if priced:
                return priced, True  # True = cache hit

    # Cache miss -- Selenium lookup
    if not scp_scraper or scp_scraper is False:
        return [], False

    # Try full query first, then simpler fallback
    queries = []
    parts = [_pn]
    if card_year:
        parts.append(str(card_year))
    if card_set:
        parts.append(card_set)
    parts.append(f"#{_cn}")
    queries.append(' '.join(parts))

    if card_set:
        simple_parts = [_pn]
        if card_year:
            simple_parts.append(str(card_year))
        simple_parts.append(f"#{_cn}")
        queries.append(' '.join(simple_parts))

    all_matches = []
    for query in queries:
        results = scp_scraper.search(query)
        if not results:
            continue
        card_number_matches = [r for r in results if _scp_url_has_card_number(r.get('url', ''), _cn)]
        if card_number_matches:
            all_matches = card_number_matches
            break

    # Store in cache (even empty results, to avoid re-scraping)
    try:
        if cache_ok:
            # Serialize for JSONB -- strip non-serializable fields
            cache_data = []
            for v in all_matches:
                cache_data.append({
                    'parallel': v.get('parallel', 'Base'),
                    'ungraded': v.get('ungraded'),
                    'grade_9': v.get('grade_9'),
                    'psa_10': v.get('psa_10'),
                    'url': v.get('url', ''),
                    'card_set': v.get('card_set', ''),
                    'set_text': v.get('set_text', ''),
                    'raw_title': v.get('raw_title', ''),
                    'is_rc': v.get('is_rc', False),
                    'is_auto': v.get('is_auto', False),
                    'print_run': v.get('print_run'),
                })
            row = SCPCache(
                player_name=_pn,
                card_year=card_year,
                card_number=_cn,
                search_query=queries[0],
                variants=cache_data,
            )
            db.add(row)
            db.commit()
    except Exception as e:
        db.rollback()
        log.warn(f'SCP cache write failed: {e}', category='scp_cache')

    return [v for v in all_matches if v.get('ungraded')], False  # False = Selenium lookup


def find_scp_match_via_selenium(scp_scraper, db, player_name: str, card_year: int,
                                card_set: str, card_number: str, parallel: str,
                                ebay_title: str = '', ebay_aspects: dict = None) -> dict:
    """Search SCP for a card, then match the eBay listing to the right variant.
    
    Strategy:
    1. Get all SCP variants (cache or Selenium)
    2. Pass 1: exact parallel match
    3. Pass 2: text search eBay title for SCP parallel names
    4. Pass 3: narrow by signals (RC, Auto, print run), pick best guess + flag
    
    Returns: (result_dict_or_None, was_cached, diagnostics_dict)
    """
    diag = {'variants_found': 0, 'variant_names': [], 'pass1_tried': None,
            'pass2_searched': None, 'pass3_signals': None, 'fail_reason': None}

    if not card_number:
        diag['fail_reason'] = 'no_card_number'
        return None, False, diag

    if ebay_aspects is None:
        ebay_aspects = {}

    priced, was_cached = _get_scp_variants(scp_scraper, db, player_name, card_year, card_set, card_number)
    if not priced:
        diag['fail_reason'] = 'no_scp_variants'
        return None, was_cached, diag

    diag['variants_found'] = len(priced)
    diag['variant_names'] = [f"{v.get('parallel','Base')} (${v.get('ungraded','?')})" for v in priced[:10]]

    # Build combined text from eBay listing for parallel detection
    search_text = ebay_title or ''
    if ebay_aspects:
        for key in ['Parallel/Variety', 'Parallel', 'Variety', 'Features']:
            if key in ebay_aspects and ebay_aspects[key]:
                search_text += ' ' + str(ebay_aspects[key])

    # Pass 1: exact parallel match from what we already extracted
    parallel_lower = (parallel or 'base').lower()
    diag['pass1_tried'] = parallel_lower
    for card in priced:
        card_parallel = (card.get('parallel') or 'Base').lower()
        if card_parallel == parallel_lower:
            return _build_scp_result(card, card_set, 'exact'), was_cached, diag

    # Pass 2: search eBay title/aspects for any SCP parallel name
    diag['pass2_searched'] = search_text[:120]
    variant_match = _find_parallel_in_text(search_text, priced)
    if variant_match:
        return _build_scp_result(variant_match, card_set, 'text_match'), was_cached, diag

    # Pass 3: narrow by signals (RC, Auto, print run)
    ebay_signals = _extract_ebay_signals(ebay_title, ebay_aspects)
    diag['pass3_signals'] = ebay_signals
    signal_match = _match_by_signals(priced, ebay_signals)
    if signal_match:
        return _build_scp_result(signal_match, card_set, 'signal_match', flagged=True), was_cached, diag

    diag['fail_reason'] = f'all_passes_failed ({len(priced)} variants available)'
    return None, was_cached, diag


def find_sold_comps_fallback(db, player_name: str, card_year: int,
                            card_number: str, parallel: str) -> dict:
    """Check sold_comps DB cache (from 130point worm) for pricing data.

    Returns dict compatible with SCP result format, or None.
    Requires MIN_SOLD_COMPS recent comps to trust the price.
    """
    import statistics
    from backend.models import SoldComp
    from sqlalchemy import func
    from datetime import datetime, timedelta

    if not card_number:
        return None

    cutoff = datetime.now() - timedelta(hours=72)
    comps = db.query(SoldComp).filter(
        func.lower(SoldComp.player_name) == player_name.lower(),
        SoldComp.card_year == card_year,
        func.lower(SoldComp.card_number) == card_number.lower(),
        SoldComp.created_at > cutoff,
    ).all()

    if len(comps) < MIN_SOLD_COMPS:
        return None

    prices = sorted([float(c.sale_price) for c in comps])

    # Trim outliers if enough data
    if len(prices) >= 5:
        trim = max(1, len(prices) // 5)
        prices = prices[trim:-trim]

    if not prices:
        return None

    median_price = statistics.median(prices)

    return {
        'scp_price': median_price,
        'grade_9': None,
        'psa_10': None,
        'scp_url': None,
        'card_set': None,
        'matched_parallel': parallel or 'Base',
        'match_type': 'sold_comps',
        'flagged': True,
        'source': 'sold_comps',
        'volume': f'{len(comps)} sold comps',
    }


def find_ebay_comps_fallback(scraper, player_name: str, card_year: int,
                             card_set: str, card_number: str, parallel: str,
                             ebay_title: str = '') -> dict:
    """Fallback pricing via eBay active BIN comps when SCP has no match.

    Builds a targeted query, fetches BIN listings, filters for relevance,
    and returns median price if >= MIN_COMPS results found.

    Returns dict compatible with SCP result format, or None.
    """
    import statistics

    # Build query: player + year + parallel + card number
    parts = [player_name]
    if card_year:
        parts.append(str(card_year))
    if card_set and card_set.lower() not in ('unknown', 'base'):
        parts.append(card_set)
    if parallel and parallel.lower() not in ('base', 'numbered'):
        parts.append(parallel)
    if card_number:
        parts.append(f'#{card_number}')
    query = ' '.join(parts)

    results = scraper.search_active_bin_comps(query)
    if not results:
        return None

    # Filter: only ungraded comps (don't compare raw auction to graded BIN)
    ungraded = [r for r in results if r.get('condition') != 'Graded']
    if len(ungraded) < MIN_COMPS:
        return None

    prices = sorted([r['price'] for r in ungraded])

    # Trim outliers: drop top and bottom 20% if enough data
    if len(prices) >= 5:
        trim = max(1, len(prices) // 5)
        prices = prices[trim:-trim]

    if not prices:
        return None

    median_price = statistics.median(prices)

    return {
        'scp_price': median_price,
        'grade_9': None,
        'psa_10': None,
        'scp_url': None,
        'card_set': card_set,
        'matched_parallel': parallel or 'Base',
        'match_type': 'ebay_comps',
        'flagged': True,  # Always flag -- lower confidence than SCP
        'source': 'ebay_comps',
        'volume': f'{len(ungraded)} active BIN comps',
        'comp_prices': prices,
    }


def _build_scp_result(card: dict, fallback_set: str, match_type: str, flagged: bool = False) -> dict:
    """Build standardized SCP result dict."""
    return {
        'scp_price': card['ungraded'],
        'grade_9': card.get('grade_9'),
        'psa_10': card.get('psa_10'),
        'scp_url': card.get('url'),
        'card_set': card.get('card_set') or fallback_set,
        'matched_parallel': card.get('parallel', 'Base'),
        'match_type': match_type,
        'flagged': flagged,
        'source': 'selenium',
        'volume': card.get('volume', ''),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='eBay-First Auction Opportunity Pipeline')
    parser.add_argument('--hours', type=int, default=48, help='Auctions ending within X hours (default: 48)')
    parser.add_argument('--min-profit', type=float, default=10, help='Min profit after all costs (default: $10)')
    parser.add_argument('--max-budget', type=float, default=200, help='Max current bid + shipping (default: $200)')
    parser.add_argument('--years', type=str, default='2023,2024,2025,2026', help='Years to search (default: 2023,2024,2025,2026)')
    parser.add_argument('--sport', type=str, default='baseball', help='Sport to search (default: baseball)')
    parser.add_argument('--dry-run', action='store_true', help='Show results without storing in DB')
    parser.add_argument(
        '--top-players',
        type=int,
        default=100,
        help='Hot player count for player queries (default: 100; match BIN local default)',
    )
    parser.add_argument('--days', type=int, default=7, help='eBay volume lookback for player discovery (default: 7, same as BIN)')
    parser.add_argument('--players', type=str, default=None, help='Comma-separated names; skips eBay discovery for the player-query arm')
    parser.add_argument(
        '--dynamic-seed-limit',
        type=int,
        default=50,
        help='Merge top N (player,sport) from recent DB sales into discovery (0=off; default: 50)',
    )
    parser.add_argument(
        '--dynamic-seed-days',
        type=int,
        default=30,
        help='Lookback days when ranking players from sales table (default: 30)',
    )
    parser.add_argument(
        '--max-discovery-candidates',
        type=int,
        default=100,
        help='Max Browse discovery calls before ranking (default: 100)',
    )
    parser.add_argument(
        '--no-dynamic-seeds',
        action='store_true',
        help='Anchor SEED_PLAYERS only (no sales-driven candidate merge)',
    )
    parser.add_argument(
        '--no-product-line-queries',
        action='store_true',
        help='Skip high-volume product-line strings (e.g. "2025 Topps Chrome baseball")',
    )
    parser.add_argument(
        '--product-line-year-cap',
        type=int,
        default=3,
        help='Use latest N years from --years for product-line expansion (0 = all years)',
    )
    parser.add_argument(
        '--sold-comp-seed-queries',
        type=int,
        default=25,
        help='Extra Browse q strings from recent sold_comps (130point); 0 disables',
    )
    parser.add_argument(
        '--sold-comp-seed-days',
        type=int,
        default=7,
        help='Lookback days when ranking sold_comp SKUs for seed queries',
    )
    parser.add_argument(
        '--player-rank-source',
        type=str,
        choices=('browse', 'sold_comps', 'sales'),
        default='browse',
        help='browse=eBay totals (default). sales=sales table counts per player. sold_comps=130point rows',
    )
    parser.add_argument(
        '--sales-rank-days',
        type=int,
        default=7,
        help='Lookback days on sales.sale_date when --player-rank-source sales',
    )
    parser.add_argument(
        '--sales-rank-fallback-browse',
        action='store_true',
        help='If sales ranking returns empty, fall back to Browse',
    )
    parser.add_argument(
        '--sold-comps-rank-days',
        type=int,
        default=30,
        help='Lookback days on sold_comps.created_at when --player-rank-source sold_comps',
    )
    parser.add_argument(
        '--no-sold-comps-fallback-browse',
        action='store_true',
        help='If sold_comps ranking returns empty, continue with empty list (auction may use DB fallback)',
    )
    args = parser.parse_args()

    dyn_limit = 0 if args.no_dynamic_seeds else max(0, args.dynamic_seed_limit)

    years = [int(y.strip()) for y in args.years.split(',')]

    from backend.config.auction_queries import BASEBALL_VALUE_QUERIES_CORE, build_baseball_value_queries

    sport_lc = (args.sport or 'baseball').strip().lower()
    if sport_lc == 'baseball':
        cap = None if args.product_line_year_cap == 0 else args.product_line_year_cap
        VALUE_QUERIES, value_query_meta = build_baseball_value_queries(
            years,
            include_product_lines=not args.no_product_line_queries,
            product_line_year_cap=cap,
        )
    else:
        VALUE_QUERIES = list(BASEBALL_VALUE_QUERIES_CORE)
        value_query_meta = {
            'product_lines': False,
            'note': f'sport={sport_lc!r}: product-line pack is baseball-only; using core parallel queries',
            'parallel_queries': len(VALUE_QUERIES),
            'total_value_queries': len(VALUE_QUERIES),
        }

    sold_seed_queries: list = []
    if args.sold_comp_seed_queries > 0:
        from backend.services.auction_sold_comp_seeds import sold_comp_search_seeds

        with closing(SessionLocal()) as db_seed:
            sold_seed_queries = sold_comp_search_seeds(
                db_seed,
                days=args.sold_comp_seed_days,
                limit=args.sold_comp_seed_queries,
                sport_token=args.sport,
            )
        if sold_seed_queries:
            print(
                f"Sold-comp seed queries: {len(sold_seed_queries)} "
                f"(top SKUs by 130point rows, last {args.sold_comp_seed_days}d)"
            )

    # Player-specific searches: same ranked list as BIN (eBay volume), not DB card counts
    from backend.config.sets import HIGH_VALUE_SETS, get_set_queries
    from contextlib import closing
    from backend.discover_players import hot_player_names_for_pipeline

    sport_key = (args.sport or 'baseball').strip().title()
    PLAYER_QUERIES = []
    if args.players:
        player_names = [p.strip() for p in args.players.split(',') if p.strip()]
        print(f"Using --players ({len(player_names)} names); skipping eBay discovery for player queries.")
    else:
        print(
            f"Finding hot players (rank={args.player_rank_source}; "
            f"BIN parity days={args.days}, limit={args.top_players})..."
        )
        with closing(SessionLocal()) as _db:
            player_names = hot_player_names_for_pipeline(
                limit=args.top_players,
                sport=sport_key,
                days=args.days,
                db_session=_db,
                dynamic_sales_player_limit=dyn_limit,
                dynamic_sales_lookback_days=args.dynamic_seed_days,
                max_discovery_candidates=args.max_discovery_candidates,
                rank_source=args.player_rank_source,
                sales_rank_lookback_days=args.sales_rank_days,
                sales_rank_fallback_browse=bool(args.sales_rank_fallback_browse),
                sold_comps_lookback_days=args.sold_comps_rank_days,
                sold_comps_fallback_browse=not args.no_sold_comps_fallback_browse,
            )
        if not player_names:
            print(
                "WARNING: discover_top_players returned no players; "
                "falling back to DB Card.name counts (no BIN parity)."
            )
            with closing(SessionLocal()) as db_temp:
                rows = (
                    db_temp.query(Card.player_name, func.count(Card.id).label('cnt'))
                    .group_by(Card.player_name)
                    .order_by(func.count(Card.id).desc())
                    .limit(args.top_players)
                    .all()
                )
            player_names = [r[0] for r in rows]

    for idx, name in enumerate(player_names):
        PLAYER_QUERIES.append(f"{name} auto numbered")
        PLAYER_QUERIES.append(f"{name} refractor")
        if sport_key in HIGH_VALUE_SETS and idx < 15:
            PLAYER_QUERIES.extend(get_set_queries(name, sport_key))

    queries = VALUE_QUERIES + sold_seed_queries + PLAYER_QUERIES

    print("=" * 80)
    print("EBAY-FIRST AUCTION OPPORTUNITY PIPELINE")
    print("=" * 80)
    print(f"\nAuctions ending within: {args.hours}h")
    print(f"Budget: ${args.max_budget:.0f} max | Min Profit: ${args.min_profit:.0f}")
    print(f"Sport: {args.sport} | dynamic_seed_limit={dyn_limit} | dynamic_seed_days={args.dynamic_seed_days}")
    print(
        f"Search queries: {len(queries)} "
        f"({len(VALUE_QUERIES)} value + {len(sold_seed_queries)} sold-seed + {len(PLAYER_QUERIES)} player)"
    )
    if value_query_meta.get('product_lines'):
        print(
            f"  Product-line years: {value_query_meta.get('product_line_years_used')} "
            f"(cap={args.product_line_year_cap or 'all'})"
        )

    known_players = load_known_players(years=years, sport=args.sport.lower())
    print(f"Known players: {len(known_players)} (MLB rosters + DB)")
    print()

    tracker = JobTracker('auction_finder')
    tracker.start(
        total=len(queries),
        parameters={
            'hours': args.hours, 'min_profit': args.min_profit,
            'max_budget': args.max_budget, 'sport': args.sport,
            'years': years, 'query_count': len(queries),
            'top_players': args.top_players, 'discovery_days': args.days,
            'players_override': bool(args.players),
            'value_query_meta': value_query_meta,
            'sold_comp_seed_queries': len(sold_seed_queries),
        }
    )

    try:
        # Step 1: Search eBay for auctions ending soon
        print("Step 1: Searching eBay for auctions ending soon...")
        print("-" * 60)

        scraper = EbayScraper()
        all_auctions = []
        seen_ids = set()
        step1_query_stats: list = []

        for i, query in enumerate(queries, 1):
            print(f"\n[{i}/{len(queries)}] \"{query}\"")
            # Paginate to get all results, not just first 200
            offset = 0
            query_total = 0
            query_new = 0
            pages = 0
            ebay_total_hint = None
            while True:
                page_meta: dict = {}
                auctions = scraper.search_auctions_ending_soon(
                    query, hours=args.hours, offset=offset, meta_out=page_meta,
                )
                if offset == 0 and page_meta.get('ebay_total') is not None:
                    ebay_total_hint = page_meta.get('ebay_total')
                pages += 1  # one Browse search GET per iteration
                if not auctions:
                    break
                for a in auctions:
                    item_id = a.get('ebay_item_id', '')
                    if item_id not in seen_ids:
                        seen_ids.add(item_id)
                        all_auctions.append(a)
                        query_new += 1
                query_total += len(auctions)
                if len(auctions) < 200:
                    break  # Last page
                offset += 200
                if offset >= 1000:  # Safety cap: 5 pages max per query
                    break
            hint = (
                f" | eBay total≈{ebay_total_hint} (first page; we fetch ≤1000)"
                if ebay_total_hint is not None
                else ''
            )
            print(f"  {query_total} rows, {query_new} new after dedupe{hint}")
            step1_query_stats.append({
                'query': query[:200],
                'pages': pages,
                'items_returned': query_total,
                'new_after_dedupe': query_new,
                'ebay_total_hint': ebay_total_hint,
            })
            tracker.update(processed=i)
            time.sleep(1.0)  # reduce Browse API burst 429s between queries

        print(f"\nTotal unique auctions: {len(all_auctions)}")

        # Step 2: Quality filter
        print(f"\nStep 2: Quality filtering...")
        print("-" * 60)

        tracker.update(processed=len(queries), total=len(queries) + len(all_auctions))

        qualified = []
        skip_reasons = {'no_card_number': 0, 'junk': 0,
                        'no_year': 0, 'no_player': 0, 'over_budget': 0,
                        'not_auction': 0}
        detail_lookups = 0
        cn_cache = {}
        step2_skip_vision_queue: list = []
        step2_vision_counts: dict = {'no_year': 0, 'no_card_number': 0, 'no_player': 0}

        with closing(SessionLocal()) as db_step2:
            for auction_idx, auction in enumerate(all_auctions, 1):
                if auction_idx % 50 == 0 or auction_idx == 1:
                    print(f"  [{auction_idx}/{len(all_auctions)}] filtering... ({len(qualified)} qualified so far)", flush=True)

                title = auction['title']
                aspects = auction.get('aspects', {})
                price = auction['price']
                shipping = auction.get('shipping', DEFAULT_SHIPPING)

                # Skip pure BIN listings that snuck through
                if auction.get('listing_type') not in ('auction', 'auction_bin'):
                    skip_reasons['not_auction'] += 1
                    continue

                if is_junk(title):
                    skip_reasons['junk'] += 1
                    continue

                total_cost = price + shipping
                if total_cost > args.max_budget:
                    skip_reasons['over_budget'] += 1
                    continue

                short_desc = auction.get('short_description') or ''
                year = extract_year(title, aspects, short_desc)
                merged_aspects = dict(aspects)
                candidates = gather_card_number_candidates(title, merged_aspects, short_desc)
                player_name = extract_player_name(title, aspects, known_players)
                card_number = pick_card_number_with_catalog(
                    candidates, db_step2, player_name, year, args.sport.lower(), cn_cache
                )

                # Missing card #, player, or year → full item details (same Browse GET)
                item_id = auction.get('ebay_item_id')
                if item_id and (not card_number or not player_name or not year):
                    details = scraper.get_full_item_details(item_id)
                    if details:
                        detail_lookups += 1
                        if detail_lookups % 25 == 0:
                            print(f"    ({detail_lookups} detail lookups so far...)", flush=True)
                        merged_aspects = dict(aspects)
                        if details.get('card_number'):
                            merged_aspects['Card Number'] = (
                                merged_aspects.get('Card Number') or details['card_number']
                            )
                        if details.get('card_year'):
                            merged_aspects['Year'] = str(details['card_year'])
                            year = year or details['card_year']
                        if not year:
                            year = extract_year(title, merged_aspects, short_desc)
                        if not player_name:
                            # Accept eBay's Player aspect directly -- covers retired players,
                            # minor leaguers, anyone not in MLB API
                            detail_player = details.get('player_name')
                            if detail_player:
                                player_name = detail_player
                            else:
                                # Last resort: try matching detail dict against known players
                                detail_aspects = details or {}
                                for key in ['Player', 'Player/Athlete', 'Athlete']:
                                    val = detail_aspects.get(key)
                                    if val:
                                        player_name = val
                                        break
                        candidates = gather_card_number_candidates(
                            title, merged_aspects, short_desc
                        )
                        card_number = pick_card_number_with_catalog(
                            candidates, db_step2, player_name, year, args.sport.lower(), cn_cache
                        ) or card_number
                        # Also grab card set and parallel from aspects if missing
                        if not aspects.get('Set') and details.get('card_set'):
                            aspects['Set'] = details['card_set']
                        if details.get('parallel') and details['parallel'] != 'Base':
                            aspects['_detail_parallel'] = details['parallel']

                        # Merge extra gallery URLs from GET /item (additionalImages, etc.)
                        _merge_auction_gallery_from_item_details(auction, details)

                if not year and player_name and card_number:
                    year = infer_year_if_unique_in_catalog(
                        db_step2, player_name, card_number, args.sport.lower()
                    )
                    if not year:
                        set_hint = (
                            aspects.get('Set')
                            or auction.get('card_info', {}).get('card_set')
                            or ''
                        )
                        year = resolve_year_from_set_hint(
                            db_step2,
                            player_name,
                            card_number,
                            args.sport.lower(),
                            set_hint,
                        )

                if not year:
                    skip_reasons['no_year'] += 1
                    if skip_reasons['no_year'] <= 10:
                        log.info(f"no_year: {title[:80]}", category='skip_debug')
                    _append_step2_vision_sample(
                        auction,
                        title,
                        'no_year',
                        step2_skip_vision_queue,
                        step2_vision_counts,
                        STEP2_VISION_CAP_PER_REASON,
                    )
                    continue

                if not card_number:
                    skip_reasons['no_card_number'] += 1
                    if skip_reasons['no_card_number'] <= 10:
                        log.info(f"no_card_number: {title[:80]}", category='skip_debug')
                    _append_step2_vision_sample(
                        auction,
                        title,
                        'no_card_number',
                        step2_skip_vision_queue,
                        step2_vision_counts,
                        STEP2_VISION_CAP_PER_REASON,
                    )
                    continue

                if not player_name:
                    skip_reasons['no_player'] += 1
                    if skip_reasons['no_player'] <= 10:
                        log.info(f"no_player: {title[:80]}", category='skip_debug')
                    _append_step2_vision_sample(
                        auction,
                        title,
                        'no_player',
                        step2_skip_vision_queue,
                        step2_vision_counts,
                        STEP2_VISION_CAP_PER_REASON,
                    )
                    continue

                # Extract card details for SCP lookup
                card_info = auction.get('card_info', {})
                parallel = aspects.get('_detail_parallel') or card_info.get('parallel', 'Base')
                # Strip brackets if eBay aspects returned "[Base]" literally
                if parallel.startswith('[') and parallel.endswith(']'):
                    parallel = parallel[1:-1]
                card_set = card_info.get('card_set', aspects.get('Set', ''))

                auction['_player'] = player_name
                auction['_year'] = year
                auction['_card_number'] = card_number
                auction['_parallel'] = parallel
                auction['_card_set'] = card_set
                qualified.append(auction)

                if auction_idx % 100 == 0:
                    tracker.update(processed=len(queries) + auction_idx)


        print(f"Qualified: {len(qualified)}")
        if detail_lookups:
            print(f"  eBay detail lookups: {detail_lookups} (for missing card#/player/year)")
        for reason, count in skip_reasons.items():
            if count:
                print(f"  Skipped ({reason}): {count}")

        if not qualified:
            print("\nNo qualified auctions found.")
            vpp_early = list(step2_skip_vision_queue)
            if vpp_early:
                print(
                    f"Step 2 vision follow-up sample: {len(vpp_early)} listing(s) "
                    f"(metadata skips with images → vision_post_pipeline_queue_sample)"
                )
            tracker.complete(summary={
                'auctions_searched': len(all_auctions),
                'step1_query_stats': step1_query_stats,
                'value_query_meta': value_query_meta,
                'sold_comp_seed_query_count': len(sold_seed_queries),
                'qualified': 0,
                'opportunities_found': 0,
                'step2_skip_reasons': skip_reasons,
                'detail_lookups': detail_lookups,
                'step2_skip_vision_queue_sample': step2_skip_vision_queue,
                'vision_post_pipeline_queue_sample': vpp_early,
                'step3_no_pricing': 0,
                'step3_no_pricing_after_primary': 0,
                'step3_no_pricing_after_sold_comps': 0,
            })
            exit()

        # Step 3: SCP validation (DB first, Selenium fallback)
        print(f"\nStep 3: SCP validation ({len(qualified)} cards)...")
        print("-" * 60)

        step3_base = len(queries) + len(all_auctions)
        tracker.update(processed=step3_base, total=step3_base + len(qualified))

        db = SessionLocal()
        scp_scraper = None  # Lazy init -- only if we need Selenium
        opportunities = []
        db_hits = 0
        selenium_hits = 0
        cache_hits = 0
        ebay_comp_hits = 0
        sold_comp_hits = 0
        no_scp = 0  # legacy aggregate for console line
        step3_no_pricing = 0
        step3_no_pricing_after_primary = 0
        step3_no_pricing_after_sold_comps = 0
        step3_bin_sanity = 0
        step3_low_volume = 0
        step3_below_min_profit = 0
        no_scp_vision_queue: list = []
        _max_no_scp_vision = 40
        bin_sanity_vision_queue: list = []
        _max_bin_sanity_vision = 40

        for i, auction in enumerate(qualified, 1):
            diag = {}
            player = auction['_player']
            year = auction['_year']
            card_number = auction['_card_number']
            parallel = auction['_parallel']
            card_set = auction['_card_set']
            title = auction['title']
            price = auction['price']
            shipping = auction.get('shipping', DEFAULT_SHIPPING)
            total_cost = price + shipping

            label = f"{player} {year} {card_set} #{card_number} [{parallel}]"

            # DB lookup first
            scp = find_scp_match_in_db(db, player, year, card_number, parallel, card_set)
            if scp:
                db_hits += 1
            else:
                # SCP lookup: cache first, Selenium fallback
                if scp_scraper is None:
                    print("  Starting Selenium for SCP lookups...")
                    try:
                        scp_scraper = SportsCardsProScraper(headless=True)
                        scp_scraper._init_driver()
                    except Exception as e:
                        print(f"  WARNING: Selenium failed to start: {e}")
                        print("  Will use SCP cache only.")
                        scp_scraper = False  # Sentinel: tried and failed

                try:
                    scp, was_cached, diag = find_scp_match_via_selenium(
                        scp_scraper if scp_scraper is not False else None,
                        db, player, year, card_set, card_number, parallel,
                        ebay_title=title, ebay_aspects=auction.get('aspects', {}))
                except Exception as e:
                    log.warn(f'SCP lookup failed: {e}', category='scp_selenium_error')
                    scp = None
                    was_cached = False
                    diag = {'fail_reason': f'exception: {e}'}
                if scp:
                    if was_cached:
                        cache_hits += 1
                    else:
                        selenium_hits += 1
                if not was_cached and scp_scraper and scp_scraper is not False:
                    time.sleep(3)  # Only sleep after Selenium calls, not cache hits

            if not scp or not scp.get('scp_price'):
                step3_no_pricing_after_primary += 1
                # Fallback 1: 130point sold comps (DB cache, instant)
                scp = find_sold_comps_fallback(db, player, year, card_number, parallel)
                if scp and scp.get('scp_price'):
                    sold_comp_hits += 1
                    if i <= 30 or i % 50 == 0:
                        print(f"  [{i}/{len(qualified)}] {label} -- 130point: ${scp['scp_price']:.2f} ({scp.get('volume', '?')})")

                # Fallback 2: eBay active BIN comps (1 API call)
                if not scp or not scp.get('scp_price'):
                    step3_no_pricing_after_sold_comps += 1
                    scp = find_ebay_comps_fallback(
                        scraper, player, year, card_set, card_number, parallel,
                        ebay_title=title)
                    if scp and scp.get('source') == 'ebay_comps':
                        ebay_comp_hits += 1
                        if i <= 30 or i % 50 == 0:
                            prices = scp.get('comp_prices', [])
                            print(
                                f"  [{i}/{len(qualified)}] {label} -- eBay comps: "
                                f"${scp['scp_price']:.2f} (median of {len(prices)} BINs)"
                            )

                if not scp or not scp.get('scp_price'):
                    no_scp += 1
                    step3_no_pricing += 1
                    if len(no_scp_vision_queue) < _max_no_scp_vision:
                        vu = list(auction.get('image_urls') or [])
                        if auction.get('image_url') and auction['image_url'] not in vu:
                            vu.insert(0, auction['image_url'])
                        no_scp_vision_queue.append({
                            'ebay_item_id': auction.get('ebay_item_id'),
                            'title': title[:240],
                            'image_urls': vu[:15],
                            'listing_type': 'auction',
                            'buy_price': float(price),
                            'shipping': float(shipping),
                        })
                    if i <= 20 or i % 50 == 0:
                        print(f"  [{i}/{len(qualified)}] {label} -- no pricing (SCP + 130point + eBay comps exhausted)")
                    if diag and no_scp <= 30:
                        reason = diag.get('fail_reason', 'unknown')
                        variants = diag.get('variants_found', 0)
                        if variants > 0:
                            names = diag.get('variant_names', [])
                            p1 = diag.get('pass1_tried', '?')
                            print(f"    LOST: {variants} SCP variants exist: {', '.join(names[:5])}")
                            print(f"    Pass1 tried: '{p1}' | Pass2 searched: {(diag.get('pass2_searched') or '')[:80]}")
                            sigs = diag.get('pass3_signals', {})
                            if sigs:
                                print(
                                    f"    Pass3 signals: RC={sigs.get('is_rc')} Auto={sigs.get('is_auto')} "
                                    f"Relic={sigs.get('is_relic')} PR={sigs.get('print_run')}"
                                )
                            print(f"    eBay title: {title[:100]}")
                        else:
                            print(f"    LOST: {reason}")
                    if i % 25 == 0:
                        tracker.update(processed=step3_base + i)
                    continue

            scp_price = scp['scp_price']

            # Graded listing detection
            GRADED_PATTERNS = ['psa ', 'bgs ', 'sgc ', 'cgc ', 'fcgs ', 'gem mint',
                               'mint 10', 'mint 9', ' graded ', 'psa10', 'psa 10',
                               'bgs 10', 'sgc 10', 'cgc 10', 'grade 10', 'grade 9']
            if any(gp in title.lower() for gp in GRADED_PATTERNS):
                step3_below_min_profit += 1
                continue

            # Conservative variant pricing: find cheapest keyword-matching SCP variant
            # and use 2.0x ratio check (same as BIN pipeline)
            try:
                import json as _jmod2
                from sqlalchemy import text as _text2
                _auc_scp_rows = db.execute(_text2(
                    "SELECT variants FROM scp_cache "
                    "WHERE player_name ILIKE :p AND card_year = :y AND card_number ILIKE :n"
                ), {"p": player, "y": year, "n": card_number}).fetchall()
                _auc_all_v = []
                for _asr in _auc_scp_rows:
                    _avlist = _asr[0]
                    if isinstance(_avlist, str): _avlist = _jmod2.loads(_avlist)
                    if isinstance(_avlist, list):
                        for _avv in _avlist:
                            _avp = _avv.get('ungraded') or 0
                            if _avp and float(_avp) > 0:
                                _apar = _avv.get('parallel', 'Base')
                                _akws = [w.lower() for w in __import__('re').split(r'[^a-zA-Z0-9]+', _apar) if len(w) >= 3]
                                _auc_all_v.append({'parallel': _apar, 'price': float(_avp), 'keywords': _akws})
                if len(_auc_all_v) >= 2:
                    _tl = title.lower()
                    _auc_matches = [v for v in _auc_all_v if v['parallel'] != 'Base' and v['keywords'] and any(kw in _tl for kw in v['keywords'])]
                    if _auc_matches:
                        _auc_cheapest = min(_auc_matches, key=lambda v: v['price'])
                        scp_price = _auc_cheapest['price']
                    _auc_closest = min(_auc_all_v, key=lambda v: abs(v['price'] - price))
                    _auc_pvc = scp_price / max(_auc_closest['price'], 1)
                    if _auc_pvc > 2.0:
                        step3_below_min_profit += 1
                        continue
            except Exception:
                pass

            # Sanity check: if listing has a BIN price and it's way below SCP,
            # the SCP match is probably wrong. Seller knows what the card is worth.
            bin_price = auction.get('bin_price')
            if bin_price and scp_price > 0:
                bin_ratio = bin_price / scp_price
                if bin_ratio < 0.50:
                    if i <= 30 or i % 50 == 0:
                        print(f"  [{i}/{len(qualified)}] {label} -- BIN ${bin_price:.2f} is {bin_ratio:.0%} of SCP ${scp_price:.2f} (seller disagrees)")
                    if len(bin_sanity_vision_queue) < _max_bin_sanity_vision:
                        vu = list(auction.get("image_urls") or [])
                        if auction.get("image_url") and auction["image_url"] not in vu:
                            vu.insert(0, auction["image_url"])
                        bin_sanity_vision_queue.append(
                            {
                                "reason": "auction_bin_tertiary_visual_vs_scp",
                                "pipeline_card": label,
                                "scp_price": float(scp_price),
                                "buy_price_or_bin": float(bin_price),
                                "bin_ratio": round(bin_ratio, 3),
                                "ebay_item_id": auction.get("ebay_item_id"),
                                "title": title[:240],
                                "image_urls": vu[:15],
                                "listing_type": "auction",
                                "buy_price": float(price),
                                "shipping": float(shipping),
                                "note": "Hybrid listing BIN << SCP — vision may confirm wrong SCP match vs cheap BIN",
                            }
                        )
                    no_scp += 1
                    step3_bin_sanity += 1
                    continue

            # Profit check: SCP * 0.87 - (bid + shipping) >= min_profit
            net_after_fees = scp_price * (1 - FEE_RATE)
            profit = net_after_fees - total_cost

            # Check volume -- skip dead cards
            volume = scp.get('volume', '')
            if volume and any(lv in volume.lower() for lv in LOW_VOLUME):
                step3_low_volume += 1
                if i <= 20 or i % 50 == 0:
                    print(f"  [{i}/{len(qualified)}] {label} -- low volume ({volume})")
                continue

            if profit < args.min_profit:
                step3_below_min_profit += 1
                if i <= 20 or i % 50 == 0:
                    print(f"  [{i}/{len(qualified)}] {label} -- ${profit:.2f} profit (below ${args.min_profit:.0f})")
                continue

            roi = (profit / total_cost) * 100

            # Calculate hours left
            hours_left = 0
            end_time = auction.get('end_time')
            if end_time:
                try:
                    if isinstance(end_time, str):
                        end_time_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                        # Convert to naive for comparison
                        end_time_dt = end_time_dt.replace(tzinfo=None)
                    else:
                        end_time_dt = end_time
                    delta = end_time_dt - datetime.now()
                    hours_left = max(0, round(delta.total_seconds() / 3600, 1))
                except Exception:
                    hours_left = 0
                    end_time_dt = None
            else:
                end_time_dt = None

            numeric_id = ''
            item_id = auction.get('ebay_item_id', '')
            if '|' in item_id:
                numeric_id = item_id.split('|')[1]
            else:
                numeric_id = item_id
            url = f"https://www.ebay.com/itm/{numeric_id}" if numeric_id else 'N/A'

            src_tag = 'DB' if scp.get('source') == 'database' else 'SCP'
            print(f"  [{i}/{len(qualified)}] [{src_tag}] {label}")
            print(f"    Bid: ${price:.2f} + ${shipping:.2f} ship = ${total_cost:.2f} | SCP: ${scp_price:.2f} | Profit: ${profit:.2f} ({roi:.0f}% ROI) | {hours_left:.0f}h left")
            print(f"    {url}")

            # Use the parallel SCP actually matched, not what we guessed
            matched_parallel = scp.get('matched_parallel', parallel)
            match_type = scp.get('match_type', 'unknown')
            is_flagged = scp.get('flagged', False) or match_type in ('base_fallback', 'lowest_fallback')

            if match_type not in ('exact', 'text_match'):
                print(f"    ** Flagged: match was '{match_type}' (SCP matched: {matched_parallel})")

            img_urls = list(auction.get('image_urls') or [])
            if auction.get('image_url') and auction['image_url'] not in img_urls:
                img_urls.insert(0, auction['image_url'])

            opportunities.append({
                'player_name': player,
                'card_year': year,
                'card_set': scp.get('card_set') or card_set,
                'card_number': card_number,
                'parallel': matched_parallel,
                'is_flagged': is_flagged,
                'scp_price': scp_price,
                'scp_grade_9': scp.get('grade_9'),
                'scp_psa_10': scp.get('psa_10'),
                'scp_url': scp.get('scp_url'),
                'scp_volume': scp.get('volume', ''),
                'buy_price': price,
                'shipping': shipping,
                'profit': profit,
                'roi': roi,
                'ebay_title': title,
                'ebay_url': url,
                'ebay_item_id': numeric_id,
                'image_url': auction.get('image_url'),
                'listing_image_urls': img_urls if img_urls else None,
                'bid_count': auction.get('bid_count', 0),
                'end_time': end_time_dt,
                'listing_type': 'auction',
                'match_type': match_type,
                'price_source': scp.get('source', 'scp'),
            })

        if scp_scraper:
            scp_scraper.close()

        print(f"\nSCP lookups: {db_hits} DB, {cache_hits} cache, {selenium_hits} Selenium, {sold_comp_hits} 130point, {ebay_comp_hits} eBay comps, {no_scp} no match")
        print(
            f"Step 3 drops: no_pricing(final)={step3_no_pricing} "
            f"(no_price_after_primary={step3_no_pricing_after_primary}, "
            f"after_sold_comps={step3_no_pricing_after_sold_comps}), "
            f"bin_sanity={step3_bin_sanity}, low_volume={step3_low_volume}, "
            f"below_min_profit=${args.min_profit}: {step3_below_min_profit}"
        )

        # Summary
        print("\n" + "=" * 80)
        print(f"RESULTS: {len(opportunities)} auction opportunities found")
        vision_post_pipeline_queue_sample: list = []
        vision_post_pipeline_queue_sample.extend(step2_skip_vision_queue)
        for row in no_scp_vision_queue:
            vision_post_pipeline_queue_sample.append(
                {
                    **row,
                    "reason": "auction_no_pricing_after_fallbacks",
                }
            )
        vision_post_pipeline_queue_sample.extend(bin_sanity_vision_queue)
        if vision_post_pipeline_queue_sample:
            n2 = len(step2_skip_vision_queue)
            tail = len(vision_post_pipeline_queue_sample) - n2
            print(
                f"Vision follow-up sample: {len(vision_post_pipeline_queue_sample)} listing(s) "
                f"(Step 2 metadata w/ images: {n2}; Step 3 queues: {tail} — "
                f"results_summary.vision_post_pipeline_queue_sample; does not gate ingest)"
            )
        print("=" * 80)

        if opportunities:
            opportunities.sort(key=lambda x: x['profit'], reverse=True)

            for i, opp in enumerate(opportunities[:30], 1):
                hrs = 0
                if opp.get('end_time'):
                    delta = opp['end_time'] - datetime.now()
                    hrs = max(0, round(delta.total_seconds() / 3600, 1))
                print(f"\n{i}. {opp['player_name']} {opp['card_year']} {opp['card_set']} #{opp['card_number']} [{opp['parallel']}]")
                print(f"   Bid: ${opp['buy_price']:.2f} + ${opp['shipping']:.2f} ship | SCP: ${opp['scp_price']:.2f} | Profit: ${opp['profit']:.2f} ({opp['roi']:.0f}% ROI)")
                print(f"   Bids: {opp['bid_count']} | Ends in: {hrs:.0f}h")
                print(f"   {opp['ebay_title'][:100]}")
                print(f"   {opp['ebay_url']}")

        # Step 4: Store in database
        if not args.dry_run and opportunities:
            print(f"\nStoring {len(opportunities)} auction opportunities...")
            try:
                # Only clear previous auction-pipeline results, not BIN results
                db.query(Opportunity).filter(
                    Opportunity.listing_type == 'auction',
                    Opportunity.scan_id.isnot(None)
                ).delete(synchronize_session=False)
                db.commit()

                for opp in opportunities:
                    row = Opportunity(
                        player_name=opp['player_name'],
                        card_year=opp['card_year'],
                        card_set=opp['card_set'],
                        card_number=opp['card_number'],
                        parallel=opp['parallel'],
                        scp_price=opp['scp_price'],
                        scp_grade_9=opp.get('scp_grade_9'),
                        scp_psa_10=opp.get('scp_psa_10'),
                        scp_url=opp.get('scp_url'),
                        scp_volume=opp.get('scp_volume'),
                        buy_price=opp['buy_price'],
                        shipping=opp['shipping'],
                        profit=opp['profit'],
                        roi=opp['roi'],
                        ebay_title=opp['ebay_title'],
                        ebay_url=opp['ebay_url'],
                        ebay_item_id=opp['ebay_item_id'],
                        image_url=opp.get('image_url'),
                        listing_image_urls=opp.get('listing_image_urls') or None,
                        bid_count=opp.get('bid_count', 0),
                        end_time=opp.get('end_time'),
                        listing_type='auction',
                        flagged=opp.get('is_flagged', False),
                        verification_status='pending',
                        verification_detail={'schema': 1, 'pipeline': 'auction'},
                        sport=sport_key,
                        price_source=opp.get('price_source', 'scp'),
                        scan_id=tracker.run_id,
                    )
                    db.add(row)

                db.commit()
                print(f"Stored {len(opportunities)} auction opportunities in database.")
            except Exception as e:
                db.rollback()
                log.error(f'Failed to store auction opportunities: {e}', category='db_write_error')
                print(f"DB error: {e}")
        elif args.dry_run:
            print("\n[DRY RUN] Skipping database storage.")

        db.close()

        # Always emit vision_* keys (possibly empty) so tools can tell current code from older
        # job_runs rows that omit vision_post_pipeline_queue_sample entirely.
        summary = {
            'auctions_searched': len(all_auctions),
            'step1_query_stats': step1_query_stats,
            'value_query_meta': value_query_meta,
            'sold_comp_seed_query_count': len(sold_seed_queries),
            'qualified': len(qualified),
            'step2_skip_reasons': skip_reasons,
            'detail_lookups': detail_lookups,
            'cache_hits': cache_hits,
            'db_hits': db_hits,
            'selenium_hits': selenium_hits,
            'ebay_comp_hits': ebay_comp_hits,
            'sold_comp_hits': sold_comp_hits,
            'no_scp_or_rejected': no_scp,
            'step3_no_pricing': step3_no_pricing,
            'step3_no_pricing_after_primary': step3_no_pricing_after_primary,
            'step3_no_pricing_after_sold_comps': step3_no_pricing_after_sold_comps,
            'step3_bin_sanity': step3_bin_sanity,
            'step3_low_volume': step3_low_volume,
            'step3_below_min_profit': step3_below_min_profit,
            'opportunities_found': len(opportunities),
            'no_scp_vision_queue_sample': no_scp_vision_queue,
            'step2_skip_vision_queue_sample': step2_skip_vision_queue,
            'vision_post_pipeline_queue_sample': vision_post_pipeline_queue_sample,
            'parameters': {
                'hours': args.hours,
                'min_profit': args.min_profit,
                'max_budget': args.max_budget,
                'sport': args.sport,
                'years': years,
                'value_query_meta': value_query_meta,
                'sold_comp_seed_queries': len(sold_seed_queries),
            },
        }
        log.info('Auction pipeline complete', context=summary)
        tracker.complete(summary=summary)

    except Exception as e:
        log.error(f'Auction pipeline failed: {e}', category='pipeline_crash')
        tracker.fail(str(e))
        raise
