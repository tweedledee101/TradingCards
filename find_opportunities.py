#!/usr/bin/env python3
"""SCP-to-eBay Opportunity Pipeline — SCP catalog, eBay listings, store opportunities."""
from __future__ import annotations

import argparse
import sys
import time
import re
from contextlib import closing
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from backend.scrapers.ebay_scraper import EbayScraper
from backend.utils.job_tracker import JobTracker
from backend.utils.logger import get_logger
from backend.utils.retention import run_if_stale
from backend.utils.database import SessionLocal
from backend.models import Opportunity, PipelineListingSkip
from backend.services.dev_strict_listing import dev_strict_listing_skip_reason
from backend.services.scp_sold_comps_reconcile import apply_scp_sold_comps_reconcile

log = get_logger('opportunity_finder')

FEE_RATE = 0.13

# BIN price must be at least this fraction of SCP to be considered.
# Below this, the listing is almost certainly a different product, wrong
# condition, or a scam. Real arbitrage lives in the margins, not at 90% off.
MIN_PRICE_RATIO = 0.30

# Known reprint/replica indicators in eBay titles
REPRINT_PATTERNS = [
    'replica', 'reprint', 'rp', 'project 2020', 'project 70', 'project70',
    'shoebox treasures', 'sticker', 'die-cut replica', 'custom card',
    'novelty', 'art card', 'aceo'
]


def get_scp_catalog(driver, player_name):
    """Get all card variations + prices for a player from SportsCardsPro"""
    query = player_name.replace(' ', '+')
    url = f"https://www.sportscardspro.com/search-products?q={query}&type=prices"
    driver.get(url)
    time.sleep(5)

    catalog = []
    rows = driver.find_elements(By.CSS_SELECTOR, "table tr")

    for row in rows:
        try:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 6:
                continue

            title = cells[1].text.strip()
            set_name = cells[2].text.strip()
            ungraded_str = cells[3].text.strip()
            grade_9_str = cells[4].text.strip()
            psa_10_str = cells[5].text.strip()

            if not title or not ungraded_str or '$' not in ungraded_str:
                continue

            # Price is first line, volume may be on subsequent lines
            ungraded_lines = ungraded_str.split('\n')
            price = float(ungraded_lines[0].replace('$', '').replace(',', '').strip())

            # Extract volume from the ungraded cell text or sub-elements
            volume_text = ''
            cell_full_text = cells[3].text.strip()
            for line in cell_full_text.split('\n'):
                if 'volume' in line.lower() or 'sale' in line.lower() or 'rare' in line.lower():
                    volume_text = line.strip()
                    break

            # Parse Grade 9 and PSA 10 prices
            grade_9 = None
            psa_10 = None
            if '$' in grade_9_str:
                try:
                    grade_9 = float(grade_9_str.replace('$', '').replace(',', '').strip())
                except ValueError:
                    pass
            if '$' in psa_10_str:
                try:
                    psa_10 = float(psa_10_str.replace('$', '').replace(',', '').strip())
                except ValueError:
                    pass

            # Get SCP product URL from the row's first link
            scp_url = None
            links = row.find_elements(By.TAG_NAME, "a")
            if links:
                scp_url = links[0].get_attribute('href')

            parallel_match = re.search(r'\[([^\]]+)\]', title)
            parallel = parallel_match.group(1) if parallel_match else 'Base'
            if parallel in ('RC', 'AU', 'SP'):
                parallel = 'Base'

            number_match = re.search(r'#([\w\-]+)', title)
            card_number = number_match.group(1) if number_match else None

            print_run_match = re.search(r'/(\d+)', title)
            print_run = print_run_match.group(1) if print_run_match else None

            year_match = re.search(r'(\d{4})', set_name)
            year = int(year_match.group(1)) if year_match else None

            clean_set = re.sub(r'^\d{4}\s+', '', set_name)
            clean_set = re.sub(r'\s*\(.*?\)\s*$', '', clean_set).strip()

            catalog.append({
                'player': player_name,
                'title': title,
                'parallel': parallel,
                'card_number': card_number,
                'print_run': print_run,
                'year': year,
                'set_name': clean_set,
                'price': price,
                'grade_9': grade_9,
                'psa_10': psa_10,
                'scp_url': scp_url,
                'volume': volume_text
            })
        except (ValueError, IndexError):
            continue

    return catalog


def build_ebay_query(variation):
    """Build precise eBay search query from SCP catalog entry"""
    parts = [variation['player']]

    if variation['year']:
        parts.append(str(variation['year']))

    parts.append(variation['set_name'])

    if variation['card_number']:
        parts.append(f"#{variation['card_number']}")

    if variation['parallel'] != 'Base':
        parts.append(variation['parallel'])

    if variation['print_run']:
        parts.append(f"/{variation['print_run']}")

    return ' '.join(parts)


def _ebay_numeric_id(listing: dict) -> str | None:
    raw = listing.get("ebay_item_id") or ""
    if "|" in raw:
        return raw.split("|")[1].strip() or None
    return raw.strip() or None


def _record_bin_listing_skip(
    sink: list | None,
    reason: str,
    *,
    pipeline: str,
    sport: str,
    search_query: str,
    pipeline_card_label: str,
    listing: dict | None,
    scp_price,
    job_run_id: int | None,
    ratio: float | None = None,
    extra: dict | None = None,
) -> None:
    if sink is None:
        return
    try:
        price = float(listing.get("price", 0) or 0) if listing else None
    except (TypeError, ValueError):
        price = None
    sink.append({
        "pipeline": pipeline,
        "skip_reason": reason,
        "ebay_item_id": _ebay_numeric_id(listing) if listing else None,
        "sport": sport,
        "search_query": search_query[:2000] if search_query else None,
        "pipeline_card_label": pipeline_card_label[:2000] if pipeline_card_label else None,
        "ebay_title": ((listing.get("title") or "")[:500] if listing else None),
        "buy_price": price,
        "scp_price": float(scp_price) if scp_price is not None else None,
        "ratio": ratio,
        "extra": extra,
        "job_run_id": job_run_id,
    })


def find_ebay_opportunities(
    scraper,
    variation,
    max_budget,
    *,
    vision_post_pipeline_queue: list | None = None,
    vision_queue_max: int = 0,
    sport: str = "Baseball",
    listing_skip_sink: list | None = None,
    search_query: str = "",
    pipeline_card_label: str = "",
    job_run_id: int | None = None,
    dev_strict_listings: bool = False,
    cache_db=None,
    cache_ttl_hours: int = 12,
):
    """Search eBay for listings below SCP price (active **BIN + auction** — ``get_active_listings``).

    ``vision_post_pipeline_queue`` collects a **bounded sample** of listings for optional
    **post-pipeline** multimodal review (Nova / manual). The main pipeline never waits on
    vision and never uses vision to include/exclude opportunities.

    ``dev_strict_listings``: tighter title vs parallel/set tokens (dev experiments only).
    """
    query = build_ebay_query(variation)
    scp_price = variation['price']
    if not pipeline_card_label:
        pipeline_card_label = (
            f"{variation['player']} {variation['year']} {variation['set_name']} "
            f"#{variation.get('card_number')} [{variation.get('parallel', 'Base')}]"
        )
    if not search_query:
        search_query = query

    meta = {'listings_fetched': 0, 'query': query, 'cache_hit': False}
    try:
        if cache_db is not None:
            from backend.utils.ebay_search_cache import cached_get_active_listings
            listings = cached_get_active_listings(scraper, query, cache_db, ttl_hours=cache_ttl_hours)
            # Check if this was a cache hit (no new API call)
            from backend.utils.ebay_search_cache import get_cached_results
            meta['cache_hit'] = get_cached_results(cache_db, query, ttl_hours=cache_ttl_hours) is not None
        else:
            listings = scraper.get_active_listings(query)
        meta['listings_fetched'] = len(listings or [])
    except Exception as e:
        log.error(f'eBay search failed: {e}', category='ebay_api_error', context={
            'player': variation['player'], 'query': query
        })
        meta['ebay_error'] = True
        return query, [], meta

    JUNK_PATTERNS = ['you pick', 'pick your', 'complete your set', 'pick a card',
                     'choose your', 'pick em', "pick 'em", 'buy 3 get',
                     'lot of', 'mystery', 'repack', 'break',
                     'digital', 'bunt']

    # Factory/complete set/exclusive print run versions are different products
    FACTORY_SET_PATTERNS = ['complete set', 'complete sets', 'factory set',
                            'factory sealed', 'hobby set', 'retail set',
                            '582 montgomery', 'montgomery club',
                            'walmart exclusive', 'target exclusive',
                            'base set photo variation', 'photo variations #']

    opportunities = []
    seen_ids = set()
    player_lower = variation['player'].lower()
    card_number = variation.get('card_number', '')
    year = str(variation.get('year', ''))

    for listing in listings:
        try:
            title = listing.get('title', '')
            title_lower = title.lower()

            if player_lower not in title_lower:
                continue

            if year and year not in title:
                continue

            if card_number:
                num_clean = card_number.replace('#', '').strip()
                if f'#{num_clean}' not in title and f'# {num_clean}' not in title and f'{num_clean}' not in title_lower:
                    continue
                if len(num_clean) <= 3 and f'#{num_clean}' not in title and f'# {num_clean}' not in title:
                    continue

            if any(junk in title_lower for junk in JUNK_PATTERNS):
                continue

            # Factory/complete set versions are different products (much cheaper)
            # Only allow if the SCP card itself is from a complete/factory set
            scp_title_lower = variation.get('title', '').lower()
            set_name_check = variation.get('set_name', '').lower()
            is_scp_factory = any(fs in scp_title_lower or fs in set_name_check
                                 for fs in FACTORY_SET_PATTERNS)
            if not is_scp_factory and any(fs in title_lower for fs in FACTORY_SET_PATTERNS):
                log.warn('Factory/complete set version filtered', category='factory_set_mismatch', context={
                    'scp_card': f"{variation['player']} {variation['set_name']} #{card_number} [{variation.get('parallel', 'Base')}]",
                    'ebay_title': title, 'buy_price': float(listing.get('price', 0)),
                    'scp_price': scp_price
                })
                _record_bin_listing_skip(
                    listing_skip_sink, "factory_set_mismatch",
                    pipeline="opportunity_finder", sport=sport, search_query=search_query,
                    pipeline_card_label=pipeline_card_label, listing=listing, scp_price=scp_price,
                    job_run_id=job_run_id,
                )
                continue

            if dev_strict_listings:
                rs = dev_strict_listing_skip_reason(title, variation)
                if rs:
                    _record_bin_listing_skip(
                        listing_skip_sink, rs,
                        pipeline="opportunity_finder", sport=sport, search_query=search_query,
                        pipeline_card_label=pipeline_card_label, listing=listing, scp_price=scp_price,
                        job_run_id=job_run_id, extra={"dev_strict": True},
                    )
                    continue

            parallel = variation.get('parallel', 'Base')
            if parallel != 'Base':
                parallel_keywords = parallel.lower().split()
                if not any(kw in title_lower for kw in parallel_keywords if len(kw) >= 3):
                    _record_bin_listing_skip(
                        listing_skip_sink, "parallel_mismatch",
                        pipeline="opportunity_finder", sport=sport, search_query=search_query,
                        pipeline_card_label=pipeline_card_label, listing=listing, scp_price=scp_price,
                        job_run_id=job_run_id, extra={"parallel": parallel},
                    )
                    continue

            # Grade detection: skip graded listings (PSA/BGS/SGC/CGC).
            # Comparing graded card prices to ungraded SCP is always wrong.
            GRADED_PATTERNS = ['psa ', 'bgs ', 'sgc ', 'cgc ', 'fcgs ', 'gem mint',
                               'mint 10', 'mint 9', ' graded ', 'psa10', 'psa 10',
                               'bgs 10', 'sgc 10', 'cgc 10']
            if any(gp in title_lower for gp in GRADED_PATTERNS):
                _record_bin_listing_skip(
                    listing_skip_sink, "graded_listing",
                    pipeline="opportunity_finder", sport=sport, search_query=search_query,
                    pipeline_card_label=pipeline_card_label, listing=listing, scp_price=scp_price,
                    job_run_id=job_run_id,
                )
                continue

            is_auction = listing.get('listing_type') == 'auction'

            price = float(listing.get('price', 0))
            if price <= 0 or price > max_budget:
                continue

            # Price floor: BIN below 30% of SCP is not the same product.
            # Auctions skip this -- low current bids are normal.
            if not is_auction and price < scp_price * MIN_PRICE_RATIO:
                log.warn('BIN price too far below SCP market rate', category='price_floor', context={
                    'scp_card': f"{variation['player']} {variation['set_name']} #{card_number} [{variation.get('parallel', 'Base')}]",
                    'ebay_title': title, 'buy_price': price, 'scp_price': scp_price,
                    'ratio': round(price / scp_price, 2)
                })
                if (
                    vision_post_pipeline_queue is not None
                    and vision_queue_max > 0
                    and len(vision_post_pipeline_queue) < vision_queue_max
                ):
                    vu = list(listing.get("image_urls") or [])
                    if listing.get("image_url") and listing["image_url"] not in vu:
                        vu.insert(0, listing["image_url"])
                    vision_post_pipeline_queue.append(
                        {
                            "reason": "bin_price_floor_excluded",
                            "pipeline_card": (
                                f"{variation['player']} {variation.get('year')} "
                                f"{variation['set_name']} #{card_number} [{variation.get('parallel', 'Base')}]"
                            ),
                            "scp_price": float(scp_price),
                            "buy_price": float(price),
                            "ebay_item_id": _ebay_numeric_id(listing),
                            "title": title[:240],
                            "image_urls": vu[:15],
                        }
                    )
                _record_bin_listing_skip(
                    listing_skip_sink, "price_floor",
                    pipeline="opportunity_finder", sport=sport, search_query=search_query,
                    pipeline_card_label=pipeline_card_label, listing=listing, scp_price=scp_price,
                    job_run_id=job_run_id, ratio=round(price / scp_price, 4) if scp_price else None,
                )
                continue

            # Reprint / replica detection
            if any(rp in title_lower for rp in REPRINT_PATTERNS):
                log.warn('Reprint/replica detected', category='reprint_match', context={
                    'scp_card': f"{variation['player']} {variation['set_name']} #{card_number} [{variation.get('parallel', 'Base')}]",
                    'ebay_title': title, 'buy_price': price, 'scp_price': scp_price
                })
                _record_bin_listing_skip(
                    listing_skip_sink, "reprint_match",
                    pipeline="opportunity_finder", sport=sport, search_query=search_query,
                    pipeline_card_label=pipeline_card_label, listing=listing, scp_price=scp_price,
                    job_run_id=job_run_id,
                )
                continue

            # Wrong set detection -- eBay title has a different set name
            set_name_lower = variation.get('set_name', '').lower()
            KNOWN_SETS = ['gold label', 'gallery', 'stadium club', 'allen & ginter',
                          'gypsy queen', 'heritage', 'bowman', 'chrome', 'finest',
                          'inception', 'tribute', 'luminaries', 'dynasty', 'diamond icons']
            wrong_set = False
            for known_set in KNOWN_SETS:
                if known_set in title_lower and known_set not in set_name_lower:
                    log.warn('Wrong set in eBay listing', category='wrong_variation', context={
                        'scp_card': f"{variation['player']} {variation['set_name']} #{card_number}",
                        'scp_set': variation.get('set_name', ''),
                        'ebay_title': title, 'detected_set': known_set,
                        'buy_price': price, 'scp_price': scp_price
                    })
                    wrong_set = True
                    break
            if wrong_set:
                _record_bin_listing_skip(
                    listing_skip_sink, "wrong_set_heuristic",
                    pipeline="opportunity_finder", sport=sport, search_query=search_query,
                    pipeline_card_label=pipeline_card_label, listing=listing, scp_price=scp_price,
                    job_run_id=job_run_id,
                )
                continue

            profit = scp_price - price - (price * FEE_RATE)
            roi = (profit / price) * 100

            # SCP variant sanity check: if buy price is far below SCP, check if there's
            # a cheaper SCP variant for the same card# that better explains the price.
            # This catches wrong parallel matches (e.g., Aqua Rainbow $56 matched to Blue Rainbow $193).
            if profit > 0 and price < scp_price * 0.50 and cache_db is not None:
                try:
                    from backend.utils.scp_variant_sanity import check_variant_sanity
                    sanity = check_variant_sanity(
                        cache_db, variation['player'], variation.get('year'),
                        variation.get('card_number'), scp_price, price,
                    )
                    if sanity and sanity.get('likely_wrong_parallel'):
                        _record_bin_listing_skip(
                            listing_skip_sink, "variant_sanity_reject",
                            pipeline="opportunity_finder", sport=sport, search_query=search_query,
                            pipeline_card_label=pipeline_card_label, listing=listing, scp_price=scp_price,
                            job_run_id=job_run_id,
                            extra={"closest_parallel": sanity.get('closest_parallel'),
                                   "closest_price": sanity.get('closest_price')},
                        )
                        continue
                except Exception:
                    pass  # sanity check failure is non-fatal

            if profit <= 0 or roi <= 0:
                _record_bin_listing_skip(
                    listing_skip_sink, "economics_below_threshold",
                    pipeline="opportunity_finder", sport=sport, search_query=search_query,
                    pipeline_card_label=pipeline_card_label, listing=listing, scp_price=scp_price,
                    job_run_id=job_run_id, extra={"profit": float(profit), "roi": float(roi)},
                )
                continue

            item_id = listing.get('ebay_item_id', '')
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)

            numeric_id = item_id.split('|')[1] if '|' in item_id else item_id
            url = f"https://www.ebay.com/itm/{numeric_id}" if numeric_id else 'N/A'

            # Flag BIN listings between 30-50% of SCP -- they pass but deserve scrutiny.
            # Auctions are never flagged for low price.
            flagged = (not is_auction) and price < scp_price * 0.50
            if flagged:
                log.warn('BIN price well below SCP market rate', category='suspicious_price', context={
                    'scp_card': f"{variation['player']} {variation['set_name']} #{card_number} [{variation.get('parallel', 'Base')}]",
                    'ebay_title': title, 'buy_price': price, 'scp_price': scp_price,
                    'ratio': round(price / scp_price, 2), 'url': url
                })

            img_urls = list(listing.get('image_urls') or [])
            if listing.get('image_url') and listing['image_url'] not in img_urls:
                img_urls.insert(0, listing['image_url'])

            opportunities.append({
                'title': listing.get('title', 'Unknown'),
                'buy_price': price,
                'scp_price': scp_price,
                'profit': profit,
                'roi': roi,
                'url': url,
                'image_url': listing.get('image_url'),
                'listing_image_urls': img_urls,
                'flagged': flagged,
                'listing_type': 'auction' if is_auction else 'buy_it_now'
            })
        except (ValueError, TypeError):
            continue

    meta['opportunities_raw'] = len(opportunities)
    return query, opportunities, meta


def get_hot_players(
    limit=40,
    sport='Baseball',
    days=7,
    db_session=None,
    dynamic_sales_player_limit: int = 0,
    dynamic_sales_lookback_days: int = 30,
    max_discovery_candidates: int = 100,
    rank_source: str = 'browse',
    sales_rank_lookback_days: int = 7,
    sales_rank_fallback_browse: bool = False,
    sold_comps_lookback_days: int = 30,
    sold_comps_fallback_browse: bool = True,
):
    """Rank players (``sales`` counts, ``sold_comps``, or Browse); optional sales merge on Browse path."""
    from backend.discover_players import discover_top_players

    kw = {
        'days': days,
        'limit': limit,
        'sport': sport,
        'rank_source': rank_source,
        'sales_rank_lookback_days': sales_rank_lookback_days,
        'sales_rank_fallback_browse': sales_rank_fallback_browse,
        'sold_comps_lookback_days': sold_comps_lookback_days,
        'sold_comps_fallback_browse': sold_comps_fallback_browse,
    }
    if db_session is not None or dynamic_sales_player_limit > 0:
        kw.update(
            db_session=db_session,
            dynamic_sales_lookback_days=dynamic_sales_lookback_days,
            dynamic_sales_player_limit=dynamic_sales_player_limit,
            max_discovery_candidates=max_discovery_candidates,
        )
    rows = discover_top_players(**kw)
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SCP-to-eBay Opportunity Pipeline')
    parser.add_argument('--max-budget', type=float, default=200, help='Max buy price (default: $200)')
    parser.add_argument('--min-profit', type=float, default=10, help='Min profit after fees (default: $10)')
    parser.add_argument('--min-roi', type=float, default=20, help='Min ROI %% (default: 20)')
    parser.add_argument('--min-scp-price', type=float, default=20, help='Min SCP price to consider (default: $20)')
    parser.add_argument('--max-scp-price', type=float, default=1000, help='Max SCP price (default: $1000)')
    parser.add_argument('--players', type=str, default=None, help='Comma-separated player names')
    parser.add_argument(
        '--top-players',
        type=int,
        default=100,
        help='How many ranked players to run (default: 100; GitHub Actions often passes 40)',
    )
    parser.add_argument('--days', type=int, default=7, help='eBay volume lookback days for discovery (default: 7)')
    parser.add_argument(
        '--skip-auction-chain',
        action='store_true',
        help='Do not run find_auction_opportunities after BIN (use separate job/workflow for auctions)',
    )
    parser.add_argument(
        '--sport',
        type=str,
        default='Baseball',
        help='Discovery sport: Baseball, Basketball, Football, or all (default: Baseball)',
    )
    parser.add_argument(
        '--dynamic-seed-limit',
        type=int,
        default=50,
        help='Merge top N (player,sport) from recent DB sales into discovery candidates (0=off)',
    )
    parser.add_argument(
        '--dynamic-seed-days',
        type=int,
        default=30,
        help='Lookback days when ranking players from sales table (default: 30)',
    )
    parser.add_argument(
        '--no-dynamic-seeds',
        action='store_true',
        help='Anchor SEED_PLAYERS only (no sales-driven candidate merge)',
    )
    parser.add_argument(
        '--max-discovery-candidates',
        type=int,
        default=100,
        help='Max Browse discovery calls before ranking (default: 100)',
    )
    parser.add_argument(
        '--player-rank-source',
        type=str,
        choices=('browse', 'sold_comps', 'sales'),
        default='browse',
        help=(
            'browse=eBay totals on seeds (default). sales=count sales rows per player in lookback (no Browse). '
            'sold_comps=130point row counts'
        ),
    )
    parser.add_argument(
        '--sales-rank-days',
        type=int,
        default=7,
        help='Lookback days on sales.sale_date when --player-rank-source sales (default: 7)',
    )
    parser.add_argument(
        '--sales-rank-fallback-browse',
        action='store_true',
        help='If sales ranking returns empty, fall back to Browse ranking',
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
        help='If sold_comps ranking returns empty, exit instead of falling back to Browse',
    )
    parser.add_argument(
        '--dev-strict-listings',
        action='store_true',
        help='Dev: stricter eBay title vs SCP parallel + set tokens before economics (text only)',
    )
    parser.add_argument(
        '--dev-reconcile-scp-comps',
        action='store_true',
        help='Dev: adjust variation reference price from SCP toward sold_comps median before eBay economics',
    )
    parser.add_argument(
        '--dev-vision-queue-pass',
        action='store_true',
        help='Dev: enqueue every passing opportunity listing (up to max) for post-pipeline vision/CE review',
    )
    parser.add_argument(
        '--dev-vision-queue-max',
        type=int,
        default=200,
        help='Cap for --dev-vision-queue-pass (default 200)',
    )
    parser.add_argument(
        '--use-scp-cache',
        action='store_true',
        help='Read SCP catalog from scp_cache table instead of Selenium (no browser needed). Uses cached data from prior runs.',
    )
    parser.add_argument(
        '--max-ebay-variations',
        type=int,
        default=0,
        help='Cap how many SCP variations get an eBay search (0=no cap). Use in CI to finish before job timeout.',
    )
    parser.add_argument(
        '--bin-replace-scope',
        type=str,
        choices=('all', 'shard_players'),
        default='all',
        help=(
            'all=delete all BIN rows then insert (single runner). '
            'shard_players=delete BIN rows only for --players in this run (parallel shards).'
        ),
    )
    args = parser.parse_args()

    if args.bin_replace_scope == 'shard_players':
        if not args.players or not str(args.players).strip():
            print(
                'error: --bin-replace-scope shard_players requires --players (comma-separated)',
                file=sys.stderr,
            )
            sys.exit(2)

    print("=" * 80)
    print("SCP-TO-EBAY OPPORTUNITY PIPELINE")
    print("=" * 80)
    print(f"\nBudget: ${args.max_budget:.0f} max buy | Min Profit: ${args.min_profit:.0f} | Min ROI: {args.min_roi:.0f}%")
    print(f"SCP Price Range: ${args.min_scp_price:.0f}-${args.max_scp_price:.0f}\n")
    print(f"BIN DB replace scope: {args.bin_replace_scope}\n")

    dyn_limit = 0 if args.no_dynamic_seeds else max(0, args.dynamic_seed_limit)

    player_rows = []
    players = []
    # Step 1: ranked players (list of dicts player_name + sport)
    if args.players:
        sport_default = 'Baseball' if str(args.sport).strip().lower() == 'all' else str(args.sport).strip().title()
        player_rows = [
            {'player_name': p.strip(), 'sport': sport_default}
            for p in args.players.split(',') if p.strip()
        ]
    else:
        print(
            f"Finding hot players (rank={args.player_rank_source}; "
            f"optional sales-driven candidate merge on Browse path)..."
        )
        with closing(SessionLocal()) as db_disc:
            player_rows = get_hot_players(
                limit=args.top_players,
                sport=args.sport,
                days=args.days,
                db_session=db_disc,
                dynamic_sales_player_limit=dyn_limit,
                dynamic_sales_lookback_days=args.dynamic_seed_days,
                max_discovery_candidates=args.max_discovery_candidates,
                rank_source=args.player_rank_source,
                sales_rank_lookback_days=args.sales_rank_days,
                sales_rank_fallback_browse=bool(args.sales_rank_fallback_browse),
                sold_comps_lookback_days=args.sold_comps_rank_days,
                sold_comps_fallback_browse=not args.no_sold_comps_fallback_browse,
            )

    players = [r['player_name'] for r in player_rows]
    print(f"Players ({len(players)}): {', '.join(players[:12])}{'…' if len(players) > 12 else ''}\n")

    log.info('Pipeline starting', context={
        'players': len(players), 'max_budget': args.max_budget,
        'min_profit': args.min_profit, 'min_roi': args.min_roi,
        'sport': args.sport, 'dynamic_seed_limit': dyn_limit,
    })

    # Job tracking
    tracker = JobTracker('opportunity_finder')
    tracker.start(
        total=len(players),
        parameters={
            'max_budget': args.max_budget,
            'min_profit': args.min_profit,
            'min_roi': args.min_roi,
            'players': players,
            'sport': args.sport,
            'dynamic_seed_limit': dyn_limit,
            'dynamic_seed_days': args.dynamic_seed_days,
            'skip_auction_chain': bool(args.skip_auction_chain),
            'max_ebay_variations': args.max_ebay_variations or None,
            'bin_replace_scope': args.bin_replace_scope,
            'player_rank_source': args.player_rank_source,
            'sales_rank_days': args.sales_rank_days,
            'sales_rank_fallback_browse': bool(args.sales_rank_fallback_browse),
            'sold_comps_rank_days': args.sold_comps_rank_days,
            'no_sold_comps_fallback_browse': bool(args.no_sold_comps_fallback_browse),
            'dev_strict_listings': bool(args.dev_strict_listings),
            'dev_reconcile_scp_comps': bool(args.dev_reconcile_scp_comps),
            'dev_vision_queue_pass': bool(args.dev_vision_queue_pass),
            'dev_vision_queue_max': int(args.dev_vision_queue_max),
        }
    )

    if not players:
        msg = (
            "Player list is empty after ranking. For browse: check DISCOVER_SUMMARY / error_log "
            "(discover_all_seeds_zero). For sales: ensure sales.sale_date rows exist in "
            f"--sales-rank-days ({args.sales_rank_days}). Use --players a,b,c to override."
        )
        print(msg, file=sys.stderr)
        log.error(msg, category='discover_zero_players', context={'top_players': args.top_players})
        tracker.fail(msg)
        sys.exit(1)

    listing_skip_buffer: list = []
    skip_db = SessionLocal()

    def _flush_listing_skips() -> None:
        if not listing_skip_buffer:
            return
        try:
            skip_db.bulk_insert_mappings(PipelineListingSkip, listing_skip_buffer)
            skip_db.commit()
            listing_skip_buffer.clear()
        except Exception as ex:
            skip_db.rollback()
            log.error(f'Persist listing skips failed: {ex}', category='skip_persist_error')

    try:
        # Step 2/3: Get SCP catalogs
        all_variations = []

        if args.use_scp_cache:
            # Read from scp_cache table -- no Selenium needed
            print("Reading SCP catalog from scp_cache (no browser)...")
            import json as _json
            cache_db = SessionLocal()
            from backend.models import SCPCache
            for i, prow in enumerate(player_rows, 1):
                player = prow['player_name']
                ply_sport = prow.get('sport') or 'Baseball'
                print(f"\n[SCP-cache {i}/{len(player_rows)}] {player} ({ply_sport})")
                rows = cache_db.query(SCPCache).filter(
                    SCPCache.player_name.ilike(f"%{player}%")
                ).all()
                catalog = []
                for row in rows:
                    variants = row.variants
                    if isinstance(variants, str):
                        variants = _json.loads(variants)
                    if not isinstance(variants, list):
                        continue
                    for v in variants:
                        price = v.get('ungraded') or 0
                        if not price or price <= 0:
                            continue
                        catalog.append({
                            'player': player,
                            'title': v.get('raw_title', ''),
                            'parallel': v.get('parallel', 'Base'),
                            'card_number': str(row.card_number or v.get('card_number', '')),
                            'print_run': v.get('print_run'),
                            'year': row.card_year or v.get('year'),
                            'set_name': v.get('card_set', ''),
                            'price': float(price),
                            'grade_9': v.get('grade_9'),
                            'psa_10': v.get('psa_10'),
                            'scp_url': v.get('url'),
                            'volume': '',
                        })
                print(f"  {len(catalog)} total variations from cache")
                affordable = [v for v in catalog if args.min_scp_price <= v['price'] <= args.max_scp_price]
                print(f"  {len(affordable)} tradeable in ${args.min_scp_price:.0f}-${args.max_scp_price:.0f} range")
                for v in affordable:
                    print(f"    ${v['price']:>8.2f} | {v['title'][:50]} | {v['set_name']}")
                    v['_pipeline_sport'] = ply_sport
                all_variations.extend(affordable)
                tracker.update(processed=i)
            cache_db.close()
        else:
            # Selenium path (original)
            print("Starting browser for SportsCardsPro...")
            opts = Options()
            opts.add_argument('--headless')
            import shutil
            for firefox_path in ['/usr/lib/firefox/firefox', '/usr/bin/firefox-esr', '/usr/bin/firefox']:
                if shutil.which(firefox_path) or __import__('os').path.exists(firefox_path):
                    opts.binary_location = firefox_path
                    break
            service = Service(executable_path=shutil.which('geckodriver') or '/usr/local/bin/geckodriver')
            driver = webdriver.Firefox(options=opts, service=service)

            for i, prow in enumerate(player_rows, 1):
                player = prow['player_name']
                ply_sport = prow.get('sport') or 'Baseball'
                print(f"\n[SCP {i}/{len(player_rows)}] {player} ({ply_sport})")
                catalog = get_scp_catalog(driver, player)
                print(f"  {len(catalog)} total variations found")

                if not catalog:
                    log.warn('SCP returned 0 variations', category='scp_empty', context={
                        'player': player
                    })

                affordable = [v for v in catalog if args.min_scp_price <= v['price'] <= args.max_scp_price]

                LOW_VOLUME = ['rare', '1 sale per year', '2 sales per year']
                liquid = []
                for v in affordable:
                    vol = v.get('volume', '').lower()
                    if any(lv in vol for lv in LOW_VOLUME):
                        continue
                    liquid.append(v)

                skipped = len(affordable) - len(liquid)
                if skipped:
                    print(f"  {skipped} skipped (low volume)")
                affordable = liquid

                print(f"  {len(affordable)} tradeable in ${args.min_scp_price:.0f}-${args.max_scp_price:.0f} range")

                for v in affordable:
                    vol_tag = f" [{v['volume']}]" if v.get('volume') else ''
                    print(f"    ${v['price']:>8.2f} | {v['title'][:50]} | {v['set_name']}{vol_tag}")
                    v['_pipeline_sport'] = ply_sport

                all_variations.extend(affordable)
                tracker.update(processed=i)
                time.sleep(2)

            driver.quit()
        print(f"\n{'=' * 80}")
        print(f"Total variations to check on eBay: {len(all_variations)}")
        if args.max_ebay_variations and len(all_variations) > args.max_ebay_variations:
            # Prioritize the $20-$200 sweet spot where arbitrage actually exists,
            # then $200-$500, then $5-$20 (mostly noise at low end)
            def _sort_key(v):
                p = v['price']
                if 20 <= p <= 200:
                    return (0, -p)  # sweet spot first, highest price first
                elif 200 < p <= 500:
                    return (1, -p)
                else:
                    return (2, -p)
            all_variations.sort(key=_sort_key)
            print(
                f"  (capped to {args.max_ebay_variations} via --max-ebay-variations — "
                f"full list had {len(all_variations)}, prioritized $20-$200 sweet spot)"
            )
            all_variations = all_variations[: args.max_ebay_variations]
        print(f"{'=' * 80}\n")

        if not all_variations:
            msg = (
                "No SCP variations in price range — SCP returned nothing usable, site/blocking/HTML changed, "
                "or filters (--min-scp-price / volume) removed everything. Adjust thresholds or check SCP rows."
            )
            print(msg, file=sys.stderr)
            log.error(msg, category='scp_no_variations', context={
                'players': len(players),
                'min_scp_price': args.min_scp_price,
                'max_scp_price': args.max_scp_price,
            })
            tracker.fail(msg)
            sys.exit(1)

        # Step 4: Search eBay for each variation
        scraper = EbayScraper()
        all_opportunities = []
        ebay_variation_stats: list = []
        vision_post_pipeline_queue: list = []
        _VISION_Q_MAX = int(args.dev_vision_queue_max) if args.dev_vision_queue_pass else 50
        recon_db = SessionLocal() if args.dev_reconcile_scp_comps else None
        vision_seen_ids: set[str] = set()
        cache_db = SessionLocal()  # eBay search cache DB session

        try:
            for i, var in enumerate(all_variations, 1):
                label = f"{var['player']} {var['year']} {var['set_name']} #{var['card_number']} [{var['parallel']}]"
                print(f"[eBay {i}/{len(all_variations)}] {label}")

                if recon_db is not None:
                    try:
                        apply_scp_sold_comps_reconcile(recon_db, var)
                        d = var.get('_price_reconciliation') or {}
                        if d.get('action') and d.get('action') != 'keep_scp':
                            print(
                                f"  SCP raw ${var.get('_scp_price_raw', var['price']):.2f} → "
                                f"ref ${var['price']:.2f} ({d.get('action')})"
                            )
                        else:
                            print(f"  SCP (ref): ${var['price']:.2f}")
                    except Exception as ex:
                        log.warn(
                            f'SCP/sold_comps reconcile skipped: {ex}',
                            category='scp_reconcile_error',
                            context={'card': label[:120]},
                        )
                        print(f"  SCP (ref): ${var['price']:.2f}")
                else:
                    print(f"  SCP: ${var['price']:.2f}")

                ply_sport = var.get('_pipeline_sport') or 'Baseball'
                query, opps, ebay_meta = find_ebay_opportunities(
                    scraper,
                    var,
                    max_budget=args.max_budget,
                    vision_post_pipeline_queue=vision_post_pipeline_queue,
                    vision_queue_max=_VISION_Q_MAX,
                    sport=ply_sport,
                    listing_skip_sink=listing_skip_buffer,
                    job_run_id=tracker.run_id,
                    dev_strict_listings=bool(args.dev_strict_listings),
                    cache_db=cache_db,
                )
                print(f"  Query: {query}")
                if len(listing_skip_buffer) >= 200:
                    _flush_listing_skips()

                good_opps = [o for o in opps if o['profit'] >= args.min_profit and o['roi'] >= args.min_roi]

                if good_opps:
                    print(f"  {len(good_opps)} opportunities found!")
                    for opp in good_opps:
                        tag = '[AUCTION]' if opp.get('listing_type') == 'auction' else '[BIN]'
                        print(f"    {tag} ${opp['buy_price']:.2f} -> ${opp['scp_price']:.2f} = ${opp['profit']:.2f} profit ({opp['roi']:.0f}% ROI)")
                        print(f"    {opp['title'][:80]}")
                        print(f"    {opp['url']}")
                        vu = list(opp.get("listing_image_urls") or [])
                        if opp.get("image_url") and opp["image_url"] not in vu:
                            vu.insert(0, opp["image_url"])
                        nid = None
                        if "/itm/" in (opp.get("url") or ""):
                            tail = opp["url"].split("/itm/", 1)[-1].split("?")[0]
                            nid = tail.strip() or None
                        if (
                            opp.get("flagged")
                            and len(vision_post_pipeline_queue) < _VISION_Q_MAX
                        ):
                            vision_post_pipeline_queue.append(
                                {
                                    "reason": "bin_tertiary_visual_vs_scp",
                                    "pipeline_card": label,
                                    "scp_price": float(opp["scp_price"]),
                                    "buy_price": float(opp["buy_price"]),
                                    "ebay_item_id": nid,
                                    "title": (opp.get("title") or "")[:240],
                                    "image_urls": vu[:15],
                                    "note": "BIN 30–50% of SCP — verify listing photo matches SCP card identity",
                                }
                            )
                            if nid:
                                vision_seen_ids.add(nid)
                        if (
                            args.dev_vision_queue_pass
                            and nid
                            and nid not in vision_seen_ids
                            and len(vision_post_pipeline_queue) < _VISION_Q_MAX
                        ):
                            vision_seen_ids.add(nid)
                            vision_post_pipeline_queue.append(
                                {
                                    "reason": "dev_identity_listing_queue",
                                    "pipeline_card": label,
                                    "scp_price": float(opp["scp_price"]),
                                    "buy_price": float(opp["buy_price"]),
                                    "ebay_item_id": nid,
                                    "title": (opp.get("title") or "")[:240],
                                    "image_urls": vu[:15],
                                    "note": "Dev: multimodal / CE check listing vs SCP identity",
                                }
                            )
                        all_opportunities.append({
                            'card': label,
                            'scp_title': var['title'],
                            'scp_url': var.get('scp_url'),
                            'grade_9': var.get('grade_9'),
                            'psa_10': var.get('psa_10'),
                            '_pipeline_sport': ply_sport,
                            '_price_reconciliation': var.get('_price_reconciliation'),
                            '_scp_price_raw': var.get('_scp_price_raw'),
                            **opp
                        })
                else:
                    print(f"  No opportunities")

                ebay_variation_stats.append({
                    'idx': i,
                    'card_label': label[:200],
                    'query': (query or '')[:240],
                    'scp_price': float(var['price']),
                    'listings_fetched': int(ebay_meta.get('listings_fetched') or 0),
                    'opportunities_raw': int(ebay_meta.get('opportunities_raw') or 0),
                    'passed_profit_roi': len(good_opps),
                    'ebay_error': bool(ebay_meta.get('ebay_error')),
                    'cache_hit': bool(ebay_meta.get('cache_hit')),
                })

                print()
                time.sleep(2)
        finally:
            if recon_db is not None:
                recon_db.close()
            cache_db.close()

        # Summary
        print("=" * 80)
        bin_count = sum(1 for o in all_opportunities if o.get('listing_type') != 'auction')
        auction_count = len(all_opportunities) - bin_count
        print(f"RESULTS: {len(all_opportunities)} opportunities found ({bin_count} BIN, {auction_count} Auction)")
        if vision_post_pipeline_queue:
            print(
                f"Vision follow-up sample: {len(vision_post_pipeline_queue)} listing(s) "
                f"(job results_summary.vision_post_pipeline_queue_sample — run vision_retry after pipeline; "
                f"does not gate ingest)"
            )
        print("=" * 80)

        if all_opportunities:
            all_opportunities.sort(key=lambda x: x['profit'], reverse=True)

            for i, opp in enumerate(all_opportunities[:30], 1):
                tag = '[AUCTION]' if opp.get('listing_type') == 'auction' else '[BIN]'
                print(f"\n{i}. {tag} {opp['card']}")
                print(f"   SCP: {opp['scp_title']}")
                print(f"   Buy: ${opp['buy_price']:.2f} | SCP Market: ${opp['scp_price']:.2f} | Profit: ${opp['profit']:.2f} ({opp['roi']:.0f}% ROI)")
                print(f"   {opp['title'][:100]}")
                print(f"   {opp['url']}")

        flagged_count = sum(1 for o in all_opportunities if o.get('flagged'))

        _flush_listing_skips()

        # Store in database (single transaction: cancel/kill before commit leaves old BIN rows intact)
        db = SessionLocal()
        try:
            bin_type_filter = (Opportunity.listing_type == 'buy_it_now') | (Opportunity.listing_type.is_(None))
            if args.bin_replace_scope == 'shard_players':
                shard_names = [p.strip() for p in args.players.split(',') if p.strip()]
                n_del = (
                    db.query(Opportunity)
                    .filter(bin_type_filter, Opportunity.player_name.in_(shard_names))
                    .delete(synchronize_session=False)
                )
                print(f"\nBIN replace scope=shard_players: removed {n_del} prior row(s) for {len(shard_names)} player(s).")
            else:
                db.query(Opportunity).filter(bin_type_filter).delete(synchronize_session=False)

            for opp in all_opportunities:
                # Parse card label: "Player Year Set #Number [Parallel]"
                parts = opp['card'].split()
                # Extract year (first 4-digit number)
                opp_year = None
                for p in parts:
                    if p.isdigit() and len(p) == 4:
                        opp_year = int(p)
                        break

                # Extract parallel from [brackets] in card label
                import re as _re
                par_match = _re.search(r'\[([^\]]+)\]', opp['card'])
                opp_parallel = par_match.group(1) if par_match else None

                # Extract card number from #xxx in card label
                num_match = _re.search(r'#(\S+)', opp['card'])
                opp_number = num_match.group(1) if num_match else None
                # Strip trailing [parallel] from number
                if opp_number and '[' in opp['card']:
                    opp_number = opp_number.rstrip(']').split('[')[0].strip()

                # Extract player name (everything before the year)
                player = opp['card'].split(str(opp_year))[0].strip() if opp_year else opp['card']

                # Extract set name (between year and #number or [parallel])
                set_name = None
                if opp_year:
                    after_year = opp['card'].split(str(opp_year), 1)[1].strip()
                    # Remove #number and [parallel]
                    set_name = _re.sub(r'#\S+', '', after_year)
                    set_name = _re.sub(r'\[.*?\]', '', set_name).strip()

                numeric_id = opp['url'].split('/itm/')[-1] if '/itm/' in opp['url'] else None

                vd: dict = {'schema': 1, 'pipeline': 'bin'}
                pr = opp.get('_price_reconciliation')
                if pr:
                    vd['pre_ebay_reconciliation'] = pr
                if opp.get('_scp_price_raw') is not None:
                    vd['scp_price_raw'] = float(opp['_scp_price_raw'])
                reconciled = bool(pr and pr.get('action') not in (None, 'keep_scp'))
                price_src = 'reconciled' if reconciled else 'scp'

                row = Opportunity(
                    player_name=player,
                    card_year=opp_year,
                    card_set=set_name,
                    card_number=opp_number,
                    parallel=opp_parallel,
                    scp_title=opp.get('scp_title'),
                    scp_price=opp['scp_price'],
                    scp_url=opp.get('scp_url'),
                    scp_grade_9=opp.get('grade_9'),
                    scp_psa_10=opp.get('psa_10'),
                    buy_price=opp['buy_price'],
                    profit=opp['profit'],
                    roi=opp['roi'],
                    ebay_title=opp['title'],
                    ebay_url=opp['url'],
                    ebay_item_id=numeric_id,
                    image_url=opp.get('image_url'),
                    listing_image_urls=opp.get('listing_image_urls') or None,
                    listing_type=opp.get('listing_type', 'buy_it_now'),
                    flagged=opp.get('flagged', False),
                    verification_status='pending',
                    verification_detail=vd,
                    sport=(opp.get('_pipeline_sport') or 'Baseball'),
                    price_source=price_src,
                    scan_id=tracker.run_id
                )
                db.add(row)

            db.commit()
            print(f"\nStored {len(all_opportunities)} opportunities in database.")
        except Exception as e:
            db.rollback()
            log.error(f'Failed to store opportunities: {e}', category='db_write_error')
            tracker.fail(f'db_write_error: {e}')
            sys.exit(1)
        finally:
            db.close()

        total_listings = sum(s['listings_fetched'] for s in ebay_variation_stats)
        variations_with_hits = sum(1 for s in ebay_variation_stats if s['passed_profit_roi'] > 0)
        summary = {
            'players': len(players),
            'variations_checked': len(all_variations),
            'opportunities_found': len(all_opportunities),
            'flagged_suspicious': flagged_count,
            'vision_post_pipeline_queue_sample': vision_post_pipeline_queue,
            'ebay_listings_fetched_total': total_listings,
            'variations_with_opportunities': variations_with_hits,
            'ebay_variation_stats': ebay_variation_stats,
            'skip_auction_chain': bool(args.skip_auction_chain),
            'sport': args.sport,
            'dynamic_seed_limit': dyn_limit,
            'max_ebay_variations_cap': args.max_ebay_variations or None,
            'bin_replace_scope': args.bin_replace_scope,
        }
        log.info('Pipeline complete', context=summary)
        tracker.complete(summary=summary)

        # Self-pruning: clean stale data if it's been >24h
        run_if_stale()

        # Run auction pipeline automatically (optional separate CI job: --skip-auction-chain)
        if args.skip_auction_chain:
            print("\n[--skip-auction-chain] Skipping find_auction_opportunities.py (run auction workflow separately).\n")
        else:
            print("\n" + "=" * 80)
            print("STARTING AUCTION PIPELINE...")
            print("=" * 80 + "\n")
            import os
            import subprocess
            repo_root = os.path.dirname(os.path.abspath(__file__))
            auction_cmd = [
                'python3', 'find_auction_opportunities.py',
                '--hours', '48',
                '--min-profit', str(args.min_profit),
                '--max-budget', str(args.max_budget),
                '--sport', str(args.sport).lower() if str(args.sport).lower() != 'all' else 'baseball',
            ]
            subprocess.run(auction_cmd, cwd=repo_root, check=False)

    except Exception as e:
        log.error(f'Pipeline failed: {e}', category='pipeline_crash', context={
            'players_attempted': len(players) if players else len(player_rows),
        })
        tracker.fail(str(e))
        raise
    finally:
        try:
            _flush_listing_skips()
        except Exception:
            pass
        try:
            skip_db.close()
        except Exception:
            pass
