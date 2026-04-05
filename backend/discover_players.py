"""
Volume-Based Player Discovery

Queries eBay Buy Browse (active listing ``total`` per seed) and ranks players.
Runs on every opportunity pipeline when ``--players`` is not set.

Operational visibility:
- Right before per-seed Browse calls, one **Analytics** line when available: ``BROWSE_APP_QUOTA {...}`` (app-level Buy/Browse **remaining** / **limit**).
- Every run prints one machine-readable line: ``DISCOVER_SUMMARY {...}`` (grep in CI logs; includes **ebay_quota_analytics**, **ebay_ratelimit_last** when present).
- Failures (zero players returned) persist one ``error_log`` row:
  ``category=discover_all_seeds_zero``, ``source=discover_players``.
- Per-seed HTTP/API issues persist as ``WARN`` rows (throttled so we do not insert 45 rows on total outage).

Usage:
    /usr/bin/python3 -m backend.discover_players
    /usr/bin/python3 -m backend.discover_players --limit 20 --days 7
"""

import json
import sys
import os
import time
from datetime import datetime
from typing import List, Dict, Optional, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.scrapers.ebay_scraper import EbayScraper
from backend.utils.logger import get_logger
from backend.utils.ebay_rate_limits import fetch_buy_browse_app_quota, parse_ratelimit_headers
import requests

log = get_logger('discover_players')

# Broad seed list - covers current stars, hot rookies, legends
# This list gets pruned by actual eBay volume data
SEED_PLAYERS = [
    # 2024-2025 Hot Rookies
    ("Paul Skenes", "Baseball"),
    ("Jackson Holliday", "Baseball"),
    ("Jackson Merrill", "Baseball"),
    ("Wyatt Langford", "Baseball"),
    ("Colton Cowser", "Baseball"),
    ("Junior Caminero", "Baseball"),
    ("Evan Carter", "Baseball"),
    ("Jasson Dominguez", "Baseball"),
    ("Jordan Walker", "Baseball"),
    ("Masyn Winn", "Baseball"),
    ("Dylan Crews", "Baseball"),
    ("James Wood", "Baseball"),
    ("Travis Bazzana", "Baseball"),
    ("Charlie Condon", "Baseball"),
    ("Jac Caglianone", "Baseball"),
    # Current Stars
    ("Shohei Ohtani", "Baseball"),
    ("Aaron Judge", "Baseball"),
    ("Bobby Witt Jr", "Baseball"),
    ("Elly De La Cruz", "Baseball"),
    ("Gunnar Henderson", "Baseball"),
    ("Ronald Acuna Jr", "Baseball"),
    ("Julio Rodriguez", "Baseball"),
    ("Corbin Carroll", "Baseball"),
    ("Mookie Betts", "Baseball"),
    ("Mike Trout", "Baseball"),
    ("Bryce Harper", "Baseball"),
    ("Juan Soto", "Baseball"),
    ("Fernando Tatis Jr", "Baseball"),
    ("Freddie Freeman", "Baseball"),
    ("Corey Seager", "Baseball"),
    ("Trea Turner", "Baseball"),
    ("Adley Rutschman", "Baseball"),
    ("Spencer Strider", "Baseball"),
    ("Yoshinobu Yamamoto", "Baseball"),
    ("Kodai Senga", "Baseball"),
    # Prospects
    ("Ethan Salas", "Baseball"),
    ("Roman Anthony", "Baseball"),
    ("Marcelo Mayer", "Baseball"),
    ("Jackson Chourio", "Baseball"),
    ("Roki Sasaki", "Baseball"),
    # Legends (always trade)
    ("Ken Griffey Jr", "Baseball"),
    ("Derek Jeter", "Baseball"),
    ("Ichiro Suzuki", "Baseball"),
    ("Cal Ripken Jr", "Baseball"),
    ("Nolan Ryan", "Baseball"),
    # Basketball
    ("Victor Wembanyama", "Basketball"),
    ("Luka Doncic", "Basketball"),
    ("Anthony Edwards", "Basketball"),
    ("Jayson Tatum", "Basketball"),
    ("Ja Morant", "Basketball"),
    ("LeBron James", "Basketball"),
    ("Stephen Curry", "Basketball"),
    ("Giannis Antetokounmpo", "Basketball"),
    ("Nikola Jokic", "Basketball"),
    ("Zach Edey", "Basketball"),
    ("Reed Sheppard", "Basketball"),
    ("Zaccharie Risacher", "Basketball"),
    ("Michael Jordan", "Basketball"),
    ("Kobe Bryant", "Basketball"),
    # Football
    ("Caleb Williams", "Football"),
    ("Jayden Daniels", "Football"),
    ("Drake Maye", "Football"),
    ("Marvin Harrison Jr", "Football"),
    ("Malik Nabers", "Football"),
    ("Brock Bowers", "Football"),
    ("Patrick Mahomes", "Football"),
    ("Josh Allen", "Football"),
    ("Lamar Jackson", "Football"),
    ("CJ Stroud", "Football"),
    ("Joe Burrow", "Football"),
    ("Travis Kelce", "Football"),
    ("Tom Brady", "Football"),
]


def _discover_429_backoff_seconds(attempt: int, retry_after_header: Optional[str]) -> float:
    """
    Decreasing backoff after HTTP 429: first wait longer, later waits shrink toward ~0.

    Default schedule (seconds): 25, 12, 6, 2, 0.5 — override with
    ``EBAY_DISCOVER_429_BACKOFF`` (comma-separated, e.g. ``30,15,8,3,1``).

    If eBay sends a **shorter** ``Retry-After``, we use ``min(schedule, Retry-After)``
    so we do not wait longer than eBay asks. We **never** wait longer than the
    schedule step (so Retry-After: 60 becomes 25 on the first retry, not 60).
    """
    raw = os.environ.get('EBAY_DISCOVER_429_BACKOFF', '25,12,6,2,0.5')
    parts = [p.strip() for p in raw.split(',') if p.strip()]
    try:
        schedule = [max(0.1, float(x)) for x in parts]
    except ValueError:
        schedule = [25.0, 12.0, 6.0, 2.0, 0.5]
    if not schedule:
        schedule = [25.0, 12.0, 6.0, 2.0, 0.5]
    base = schedule[attempt] if attempt < len(schedule) else schedule[-1]
    if retry_after_header:
        try:
            ra = float(retry_after_header)
            if ra > 0:
                return float(min(base, ra))
        except ValueError:
            pass
    return float(base)


def _browse_item_summary_get(
    scraper: EbayScraper,
    params: dict,
    *,
    timeout: int = 30,
    stats: Optional[Dict[str, Any]] = None,
) -> requests.Response:
    """
    GET ``/item_summary/search`` with 401 refresh and 429 ``Retry-After`` backoff.

    Discovery uses **decreasing** 429 backoff (see ``_discover_429_backoff_seconds``)
    instead of repeating a 60s ``Retry-After`` on every attempt.
    """
    last: Optional[requests.Response] = None
    for attempt in range(6):
        if attempt > 0:
            time.sleep(0.5)
        scraper.headers['Authorization'] = f'Bearer {scraper.token_manager.get_token()}'
        r = requests.get(
            f'{scraper.base_url}/item_summary/search',
            headers=scraper.headers,
            params=params,
            timeout=timeout,
        )
        last = r
        if stats is not None:
            h = parse_ratelimit_headers(r)
            if h:
                stats['ebay_ratelimit_last'] = {k: v for k, v in h.items() if k != 'source'}
                stats['ebay_ratelimit_last_source'] = 'response_headers'
        if r.status_code == 401:
            scraper.token_manager._refresh_token()
            scraper.headers['Authorization'] = f'Bearer {scraper.token_manager.get_token()}'
            r = requests.get(
                f'{scraper.base_url}/item_summary/search',
                headers=scraper.headers,
                params=params,
                timeout=timeout,
            )
            last = r
            if stats is not None:
                h = parse_ratelimit_headers(r)
                if h:
                    stats['ebay_ratelimit_last'] = {k: v for k, v in h.items() if k != 'source'}
                    stats['ebay_ratelimit_last_source'] = 'response_headers'

        if r.status_code == 429:
            if stats is not None:
                stats['browse_429_waits'] = stats.get('browse_429_waits', 0) + 1
            wait = _discover_429_backoff_seconds(attempt, r.headers.get('Retry-After'))
            if attempt < 5:
                print(
                    f"  eBay Browse 429 — sleeping {wait:g}s then retry ({attempt + 1}/5)...",
                    flush=True,
                )
                time.sleep(wait)
                continue
        return r
    assert last is not None
    return last


def _ebay_errors_summary(data: dict) -> Optional[List[Dict[str, Any]]]:
    raw = data.get('errors')
    if not raw:
        return None
    items = raw if isinstance(raw, list) else [raw]
    out: List[Dict[str, Any]] = []
    for e in items[:8]:
        if isinstance(e, dict):
            out.append({
                'errorId': e.get('errorId'),
                'domain': e.get('domain'),
                'severity': e.get('severity'),
                'message': str(e.get('message') or '')[:500],
            })
    return out or None


def discover_top_players(days: int = 7, limit: int = 20, max_queries: int = None, sport: str = None) -> List[Dict]:
    """
    Discover top players by eBay **active listing** volume (Browse search ``total``).

    ``days`` is kept for CLI compatibility; ranking uses current buyable inventory,
    not a past ``itemEndDate`` window (that filter yields 0 hits on active listings).
    
    Args:
        days: Lookback period (default 7 days)
        limit: Number of top players to return
        max_queries: Limit number of players to search (for testing)
        sport: Filter by sport (Baseball, Basketball, Football)
    
    Returns:
        List of players ranked by sales volume
    """
    scraper = EbayScraper()
    
    players_to_search = SEED_PLAYERS[:max_queries] if max_queries else SEED_PLAYERS
    if sport:
        players_to_search = [(n, s) for n, s in players_to_search if s == sport]
    
    print(f"Discovering top players from {len(players_to_search)} seed players (active eBay Browse matches)...")
    print(f"API calls needed: {len(players_to_search)} (1 per player, limit=1)")
    print("=" * 70)
    
    results: List[Dict] = []
    stats: Dict[str, Any] = {
        'seeds_queried': len(players_to_search),
        'sport_filter': sport,
        'http_not_200': 0,
        'json_errors_in_200': 0,
        'exceptions': 0,
        'zero_total_after_fallback': 0,
        'fallback_recovered': 0,
        'nonzero_seeds': 0,
        'browse_base_url': scraper.base_url,
        'browse_429_waits': 0,
        'ebay_quota_analytics': None,
        'ebay_ratelimit_last': None,
    }
    quota = fetch_buy_browse_app_quota(scraper)
    if quota:
        stats['ebay_quota_analytics'] = quota
        print(f"BROWSE_APP_QUOTA {json.dumps(quota, default=str)}", flush=True)
    samples: List[Dict[str, Any]] = []
    http_warn_logged = 0
    json_err_warn_logged = 0
    exc_warn_logged = 0

    def _sample(row: Dict[str, Any]) -> None:
        if len(samples) < 8:
            samples.append(row)

    # Browse item_summary/search: use category_ids as a query param (documented), not categoryId
    # inside ``filter`` — the latter can invalidate the filter and return total=0 for every query.
    # Default search already returns FIXED_PRICE listings; buyingOptions adds pure auctions.
    def _discovery_params(player_name: str, sp: Optional[str]) -> dict:
        p: dict = {
            'q': f'{player_name} card',
            'filter': 'buyingOptions:{AUCTION|FIXED_PRICE}',
            'limit': 1,
        }
        if sp == 'Baseball':
            p['category_ids'] = '261328'  # Trading Card Singles (URI param per Buy Browse docs)
        return p

    for i, (player_name, sport) in enumerate(players_to_search, 1):
        print(f"  [{i}/{len(players_to_search)}] {player_name}...", end=" ", flush=True)
        # Pace Browse calls — burst discovery after token refresh triggers 429 for every seed.
        if i > 1:
            time.sleep(0.5)

        try:
            params = _discovery_params(player_name, sport)
            r = _browse_item_summary_get(scraper, params, timeout=30, stats=stats)

            data = r.json() if r.content else {}
            if r.status_code != 200:
                stats['http_not_200'] += 1
                err = data.get('errors', data) if isinstance(data, dict) else r.text
                snippet = str(err)[:400]
                print(f"HTTP {r.status_code} {snippet[:200]}")
                _sample({
                    'player': player_name, 'sport': sport, 'phase': 'primary',
                    'http_status': r.status_code, 'params': params,
                    'ebay_errors': _ebay_errors_summary(data) if isinstance(data, dict) else None,
                    'body_snippet': snippet,
                })
                if http_warn_logged < 5:
                    log.warn(
                        'eBay Browse discovery HTTP non-success',
                        category='ebay_browse_discover_http',
                        context={
                            'player': player_name, 'sport': sport, 'http_status': r.status_code,
                            'params': params, 'ebay_errors': _ebay_errors_summary(data) if isinstance(data, dict) else None,
                            'body_snippet': snippet,
                        },
                    )
                    http_warn_logged += 1
                continue

            api_errs = _ebay_errors_summary(data)
            if api_errs:
                stats['json_errors_in_200'] += 1
                print(f"errors: {str(data.get('errors'))[:200]}")
                _sample({
                    'player': player_name, 'sport': sport, 'phase': 'primary',
                    'http_status': 200, 'params': params, 'ebay_errors': api_errs,
                })
                if json_err_warn_logged < 5:
                    log.warn(
                        'eBay Browse discovery returned errors[] with HTTP 200',
                        category='ebay_browse_discover_api_errors',
                        context={'player': player_name, 'sport': sport, 'params': params, 'ebay_errors': api_errs},
                    )
                    json_err_warn_logged += 1
            
            total = data.get('total', 0)
            if isinstance(total, str) and total.isdigit():
                total = int(total)
            elif not isinstance(total, int):
                total = 0

            used_fallback = False
            fb_params: Optional[dict] = None
            # Fallback: BIN-default search without buyingOptions filter
            if total == 0:
                fb_params = {'q': f'{player_name} card', 'limit': 1}
                if sport == 'Baseball':
                    fb_params['category_ids'] = '261328'
                r2 = _browse_item_summary_get(scraper, fb_params, timeout=30, stats=stats)
                if r2.status_code == 200:
                    d2 = r2.json()
                    t2 = d2.get('total', 0)
                    if isinstance(t2, str) and str(t2).isdigit():
                        t2 = int(t2)
                    if isinstance(t2, int) and t2 > 0:
                        total = t2
                        used_fallback = True
                        stats['fallback_recovered'] += 1

            print(f"{total:,} listings")
            
            if total == 0:
                stats['zero_total_after_fallback'] += 1
                _sample({
                    'player': player_name, 'sport': sport,
                    'primary_params': params, 'fallback_params': fb_params,
                    'used_fallback': used_fallback, 'total': 0,
                })
                continue

            stats['nonzero_seeds'] += 1
            results.append({
                'player_name': player_name,
                'sport': sport,
                'sales_volume': total,
            })
            
        except Exception as e:
            stats['exceptions'] += 1
            print(f"ERROR: {e}")
            _sample({'player': player_name, 'sport': sport, 'exception': str(e)[:400]})
            if exc_warn_logged < 5:
                log.warn(
                    f'eBay Browse discovery exception: {e}',
                    category='ebay_browse_discover_exception',
                    context={'player': player_name, 'sport': sport},
                )
                exc_warn_logged += 1
            continue
    
    # Rank by volume
    results.sort(key=lambda x: x['sales_volume'], reverse=True)
    
    print(f"\nSearched {len(players_to_search)} players, {len(results)} had listings")

    top_names = [p['player_name'] for p in results[:limit]]
    summary_line = {
        'event': 'discover_players',
        'ts': datetime.utcnow().isoformat() + 'Z',
        'nonzero_seeds': stats['nonzero_seeds'],
        'seeds_queried': stats['seeds_queried'],
        'returned_top_n': len(results[:limit]),
        'http_not_200': stats['http_not_200'],
        'json_errors_in_200': stats['json_errors_in_200'],
        'exceptions': stats['exceptions'],
        'zero_after_fallback': stats['zero_total_after_fallback'],
        'fallback_recovered': stats['fallback_recovered'],
        'browse_429_waits': stats.get('browse_429_waits', 0),
        'ebay_quota_analytics': stats.get('ebay_quota_analytics'),
        'ebay_ratelimit_last': stats.get('ebay_ratelimit_last'),
        'top_players_preview': top_names[:10],
    }
    print(f"DISCOVER_SUMMARY {json.dumps(summary_line, default=str)}", flush=True)

    degraded = stats['http_not_200'] or stats['exceptions'] or stats['json_errors_in_200']
    if degraded and results:
        log.warn(
            'Player discovery completed with errors but found some seeds',
            category='discover_run_degraded',
            context={**stats, 'samples': samples[:5], 'top_players': top_names[:limit]},
        )

    if not results:
        rate_hint = ''
        if stats.get('browse_429_waits'):
            rate_hint = (
                ' Many responses were HTTP 429 (Browse throttling). Discovery uses decreasing backoff; '
                'check DISCOVER_SUMMARY ebay_quota_analytics / ebay_ratelimit_last. '
                'Avoid stacking pipelines on the same app id or wait for quota reset.'
            )
        log.error(
            'Player discovery returned ZERO ranked players — opportunity pipeline cannot choose top 40.'
            + rate_hint,
            category='discover_all_seeds_zero',
            context={
                **stats,
                'samples': samples,
                'hint': 'Query error_log WHERE category IN (\'discover_all_seeds_zero\',\'ebay_browse_discover_http\',\'ebay_browse_discover_api_errors\') ORDER BY timestamp DESC LIMIT 20',
            },
            stack_trace=None,
        )

    return results[:limit]


def hot_player_names_for_pipeline(
    limit: int = 40,
    sport: str = 'Baseball',
    days: int = 7,
) -> List[str]:
    """Ranked player names for BIN and auction pipelines (eBay volume, not DB card counts)."""
    rows = discover_top_players(days=days, limit=limit, sport=sport)
    return [p['player_name'] for p in rows]


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Discover top players by eBay sales volume')
    parser.add_argument('--days', type=int, default=7, help='Lookback period in days')
    parser.add_argument('--limit', type=int, default=20, help='Number of top players')
    parser.add_argument('--max-queries', type=int, help='Limit players to search (for testing)')
    parser.add_argument('--sport', type=str, default='Baseball', help='Filter by sport (default: Baseball)')
    args = parser.parse_args()
    
    players = discover_top_players(
        days=args.days,
        limit=args.limit,
        max_queries=args.max_queries,
        sport=args.sport
    )
    
    print("\n" + "=" * 70)
    print(f"TOP {len(players)} PLAYERS BY SALES VOLUME (Last {args.days} Days)")
    print("=" * 70)
    print(f"{'Rank':>4} {'Player':<28} {'Sport':<12} {'Listings':>10}")
    print("-" * 60)
    
    for i, p in enumerate(players, 1):
        print(f"{i:4d} {p['player_name']:<28} {p['sport']:<12} {p['sales_volume']:>10,}")
    
    print(f"\nThese {len(players)} players should be used for data collection.")
