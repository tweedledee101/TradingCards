#!/usr/bin/env python3
"""Scrape SportsCardsPro for profitable variations of liquid cards"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from backend.utils.database import SessionLocal
from backend.models import Card, Sale
from sqlalchemy import func
from datetime import datetime, timedelta
import time
import re

def extract_parallel(title):
    """Extract parallel name from title like 'Gunnar Henderson [Aqua Lava] #2 /199'"""
    match = re.search(r'\[([^\]]+)\]', title)
    if match:
        return match.group(1)
    return 'Base'

def save_variation_to_db(db, player_name, year, set_name, card_number, parallel, ungraded_price, sport='Baseball'):
    """Save or update card variation in database"""
    try:
        card = db.query(Card).filter(
            Card.player_name == player_name,
            Card.card_year == year,
            Card.card_set == set_name,
            Card.card_number == card_number,
            Card.parallel == parallel
        ).first()
        
        if card:
            card.ungraded_price = ungraded_price
            card.updated_at = datetime.now()
        else:
            card = Card(
                player_name=player_name,
                card_year=year,
                card_set=set_name,
                card_number=card_number,
                parallel=parallel,
                ungraded_price=ungraded_price,
                sport=sport
            )
            db.add(card)
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"    Error saving {parallel}: {e}")
        return False

def get_variations(driver, player_name, year, set_name, card_number, min_price=20):
    """Get variations >$min_price from SportsCardsPro"""
    query = f"{player_name} {year} {set_name} #{card_number}"
    url = f"https://www.sportscardspro.com/search-products?q={query.replace(' ', '+').replace('#', '%23')}&type=prices"
    
    driver.get(url)
    time.sleep(5)
    
    variations = []
    
    # Find all rows in the table
    rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
    
    for row in rows:
        try:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 5:
                continue
            
            # Column 0 = empty/checkbox
            # Column 1 = Title
            # Column 2 = Set
            # Column 3 = Ungraded
            # Column 4 = Grade 9
            # Column 5 = PSA 10
            
            title = cells[1].text.strip()
            ungraded = cells[3].text.strip()
            
            # Skip if no data
            if not title or not ungraded or '$' not in ungraded:
                continue
            
            # Parse price
            price_str = ungraded.replace('$', '').replace(',', '').strip()
            price = float(price_str)
            
            if price >= min_price:
                variations.append({'variation': title, 'ungraded_price': price})
                
        except (ValueError, IndexError, Exception):
            continue
    
    return variations

# Get liquid cards from database
db = SessionLocal()
cutoff = datetime.now() - timedelta(days=14)

liquid_cards = db.query(
    Card.player_name,
    Card.card_year,
    Card.card_set,
    Card.card_number,
    func.count(Sale.id).label('sales')
).join(Sale).filter(
    Card.sport == 'Baseball',
    Card.card_number.isnot(None),
    Sale.sale_date >= cutoff
).group_by(
    Card.player_name,
    Card.card_year,
    Card.card_set,
    Card.card_number
).having(
    func.count(Sale.id) >= 3
).order_by(
    func.count(Sale.id).desc()
).all()

print(f"Found {len(liquid_cards)} liquid cards")
print("=" * 70)

# Setup Chrome with anti-detection
chrome_options = Options()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)
driver = webdriver.Chrome(options=chrome_options)

try:
    for i, card in enumerate(liquid_cards, 1):
        print(f"\n{i}/{len(liquid_cards)} {card.player_name} {card.card_year} {card.card_set} #{card.card_number} ({card.sales} sales)")
        
        variations = get_variations(
            driver,
            card.player_name,
            card.card_year,
            card.card_set,
            card.card_number,
            min_price=20
        )
        
        if len(variations) > 0:
            print(f"  ✓ Found {len(variations)} variations >$20:")
            saved_count = 0
            for v in variations:
                parallel = extract_parallel(v['variation'])
                if save_variation_to_db(db, card.player_name, card.card_year, card.card_set, 
                                       card.card_number, parallel, v['ungraded_price']):
                    saved_count += 1
                    if saved_count <= 10:
                        print(f"    ${v['ungraded_price']:>7.2f} - {v['variation']}")
            
            if len(variations) > 10:
                print(f"    ... and {len(variations) - 10} more")
            print(f"  💾 Saved {saved_count}/{len(variations)} to database")
        else:
            print(f"  ✗ No variations >$20")
        
        time.sleep(2)
finally:
    driver.quit()
    db.close()

print("\n" + "=" * 70)
print("DONE")
