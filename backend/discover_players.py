"""
Volume-Based Player Discovery

Searches eBay sold listings for a broad seed list of players,
counts actual sales per player, and ranks by volume.

The seed list is large (100+ players) but we only use 1 API call each.
The TOP players by volume become our targets.

This runs weekly to refresh the target list.

Usage:
    /usr/bin/python3 -m backend.discover_players
    /usr/bin/python3 -m backend.discover_players --limit 20 --days 7
"""

import sys
import os
import time
from datetime import datetime
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.scrapers.ebay_scraper import EbayScraper
import requests

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


def discover_top_players(days: int = 7, limit: int = 20, max_queries: int = None, sport: str = None) -> List[Dict]:
    """
    Discover top players by eBay sales volume.
    
    Searches each seed player, counts total listings, ranks by volume.
    
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
    
    print(f"Discovering top players from {len(players_to_search)} seed players ({days} days)...")
    print(f"API calls needed: {len(players_to_search)} (1 per player, limit=1)")
    print("=" * 70)
    
    results = []
    
    from datetime import timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    for i, (player_name, sport) in enumerate(players_to_search, 1):
        print(f"  [{i}/{len(players_to_search)}] {player_name}...", end=" ", flush=True)
        
        try:
            scraper.headers['Authorization'] = f'Bearer {scraper.token_manager.get_token()}'
            params = {
                'q': f'{player_name} card',
                'filter': f'buyingOptions:{{AUCTION|FIXED_PRICE}},itemEndDate:[{start_date.isoformat()}..{end_date.isoformat()}]',
                'limit': 1
            }
            r = requests.get(
                f'{scraper.base_url}/item_summary/search',
                headers=scraper.headers,
                params=params,
                timeout=10
            )
            
            if r.status_code == 401:
                scraper.token_manager._refresh_token()
                scraper.headers['Authorization'] = f'Bearer {scraper.token_manager.get_token()}'
                r = requests.get(
                    f'{scraper.base_url}/item_summary/search',
                    headers=scraper.headers,
                    params=params,
                    timeout=10
                )
            
            data = r.json()
            total = data.get('total', 0)
            print(f"{total:,} listings")
            
            if total == 0:
                continue
            
            results.append({
                'player_name': player_name,
                'sport': sport,
                'sales_volume': total,
            })
            
            time.sleep(0.3)
            
        except Exception as e:
            print(f"ERROR: {e}")
            continue
    
    # Rank by volume
    results.sort(key=lambda x: x['sales_volume'], reverse=True)
    
    print(f"\nSearched {len(players_to_search)} players, {len(results)} had listings")
    
    return results[:limit]


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
