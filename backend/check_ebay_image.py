"""Test: Search eBay using the same URL the opportunity generates, find matching listings."""
import json
import urllib.request
import requests
from backend.scrapers.ebay_scraper import EbayScraper

s = EbayScraper()
s.headers['Authorization'] = f'Bearer {s.token_manager.get_token()}'  

# Get the opportunity from the API
resp = urllib.request.urlopen("http://localhost:8000/api/opportunities")
data = json.loads(resp.read())

# Find the specific opportunity (pass card name as arg or default)
import sys
search_name = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else 'Mookie Betts'

opp = None
for o in data['opportunities']:
    if search_name.lower() in f"{o['card_year']} {o['card_set']} {o['player_name']}".lower():
        opp = o
        break

if not opp:
    print(f"No opportunity found matching '{search_name}'")
    avail = [f"{o['card_year']} {o['card_set']} {o['player_name']}" for o in data['opportunities']]
    print(f"Available: {avail}")
    exit(1)

print(f"OPPORTUNITY: {opp['card_year']} {opp['card_set']} {opp['player_name']} {opp['parallel']}")
print(f"  Buy at: ${opp['arbitrage']['buy_price']:.2f}")
print(f"  Sell at: ${opp['arbitrage']['sell_price']:.2f}")
print(f"  Profit: ${opp['arbitrage']['net_profit']:.2f} ({opp['arbitrage']['roi']:.0f}% ROI)")
print(f"  eBay URL: {opp['arbitrage']['ebay_url']}")
print()

# Now search eBay with the same query the opportunity would use
search_parts = []
if opp['card_year']: search_parts.append(str(opp['card_year']))
if opp['card_set']: search_parts.append(opp['card_set'])
search_parts.append(opp['player_name'])
if opp.get('card_number'): search_parts.append(f"#{opp['card_number']}")
if opp['parallel'] and opp['parallel'] != 'Base': search_parts.append(opp['parallel'])
query = ' '.join(search_parts)

print(f"SEARCHING EBAY: {query}")
print(f"{'='*70}")

resp = requests.get(
    s.base_url + '/item_summary/search',
    headers=s.headers,
    params={'q': query, 'sort': 'price', 'limit': 15},
    timeout=30
)

if resp.status_code != 200:
    print(f"Error: {resp.status_code}")
    exit(1)

results = resp.json()
print(f"Total results: {results.get('total', '?')}\n")

buy_price = opp['arbitrage']['buy_price']
sell_price = opp['arbitrage']['sell_price']
fee_rate = 0.13

match_found = False
for item in results.get('itemSummaries', []):
    title = item.get('title', '')
    price = float(item.get('price', {}).get('value', 0))
    buying = item.get('buyingOptions', [])
    url = item.get('itemWebUrl', '')
    info = s._extract_card_info(title, item.get('condition'))
    
    # Check if this matches our opportunity
    set_match = info.get('card_set', '').lower() == opp['card_set'].lower()
    parallel_match = (info.get('parallel', 'Base')) == opp['parallel']
    year_match = info.get('card_year') == opp['card_year']
    grade_raw = not info.get('grade_company')
    
    net_profit = sell_price * (1 - fee_rate) - price
    profitable = net_profit >= 3
    
    # Verdict
    if set_match and parallel_match and year_match and grade_raw and profitable:
        verdict = "BUY"
        match_found = True
    elif set_match and parallel_match and year_match and grade_raw:
        verdict = "MATCH (no profit)"
    elif year_match and opp['player_name'].split()[-1].lower() in title.lower():
        verdict = "PARTIAL"
    else:
        verdict = "SKIP"
    
    print(f"  [{verdict:16s}] ${price:.2f} | {title[:70]}")
    print(f"    Set: {info.get('card_set')} | Parallel: {info.get('parallel')} | Grade: {info.get('grade_company') or 'Raw'}")
    if verdict == 'BUY':
        print(f"    >>> NET PROFIT: ${net_profit:.2f} | URL: {url[:90]}")
    print()
