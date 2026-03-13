"""
PWCC Marketplace Scraper

Scrapes PWCC auction results to discover trending cards.
PWCC is a premium auction house - high prices indicate strong demand.

Data Source: https://www.pwccmarketplace.com/sold-lots
Update Frequency: Daily

Usage:
    scraper = PWCCScraper()
    results = scraper.get_recent_sales(days=7)
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from typing import List, Dict
from datetime import datetime, timedelta
import logging
import time
import re

logger = logging.getLogger(__name__)


class PWCCScraper:
    """Scrape PWCC auction results for trending cards"""
    
    BASE_URL = "https://www.pwccmarketplace.com/sold-lots"
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
    
    def _init_driver(self):
        """Initialize Chrome WebDriver"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
    
    def get_recent_sales(self, days: int = 7, limit: int = 200) -> List[Dict]:
        """
        Get recent PWCC auction results
        
        Args:
            days: Look back period
            limit: Maximum results to return
            
        Returns:
            List of sales with player names and prices
        """
        try:
            self._init_driver()
            logger.info(f"Fetching PWCC sales (last {days} days, limit: {limit})...")
            
            self.driver.get(self.BASE_URL)
            
            # Wait for results to load
            wait = WebDriverWait(self.driver, 15)
            time.sleep(3)
            
            sales = []
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Scroll to load more results
            for _ in range(5):  # Load ~200 results
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            # Find all sale items
            items = self.driver.find_elements(By.CSS_SELECTOR, "[class*='lot'], [class*='item'], [class*='card']")
            
            logger.info(f"Found {len(items)} potential items")
            
            for i, item in enumerate(items[:limit], 1):
                try:
                    sale_data = self._parse_sale_item(item)
                    if sale_data and sale_data.get('sale_date'):
                        if sale_data['sale_date'] >= cutoff_date:
                            sales.append(sale_data)
                    
                    if i % 50 == 0:
                        logger.info(f"  Parsed {i}/{min(len(items), limit)} items")
                
                except Exception as e:
                    logger.debug(f"Error parsing item {i}: {e}")
                    continue
            
            logger.info(f"Extracted {len(sales)} sales from last {days} days")
            return sales
            
        except Exception as e:
            logger.error(f"Error scraping PWCC: {e}")
            return []
        
        finally:
            if self.driver:
                self.driver.quit()
    
    def _parse_sale_item(self, element) -> Dict:
        """Parse individual sale item"""
        try:
            # Get title/description
            title = element.text.strip()
            if not title or len(title) < 10:
                return None
            
            # Extract player name (first 2-3 words before year/set)
            player_name = self._extract_player_name(title)
            if not player_name:
                return None
            
            # Extract price
            price_match = re.search(r'\$[\d,]+(?:\.\d{2})?', title)
            price = float(price_match.group().replace('$', '').replace(',', '')) if price_match else 0
            
            if price < 10:  # Skip low-value items
                return None
            
            # Extract year
            year_match = re.search(r'\b(19|20)\d{2}\b', title)
            year = int(year_match.group()) if year_match else None
            
            # Extract set
            card_set = self._extract_set(title)
            
            # Detect sport
            sport = self._detect_sport(title)
            
            # Check if rookie
            is_rookie = bool(re.search(r'\brc\b|\brookie\b', title.lower()))
            
            # Check if graded
            graded = bool(re.search(r'\bpsa\b|\bbgs\b|\bsgc\b', title.lower()))
            
            return {
                'player_name': player_name,
                'sport': sport,
                'card_year': year,
                'card_set': card_set,
                'price': price,
                'is_rookie': is_rookie,
                'graded': graded,
                'title': title,
                'sale_date': datetime.now(),  # PWCC doesn't show exact dates easily
                'source': 'pwcc'
            }
        
        except Exception as e:
            logger.debug(f"Error parsing sale item: {e}")
            return None
    
    def _extract_player_name(self, title: str) -> str:
        """Extract player name from title"""
        # Remove common prefixes
        title = re.sub(r'^\d{4}\s+', '', title)  # Remove year prefix
        
        # Get first 2-3 words before common keywords
        keywords = ['PSA', 'BGS', 'SGC', 'Prizm', 'Select', 'Topps', 'Bowman', 'RC', 'Rookie', 'Auto', 'Patch']
        
        words = title.split()
        player_words = []
        
        for word in words[:5]:  # Check first 5 words
            if any(kw.lower() in word.lower() for kw in keywords):
                break
            if re.match(r'^\d+$', word):  # Skip numbers
                continue
            player_words.append(word)
        
        if len(player_words) >= 2:
            return ' '.join(player_words[:3])  # Max 3 words
        
        return None
    
    def _extract_set(self, title: str) -> str:
        """Extract card set from title"""
        sets = ['Prizm', 'Select', 'Optic', 'Bowman', 'Topps', 'Mosaic', 'Donruss', 'Chronicles', 'Contenders']
        
        for card_set in sets:
            if card_set.lower() in title.lower():
                return card_set
        
        return 'Unknown'
    
    def _detect_sport(self, title: str) -> str:
        """Detect sport from title"""
        title_lower = title.lower()
        
        if any(word in title_lower for word in ['nba', 'basketball']):
            return 'Basketball'
        elif any(word in title_lower for word in ['mlb', 'baseball']):
            return 'Baseball'
        elif any(word in title_lower for word in ['nfl', 'football']):
            return 'Football'
        elif any(word in title_lower for word in ['nhl', 'hockey']):
            return 'Hockey'
        
        # Infer from set
        if any(s in title_lower for s in ['prizm', 'select', 'optic', 'mosaic']):
            return 'Basketball'
        elif any(s in title_lower for s in ['bowman', 'topps chrome']):
            return 'Baseball'
        
        return 'Unknown'


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    scraper = PWCCScraper(headless=False)
    sales = scraper.get_recent_sales(days=7, limit=100)
    
    print(f"\nFound {len(sales)} PWCC sales\n")
    
    # Group by player
    from collections import defaultdict
    by_player = defaultdict(list)
    
    for sale in sales:
        if sale['player_name']:
            by_player[sale['player_name']].append(sale['price'])
    
    # Show top players by sales volume
    top_players = sorted(by_player.items(), key=lambda x: len(x[1]), reverse=True)[:20]
    
    print("Top 20 Players by Sales Volume:\n")
    for i, (player, prices) in enumerate(top_players, 1):
        avg_price = sum(prices) / len(prices)
        print(f"{i}. {player}")
        print(f"   Sales: {len(prices)} | Avg Price: ${avg_price:,.2f} | Total: ${sum(prices):,.2f}\n")
