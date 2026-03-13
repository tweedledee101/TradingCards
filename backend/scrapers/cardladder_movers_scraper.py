"""
Card Ladder Movers Scraper

Scrapes Card Ladder's "Movers" page to discover trending cards.
Provides player names, price velocity, and card details for automated discovery.

Data Source: https://www.cardladder.com/movers
Update Frequency: Daily at 1 AM

Usage:
    scraper = CardLadderMoversScraper()
    movers = scraper.get_top_movers(limit=50)
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from typing import List, Dict
from datetime import datetime
import logging
import time

logger = logging.getLogger(__name__)


class CardLadderMoversScraper:
    """Scrape Card Ladder movers page for trending cards"""
    
    MOVERS_URL = "https://www.cardladder.com/movers"
    
    def __init__(self, headless: bool = True):
        """
        Initialize scraper
        
        Args:
            headless: Run browser in headless mode (default: True)
        """
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
    
    def get_top_movers(self, limit: int = 50, time_period: str = "24h") -> List[Dict]:
        """
        Get top gaining cards from Card Ladder movers
        
        Args:
            limit: Maximum number of cards to return
            time_period: Time period for price change (24h, 7d, 30d)
            
        Returns:
            List of discovered cards with metadata
            
        Example:
            >>> scraper = CardLadderMoversScraper()
            >>> movers = scraper.get_top_movers(limit=50)
            >>> print(f"Found {len(movers)} trending cards")
        """
        try:
            self._init_driver()
            logger.info(f"Fetching Card Ladder movers (limit: {limit})...")
            
            # Load movers page
            self.driver.get(self.MOVERS_URL)
            
            # Wait for cards to load
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "card-item")))
            
            # Allow dynamic content to load
            time.sleep(2)
            
            # Extract card data
            movers = []
            card_elements = self.driver.find_elements(By.CLASS_NAME, "card-item")[:limit]
            
            logger.info(f"Found {len(card_elements)} card elements")
            
            for i, card_elem in enumerate(card_elements, 1):
                try:
                    card_data = self._parse_card_element(card_elem)
                    if card_data:
                        movers.append(card_data)
                        
                        if i % 10 == 0:
                            logger.info(f"  Parsed {i}/{len(card_elements)} cards")
                
                except Exception as e:
                    logger.warning(f"Error parsing card {i}: {e}")
                    continue
            
            logger.info(f"Successfully extracted {len(movers)} trending cards")
            return movers
            
        except Exception as e:
            logger.error(f"Error scraping Card Ladder movers: {e}")
            return []
        
        finally:
            if self.driver:
                self.driver.quit()
    
    def _parse_card_element(self, element) -> Dict:
        """
        Parse individual card element
        
        Args:
            element: Selenium WebElement for card
            
        Returns:
            Dictionary with card data or None if parsing fails
        """
        try:
            # Extract player name (adjust selectors based on actual site structure)
            player_name = element.find_element(By.CLASS_NAME, "player-name").text.strip()
            
            # Extract card details
            card_title = element.find_element(By.CLASS_NAME, "card-title").text.strip()
            
            # Extract price velocity
            price_change = element.find_element(By.CLASS_NAME, "price-change").text.strip()
            price_velocity = self._parse_price_change(price_change)
            
            # Extract current price
            current_price = element.find_element(By.CLASS_NAME, "current-price").text.strip()
            avg_price = self._parse_price(current_price)
            
            # Extract year and set from title
            card_year, card_set = self._parse_card_details(card_title)
            
            # Detect sport
            sport = self._detect_sport(card_title)
            
            # Calculate discovery score
            discovery_score = self._calculate_discovery_score(price_velocity, avg_price)
            
            return {
                'player_name': player_name,
                'sport': sport,
                'card_year': card_year,
                'card_set': card_set,
                'price_velocity': price_velocity,
                'avg_price': avg_price,
                'discovery_score': discovery_score,
                'discovered_at': datetime.now().isoformat(),
                'source': 'cardladder_movers'
            }
        
        except Exception as e:
            logger.debug(f"Error parsing card element: {e}")
            return None
    
    def _parse_price_change(self, price_change_text: str) -> float:
        """Parse price change percentage"""
        try:
            # Remove % and + signs, convert to float
            clean_text = price_change_text.replace('%', '').replace('+', '').strip()
            return float(clean_text)
        except:
            return 0.0
    
    def _parse_price(self, price_text: str) -> float:
        """Parse price string to float"""
        try:
            # Remove $ and commas
            clean_text = price_text.replace('$', '').replace(',', '').strip()
            return float(clean_text)
        except:
            return 0.0
    
    def _parse_card_details(self, title: str) -> tuple:
        """Extract year and set from card title"""
        import re
        
        # Extract year (4 digits)
        year_match = re.search(r'\b(19|20)\d{2}\b', title)
        year = int(year_match.group()) if year_match else None
        
        # Extract set (common patterns)
        sets = ['Prizm', 'Select', 'Optic', 'Bowman', 'Topps', 'Mosaic', 'Donruss', 'Chronicles']
        card_set = 'Unknown'
        
        for set_name in sets:
            if set_name.lower() in title.lower():
                card_set = set_name
                break
        
        return year, card_set
    
    def _detect_sport(self, title: str) -> str:
        """Detect sport from card title"""
        title_lower = title.lower()
        
        if any(word in title_lower for word in ['nba', 'basketball']):
            return 'Basketball'
        elif any(word in title_lower for word in ['mlb', 'baseball']):
            return 'Baseball'
        elif any(word in title_lower for word in ['nfl', 'football']):
            return 'Football'
        elif any(word in title_lower for word in ['nhl', 'hockey']):
            return 'Hockey'
        else:
            return 'Unknown'
    
    def _calculate_discovery_score(self, price_velocity: float, avg_price: float) -> float:
        """
        Calculate discovery score (0-100)
        
        Scoring:
        - Velocity: 0-60 points (higher velocity = higher score)
        - Price range: 0-40 points (sweet spot $50-$500)
        """
        # Velocity score (0-60)
        velocity_score = min(abs(price_velocity) / 100 * 60, 60)
        
        # Price score (0-40)
        if 50 <= avg_price <= 500:
            price_score = 40
        elif 25 <= avg_price < 50 or 500 < avg_price <= 1000:
            price_score = 30
        elif 10 <= avg_price < 25 or 1000 < avg_price <= 2000:
            price_score = 20
        else:
            price_score = 10
        
        total_score = velocity_score + price_score
        return round(total_score, 2)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    scraper = CardLadderMoversScraper(headless=False)
    movers = scraper.get_top_movers(limit=20)
    
    print(f"\nTop 20 Card Ladder Movers:\n")
    for i, card in enumerate(movers, 1):
        print(f"{i}. {card['player_name']} {card['card_year']} {card['card_set']}")
        print(f"   Score: {card['discovery_score']} | Velocity: +{card['price_velocity']}% | "
              f"Price: ${card['avg_price']:.2f}\n")
