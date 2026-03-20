#!/usr/bin/env python3
"""
SCP-to-eBay Opportunity Pipeline

1. Scrape SportsCardsPro for full player catalog (all variations + prices)
2. Filter to profitable variations within budget
3. Search eBay for active listings below SCP market price
4. Show opportunities with buy links

Usage:
    python3 find_opportunities.py --max-budget 200 --min-profit 5 --min-roi 20
    python3 find_opportunities.py --players "Colton Cowser,Bobby Witt Jr"
"""
import argparse
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from backend.scrapers.ebay_scraper import EbayScraper
from backend.utils.job_tracker import JobTracker
from backend.utils.logger import get_logger
from backend.utils.retention import run_if_stale
from backend.utils.database import SessionLocal
from backend.models import Opportunity

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


def find_ebay_opportunities(scraper, variation, max_budget):
    """Search eBay for listings below SCP price"""
    query = build_ebay_query(variation)
    scp_price = variation['price']

    try:
        listings = scraper.get_active_listings(query)
    except Exception as e:
        log.error(f'eBay search failed: {e}', category='ebay_api_error', context={
            'player': variation['player'], 'query': query
        })
        return query, []

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
                continue

            parallel = variation.get('parallel', 'Base')
            if parallel != 'Base':
                parallel_keywords = parallel.lower().split()
                if not any(kw in title_lower for kw in parallel_keywords):
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
                continue

            # Reprint / replica detection
            if any(rp in title_lower for rp in REPRINT_PATTERNS):
                log.warn('Reprint/replica detected', category='reprint_match', context={
                    'scp_card': f"{variation['player']} {variation['set_name']} #{card_number} [{variation.get('parallel', 'Base')}]",
                    'ebay_title': title, 'buy_price': price, 'scp_price': scp_price
                })
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
                continue

            profit = scp_price - price - (price * FEE_RATE)
            roi = (profit / price) * 100

            if profit <= 0 or roi <= 0:
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

            opportunities.append({
                'title': listing.get('title', 'Unknown'),
                'buy_price': price,
                'scp_price': scp_price,
                'profit': profit,
                'roi': roi,
                'url': url,
                'image_url': listing.get('image_url'),
                'flagged': flagged,
                'listing_type': 'auction' if is_auction else 'buy_it_now'
            })
        except (ValueError, TypeError):
            continue

    return query, opportunities


def get_hot_players(limit=40):
    """Get players with most sales volume from database"""
    from backend.utils.database import SessionLocal
    from backend.models import Card, Sale
    from sqlalchemy import func
    from datetime import datetime, timedelta

    db = SessionLocal()
    cutoff = datetime.now() - timedelta(days=30)

    players = db.query(
        Card.player_name,
        func.count(Sale.id).label('sales')
    ).join(Sale).filter(
        Sale.sale_date >= cutoff
    ).group_by(
        Card.player_name
    ).order_by(
        func.count(Sale.id).desc()
    ).limit(limit).all()

    db.close()
    return [p.player_name for p in players]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SCP-to-eBay Opportunity Pipeline')
    parser.add_argument('--max-budget', type=float, default=200, help='Max buy price (default: $200)')
    parser.add_argument('--min-profit', type=float, default=5, help='Min profit after fees (default: $5)')
    parser.add_argument('--min-roi', type=float, default=20, help='Min ROI %% (default: 20)')
    parser.add_argument('--min-scp-price', type=float, default=20, help='Min SCP price to consider (default: $20)')
    parser.add_argument('--max-scp-price', type=float, default=1000, help='Max SCP price (default: $1000)')
    parser.add_argument('--players', type=str, default=None, help='Comma-separated player names')
    parser.add_argument('--top-players', type=int, default=40, help='Number of hot players (default: 40)')
    args = parser.parse_args()

    print("=" * 80)
    print("SCP-TO-EBAY OPPORTUNITY PIPELINE")
    print("=" * 80)
    print(f"\nBudget: ${args.max_budget:.0f} max buy | Min Profit: ${args.min_profit:.0f} | Min ROI: {args.min_roi:.0f}%")
    print(f"SCP Price Range: ${args.min_scp_price:.0f}-${args.max_scp_price:.0f}\n")

    # Step 1: Get players
    if args.players:
        players = [p.strip() for p in args.players.split(',')]
    else:
        print("Finding hot players by sales volume...")
        players = get_hot_players(limit=args.top_players)

    print(f"Players: {', '.join(players)}\n")

    log.info('Pipeline starting', context={
        'players': len(players), 'max_budget': args.max_budget,
        'min_profit': args.min_profit, 'min_roi': args.min_roi
    })

    # Job tracking
    tracker = JobTracker('opportunity_finder')
    tracker.start(
        total=len(players),
        parameters={'max_budget': args.max_budget, 'min_profit': args.min_profit,
                    'min_roi': args.min_roi, 'players': players}
    )

    try:
        # Step 2: Start Selenium for SCP
        print("Starting browser for SportsCardsPro...")
        opts = Options()
        opts.add_argument('--headless')
        # Auto-detect Firefox binary (local vs GitHub Actions)
        import shutil
        for firefox_path in ['/usr/lib/firefox/firefox', '/usr/bin/firefox-esr', '/usr/bin/firefox']:
            if shutil.which(firefox_path) or __import__('os').path.exists(firefox_path):
                opts.binary_location = firefox_path
                break
        service = Service(executable_path=shutil.which('geckodriver') or '/usr/local/bin/geckodriver')
        driver = webdriver.Firefox(options=opts, service=service)

        # Step 3: Get SCP catalogs
        all_variations = []
        for i, player in enumerate(players, 1):
            print(f"\n[SCP {i}/{len(players)}] {player}")
            catalog = get_scp_catalog(driver, player)
            print(f"  {len(catalog)} total variations found")

            if not catalog:
                log.warn('SCP returned 0 variations', category='scp_empty', context={
                    'player': player
                })

            affordable = [v for v in catalog if args.min_scp_price <= v['price'] <= args.max_scp_price]

            # Filter out cards that rarely sell -- dead money
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

            all_variations.extend(affordable)
            tracker.update(processed=i)
            time.sleep(2)

        driver.quit()
        print(f"\n{'=' * 80}")
        print(f"Total variations to check on eBay: {len(all_variations)}")
        print(f"{'=' * 80}\n")

        if not all_variations:
            print("No variations found in price range. Try adjusting --min-scp-price or --max-scp-price.")
            tracker.complete(summary={'variations': 0, 'opportunities': 0})
            exit()

        # Step 4: Search eBay for each variation
        scraper = EbayScraper()
        all_opportunities = []

        for i, var in enumerate(all_variations, 1):
            label = f"{var['player']} {var['year']} {var['set_name']} #{var['card_number']} [{var['parallel']}]"
            print(f"[eBay {i}/{len(all_variations)}] {label}")
            print(f"  SCP: ${var['price']:.2f}")

            query, opps = find_ebay_opportunities(scraper, var, max_budget=args.max_budget)
            print(f"  Query: {query}")

            good_opps = [o for o in opps if o['profit'] >= args.min_profit and o['roi'] >= args.min_roi]

            if good_opps:
                print(f"  {len(good_opps)} opportunities found!")
                for opp in good_opps:
                    tag = '[AUCTION]' if opp.get('listing_type') == 'auction' else '[BIN]'
                    print(f"    {tag} ${opp['buy_price']:.2f} -> ${opp['scp_price']:.2f} = ${opp['profit']:.2f} profit ({opp['roi']:.0f}% ROI)")
                    print(f"    {opp['title'][:80]}")
                    print(f"    {opp['url']}")
                    all_opportunities.append({
                        'card': label,
                        'scp_title': var['title'],
                        'scp_url': var.get('scp_url'),
                        'grade_9': var.get('grade_9'),
                        'psa_10': var.get('psa_10'),
                        **opp
                    })
            else:
                print(f"  No opportunities")

            print()
            time.sleep(2)

        # Summary
        print("=" * 80)
        bin_count = sum(1 for o in all_opportunities if o.get('listing_type') != 'auction')
        auction_count = len(all_opportunities) - bin_count
        print(f"RESULTS: {len(all_opportunities)} opportunities found ({bin_count} BIN, {auction_count} Auction)")
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

        # Store in database
        db = SessionLocal()
        try:
            # Clear previous scan results
            db.query(Opportunity).delete()
            db.commit()

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
                    listing_type=opp.get('listing_type', 'buy_it_now'),
                    flagged=opp.get('flagged', False),
                    scan_id=tracker.run_id
                )
                db.add(row)

            db.commit()
            print(f"\nStored {len(all_opportunities)} opportunities in database.")
        except Exception as e:
            db.rollback()
            log.error(f'Failed to store opportunities: {e}', category='db_write_error')
        finally:
            db.close()

        summary = {
            'players': len(players),
            'variations_checked': len(all_variations),
            'opportunities_found': len(all_opportunities),
            'flagged_suspicious': flagged_count
        }
        log.info('Pipeline complete', context=summary)
        tracker.complete(summary=summary)

        # Self-pruning: clean stale data if it's been >24h
        run_if_stale()

    except Exception as e:
        log.error(f'Pipeline failed: {e}', category='pipeline_crash', context={
            'players_attempted': len(players)
        })
        tracker.fail(str(e))
        raise
