"""
eBay Sold Listings Scraper

Fetches completed sales data from eBay Browse API for trend analysis.
Extracts card details from listing titles and stores in database.

Data Flow:
    eBay API → parse_results() → extract_card_info() → Database

Usage:
    scraper = EbayScraper()
    results = scraper.search_sold_listings("Wembanyama rookie", days_back=7)
"""
import requests
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from backend.config.settings import config

class EbayScraper:
    """
    Scraper for eBay sold listings using Browse API
    
    Attributes:
        base_url: eBay Browse API endpoint
        headers: Authorization headers with OAuth token
    """
    
    def __init__(self):
        from backend.utils.token_manager import token_manager
        self.token_manager = token_manager
        
        # Use sandbox or production based on config
        if config.EBAY_USE_SANDBOX:
            self.base_url = "https://api.sandbox.ebay.com/buy/browse/v1"
            print("🧪 Using eBay SANDBOX (unlimited calls, test data)")
        else:
            self.base_url = "https://api.ebay.com/buy/browse/v1"
            print("🔴 Using eBay PRODUCTION (5,000 calls/day limit)")
        
        self.headers = {
            "Authorization": f"Bearer {self.token_manager.get_token()}",
            "Content-Type": "application/json"
        }
    
    def search_sold_listings(self, query: str, days_back: int = 7, player_name: str = None, sport: str = None) -> List[Dict]:
        """
        Search sold listings for a specific query
        
        Args:
            query: Search term (e.g., "Wembanyama rookie PSA 10")
            days_back: Number of days to look back (default: 7)
            
        Returns:
            List of parsed sale records with card details
            
        Example:
            >>> scraper = EbayScraper()
            >>> sales = scraper.search_sold_listings("Wembanyama 2023 rookie", 7)
            >>> print(f"Found {len(sales)} sales")
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # eBay API filter format
        params = {
            "q": query,
            "filter": f"buyingOptions:{{AUCTION|FIXED_PRICE}},itemEndDate:[{start_date.isoformat()}..{end_date.isoformat()}]",
            "sort": "endTimeSoonest",
            "limit": 200
        }
        
        try:
            # Refresh token if needed
            self.headers["Authorization"] = f"Bearer {self.token_manager.get_token()}"
            
            response = requests.get(
                f"{self.base_url}/item_summary/search",
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            # If 401, force token refresh and retry once
            if response.status_code == 401:
                self.token_manager._refresh_token()  # Force refresh
                self.headers["Authorization"] = f"Bearer {self.token_manager.get_token()}"
                response = requests.get(
                    f"{self.base_url}/item_summary/search",
                    headers=self.headers,
                    params=params,
                    timeout=30
                )
            
            response.raise_for_status()
            time.sleep(0.5)  # Rate limiting: 0.5 second delay between calls
            return self._parse_results(response.json(), player_name, sport)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching eBay data for '{query}': {e}")
            return []
    
    def _parse_results(self, data: dict, player_name: str = None, sport: str = None) -> List[Dict]:
        """
        Parse eBay API response into structured data
        
        Args:
            data: Raw JSON response from eBay API
            
        Returns:
            List of dictionaries with sale and card details
        """
        items = []
        
        for item in data.get('itemSummaries', []):
            title = item.get('title', '')
            if not title:
                continue
            
            # Get player name from title parsing (skip full item details to save API calls)
            ebay_player_name = None
            
            # Extract card details from title
            card_info = self._extract_card_info(title, item.get('condition'))
            
            # Skip if we can't extract required fields
            if not card_info.get('card_year') or not card_info.get('card_set'):
                continue
            
            parsed = {
                'ebay_item_id': item.get('itemId'),
                'title': title,
                'price': float(item.get('price', {}).get('value', 0)),
                'currency': item.get('price', {}).get('currency'),
                'sale_date': item.get('itemEndDate') or datetime.now().isoformat(),  # Fallback to now
                'condition': item.get('condition'),
                'listing_type': 'auction' if 'AUCTION' in item.get('buyingOptions', []) else 'buy_it_now'
            }
            
            # Skip junk data (price < $1)
            if parsed['price'] < 1.0:
                continue
            
            parsed.update(card_info)
            
            # Use eBay's player name if available, otherwise use provided
            if ebay_player_name:
                parsed['player_name'] = ebay_player_name
            elif player_name:
                parsed['player_name'] = player_name
            
            if sport:
                parsed['sport'] = sport
            
            items.append(parsed)
        
        return items
    
    def _extract_card_info(self, title: str, ebay_condition: str = None) -> Dict:
        """
        Extract player name, year, rookie status, grading, parallel from listing title
        
        Uses regex patterns to identify:
        - Rookie cards (RC, rookie)
        - Year (4-digit)
        - Grading company and grade (PSA 10, BGS 9.5, etc.)
        - Parallel type (Silver, Red Ice, Purple Wave, etc.)
        
        Args:
            title: eBay listing title
            
        Returns:
            Dictionary with extracted card attributes
            
        Example:
            >>> info = self._extract_card_info("2023 Panini Prizm Victor Wembanyama Silver RC PSA 10")
            >>> print(info['is_rookie'])  # True
            >>> print(info['grade_value'])  # 10.0
            >>> print(info['parallel'])  # Silver
        """
        title_lower = title.lower()
        
        # Check if rookie card
        is_rookie = bool(re.search(r'\brc\b|\brookie\b', title_lower))
        
        # Extract year (4 digits, 19xx or 20xx)
        year_match = re.search(r'\b(19|20)\d{2}\b', title)
        year = int(year_match.group()) if year_match else None
        
        # Use eBay's condition field to determine if graded
        graded = ebay_condition == 'Graded'
        grade_company = None
        grade_value = None
        
        if graded:
            # PSA grading
            if 'psa' in title_lower:
                grade_company = 'PSA'
                grade_match = re.search(r'psa\s*(\d+(?:\.\d)?)', title_lower)
                if grade_match:
                    val = float(grade_match.group(1))
                    # Valid PSA grades: 1-10
                    if 1 <= val <= 10:
                        grade_value = val
            
            # BGS/Beckett grading
            elif 'bgs' in title_lower or 'beckett' in title_lower:
                grade_company = 'BGS'
                grade_match = re.search(r'(?:bgs|beckett)\s*(\d+(?:\.\d)?)', title_lower)
                if grade_match:
                    val = float(grade_match.group(1))
                    # Valid BGS grades: 1-10
                    if 1 <= val <= 10:
                        grade_value = val
            
            # SGC grading
            elif 'sgc' in title_lower:
                grade_company = 'SGC'
                grade_match = re.search(r'sgc\s*(\d+(?:\.\d)?)', title_lower)
                if grade_match:
                    val = float(grade_match.group(1))
                    # Valid SGC grades: 1-10
                    if 1 <= val <= 10:
                        grade_value = val
        
        # Extract card set (common patterns)
        card_set = self._extract_card_set(title)
        
        # Extract parallel type
        parallel = self._extract_parallel(title)
        
        return {
            'is_rookie': is_rookie,
            'card_year': year,
            'graded': graded,
            'grade_company': grade_company,
            'grade_value': grade_value,
            'card_set': card_set,
            'parallel': parallel
        }
    
    def get_full_item_details(self, item_id: str) -> Optional[Dict]:
        """
        Get full item details including card number and all aspects
        
        Args:
            item_id: eBay item ID (e.g., "v1|123456789|0")
            
        Returns:
            Dictionary with card_number, parallel, grade_company, grade_value, player_name
            
        Example:
            >>> scraper = EbayScraper()
            >>> details = scraper.get_full_item_details("v1|123456789|0")
            >>> print(details['card_number'])  # "150"
        """
        try:
            # Refresh token if needed
            self.headers["Authorization"] = f"Bearer {self.token_manager.get_token()}"
            
            response = requests.get(
                f"{self.base_url}/item/{item_id}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 401:
                self.token_manager._refresh_token()
                self.headers["Authorization"] = f"Bearer {self.token_manager.get_token()}"
                response = requests.get(
                    f"{self.base_url}/item/{item_id}",
                    headers=self.headers,
                    timeout=10
                )
            
            response.raise_for_status()
            time.sleep(0.5)  # Rate limiting
            
            item_data = response.json()
            aspects = item_data.get('localizedAspects', [])
            
            return self._extract_from_aspects(aspects)
            
        except Exception as e:
            print(f"Error fetching full item details for {item_id}: {e}")
            return None
    
    def _extract_from_aspects(self, aspects: List[Dict]) -> Dict:
        """
        Extract card details from eBay's localizedAspects
        
        Args:
            aspects: List of aspect dictionaries from eBay API
            
        Returns:
            Dictionary with extracted card data
        """
        data = {
            'card_number': None,
            'parallel': 'Base',
            'grade_company': None,
            'grade_value': None,
            'player_name': None,
            'card_year': None,
            'card_set': None
        }
        
        for aspect in aspects:
            name = aspect.get('name', '')
            value = aspect.get('value', '')
            
            # Handle both string and list values
            if isinstance(value, list):
                value = value[0] if value else ''
            
            # Card Number
            if name in ['Card Number', 'Card No', 'Card No.']:
                data['card_number'] = str(value)
            
            # Parallel/Variety
            elif name in ['Parallel/Variety', 'Parallel', 'Variety']:
                data['parallel'] = value if value else 'Base'
            
            # Grading
            elif name in ['Professional Grader', 'Grader']:
                data['grade_company'] = value
            elif name == 'Grade':
                try:
                    data['grade_value'] = float(value)
                except (ValueError, TypeError):
                    pass
            
            # Card details
            elif name == 'Player':
                data['player_name'] = value
            elif name == 'Year':
                try:
                    data['card_year'] = int(value)
                except (ValueError, TypeError):
                    pass
            elif name == 'Set':
                data['card_set'] = value
        
        return data
    
    def _get_player_from_product(self, item_id: str) -> Optional[str]:
        """
        DEPRECATED: Use get_full_item_details() instead
        Get player name from full item details
        """
        details = self.get_full_item_details(item_id)
        return details.get('player_name') if details else None
    
    def _extract_player_from_aspects(self, aspects: List[Dict]) -> Optional[str]:
        """
        Extract player name from eBay's localizedAspects field
        
        Args:
            aspects: List of aspect dictionaries from eBay API
            
        Returns:
            Player name or None
        """
        if not aspects:
            return None
        
        # Common aspect names for player
        player_fields = ['Player', 'Player/Athlete', 'Athlete', 'Player Name']
        
        for aspect in aspects:
            aspect_name = aspect.get('name', '')
            if aspect_name in player_fields:
                values = aspect.get('value', '')
                if values:
                    return values if isinstance(values, str) else values[0] if isinstance(values, list) else None
        
        return None
    
    def _extract_card_set(self, title: str) -> Optional[str]:
        """
        Extract card set name from title
        
        Common sets: Prizm, Optic, Select, Topps Chrome, Bowman, etc.
        
        Args:
            title: eBay listing title
            
        Returns:
            Card set name or 'Unknown' if not found
        """
        if not title:
            return 'Unknown'
        
        title_lower = title.lower()
        
        # Common basketball sets
        sets = [
            'prizm', 'optic', 'select', 'mosaic', 'donruss',
            'chronicles', 'hoops', 'revolution', 'contenders'
        ]
        
        # Common baseball sets
        sets.extend([
            'topps chrome', 'bowman chrome', 'topps', 'bowman',
            'stadium club', 'heritage', 'gypsy queen'
        ])
        
        # Check for multi-word sets first (more specific)
        for card_set in ['topps chrome', 'bowman chrome', 'stadium club', 'gypsy queen']:
            if card_set in title_lower:
                return card_set.title()
        
        # Then check single-word sets
        for card_set in sets:
            if card_set in title_lower:
                return card_set.title()
        
        # Fallback: extract brand name (Panini, Topps, Upper Deck, etc.)
        brands = ['panini', 'topps', 'upper deck', 'leaf', 'fleer']
        for brand in brands:
            if brand in title_lower:
                return brand.title()
        
        return 'Unknown'
    
    def _extract_parallel(self, title: str) -> str:
        """
        Extract parallel/variant type from title
        
        Common parallels: Silver, Red Ice, Purple Wave, Orange, Green, etc.
        
        Args:
            title: eBay listing title
            
        Returns:
            Parallel name or 'Base' if not found
        """
        if not title:
            return 'Base'
        
        title_lower = title.lower()
        
        # Prizm parallels (most common)
        prizm_parallels = [
            'red ice', 'purple wave', 'blue ice', 'green ice',
            'orange ice', 'pink ice', 'gold', 'silver', 'ruby wave',
            'tiger stripe', 'choice', 'hyper', 'neon green', 'fast break'
        ]
        
        # Check multi-word parallels first
        for parallel in prizm_parallels:
            if parallel in title_lower:
                return parallel.title()
        
        # Single color parallels
        colors = ['silver', 'gold', 'orange', 'green', 'blue', 'red', 'purple', 'pink']
        for color in colors:
            # Match color as standalone word (not part of player name)
            if re.search(rf'\b{color}\b', title_lower):
                return color.title()
        
        # Numbered parallels
        if re.search(r'/\d+', title):
            return 'Numbered'
        
        # Auto/Autograph
        if 'auto' in title_lower or 'autograph' in title_lower:
            return 'Autograph'
        
        return 'Base'
    
    def get_rookie_cards(self, player_names: List[str], year: int) -> List[Dict]:
        """
        Fetch rookie cards for specific players
        
        Args:
            player_names: List of player names
            year: Rookie year
            
        Returns:
            Combined list of all sales for these rookies
            
        Example:
            >>> scraper = EbayScraper()
            >>> rookies = scraper.get_rookie_cards(["Wembanyama", "Henderson"], 2023)
        """
        all_results = []
        for player in player_names:
            query = f"{player} {year} rookie card"
            results = self.search_sold_listings(query)
            
            # Add player name to each result
            for result in results:
                result['player_name'] = player
            
            all_results.extend(results)
        
        return all_results
    
    def get_active_listings(self, query: str) -> List[Dict]:
        """
        Get current active listings (for velocity calculation)
        
        Args:
            query: Search term
            
        Returns:
            List of active listings with prices
            
        Note:
            Uses different endpoint than sold listings
        """
        params = {
            "q": query,
            "filter": "buyingOptions:{AUCTION|FIXED_PRICE}",
            "limit": 200
        }
        
        try:
            # Refresh token if needed
            self.headers["Authorization"] = f"Bearer {self.token_manager.get_token()}"
            
            response = requests.get(
                f"{self.base_url}/item_summary/search",
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            # If 401, force token refresh and retry once
            if response.status_code == 401:
                self.token_manager._refresh_token()  # Force refresh
                self.headers["Authorization"] = f"Bearer {self.token_manager.get_token()}"
                response = requests.get(
                    f"{self.base_url}/item_summary/search",
                    headers=self.headers,
                    params=params,
                    timeout=30
                )
            
            response.raise_for_status()
            
            time.sleep(0.5)  # Rate limiting: 0.5 second delay between calls
            
            items = []
            for item in response.json().get('itemSummaries', []):
                card_info = self._extract_card_info(item.get('title', ''), item.get('condition'))
                items.append({
                    'ebay_item_id': item.get('itemId'),
                    'title': item.get('title'),
                    'price': float(item.get('price', {}).get('value', 0)),
                    'listing_type': 'auction' if 'AUCTION' in item.get('buyingOptions', []) else 'buy_it_now',
                    'card_info': card_info
                })
            
            return items
        except requests.exceptions.RequestException as e:
            print(f"Error fetching active listings: {e}")
            return []


if __name__ == '__main__':
    from backend.utils.database import SessionLocal
    from backend.models import Card, Sale
    from collections import Counter
    
    PLAYERS = [
        ('Shohei Ohtani', 'Baseball'),
        ('Paul Skenes', 'Baseball'),
        ('Gunnar Henderson', 'Baseball'),
        ('Bobby Witt Jr', 'Baseball'),
        ('Elly De La Cruz', 'Baseball'),
        ('Jackson Holliday', 'Baseball'),
        ('Jackson Merrill', 'Baseball'),
        ('Wyatt Langford', 'Baseball'),
        ('Aaron Judge', 'Baseball'),
        ('Ronald Acuna Jr', 'Baseball')
    ]
    
    scraper = EbayScraper()
    db = SessionLocal()
    
    print("Fetching REAL eBay data...")
    print("=" * 70)
    
    for player_name, sport in PLAYERS:
        print(f"\n{player_name}")
        query = f"{player_name} rookie card"
        sales = scraper.search_sold_listings(query, days_back=30, player_name=player_name, sport=sport)
        print(f"  {len(sales)} sales")
        
        for sale in sales:
            card = db.query(Card).filter(
                Card.player_name == player_name,
                Card.card_year == sale['card_year'],
                Card.card_set == sale['card_set']
            ).first()
            
            if not card:
                card = Card(
                    player_name=player_name,
                    sport=sport,
                    card_year=sale['card_year'],
                    card_set=sale['card_set'],
                    is_rookie=sale['is_rookie']
                )
                db.add(card)
                db.flush()
            
            existing = db.query(Sale).filter(Sale.ebay_item_id == sale['ebay_item_id']).first()
            if not existing:
                sale_date = sale['sale_date']
                if isinstance(sale_date, str):
                    # Parse full ISO datetime from eBay
                    sale_date = sale_date.replace('Z', '+00:00')
                    sale_date = datetime.fromisoformat(sale_date)
                
                sale_record = Sale(
                    card_id=card.id,
                    sale_price=sale['price'],
                    sale_date=sale_date,
                    ebay_item_id=sale['ebay_item_id'],
                    listing_title=sale['title']
                )
                db.add(sale_record)
        
        db.commit()
    
    print("\n" + "=" * 70)
    print("MOST POPULAR PLAYERS:")
    print("=" * 70)
    
    sales = db.query(Sale).join(Card).all()
    player_counts = Counter([sale.card.player_name for sale in sales])
    
    for i, (player, count) in enumerate(player_counts.most_common(), 1):
        print(f"{i:2d}. {player:25s} {count:4d} sales")
    
    db.close()
