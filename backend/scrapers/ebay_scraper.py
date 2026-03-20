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
            
            # Get best image URL (prefer full-size thumbnail)
            image_url = None
            thumbs = item.get('thumbnailImages', [])
            if thumbs:
                image_url = thumbs[0].get('imageUrl')
            if not image_url:
                img = item.get('image', {})
                image_url = img.get('imageUrl') if img else None

            parsed = {
                'ebay_item_id': item.get('itemId'),
                'title': title,
                'price': float(item.get('price', {}).get('value', 0)),
                'currency': item.get('price', {}).get('currency'),
                'sale_date': item.get('itemEndDate') or datetime.now().isoformat(),  # Fallback to now
                'condition': item.get('condition'),
                'listing_type': 'auction' if 'AUCTION' in item.get('buyingOptions', []) else 'buy_it_now',
                'image_url': image_url
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
        
        # Check grading from eBay condition field OR title text
        graded = ebay_condition == 'Graded'
        grade_company = None
        grade_value = None
        
        # Always try to extract grading from title (eBay condition field is unreliable)
        # PSA grading
        if 'psa' in title_lower:
            grade_company = 'PSA'
            graded = True
            grade_match = re.search(r'psa\s*(\d+(?:\.\d)?)', title_lower)
            if grade_match:
                val = float(grade_match.group(1))
                if 1 <= val <= 10:
                    grade_value = val
        
        # BGS/Beckett grading
        elif 'bgs' in title_lower or 'beckett' in title_lower:
            grade_company = 'BGS'
            graded = True
            grade_match = re.search(r'(?:bgs|beckett)\s*(\d+(?:\.\d)?)', title_lower)
            if grade_match:
                val = float(grade_match.group(1))
                if 1 <= val <= 10:
                    grade_value = val
        
        # SGC grading
        elif 'sgc' in title_lower:
            grade_company = 'SGC'
            graded = True
            grade_match = re.search(r'sgc\s*(\d+(?:\.\d)?)', title_lower)
            if grade_match:
                val = float(grade_match.group(1))
                if 1 <= val <= 10:
                    grade_value = val
        
        # Extract card set (common patterns)
        card_set = self._extract_card_set(title)
        
        # Extract parallel type
        parallel = self._extract_parallel(title)
        
        # Extract card number from title (#RP-RA, #193, #US252, etc.)
        card_number = None
        num_match = re.search(r'#([A-Za-z0-9-]+)', title)
        if num_match:
            card_number = num_match.group(1)
        
        return {
            'is_rookie': is_rookie,
            'card_year': year,
            'graded': graded,
            'grade_company': grade_company,
            'grade_value': grade_value,
            'card_set': card_set,
            'parallel': parallel,
            'card_number': card_number
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
        Extract card set name from title, including sub-sets.
        Matches most specific set first (e.g. "Topps Heritage Rookie Performers" before "Topps").
        """
        if not title:
            return 'Unknown'
        
        title_lower = title.lower()
        
        # Specific sub-sets first (order matters - most specific first)
        specific_sets = [
            'topps chrome update', 'topps chrome',
            # Topps sub-sets
            'topps heritage high number', 'topps heritage',
            'topps update', 'topps fire', 'topps holiday', 'topps opening day',
            'topps allen & ginter', 'topps allen and ginter',
            'topps gallery', 'topps gold label', 'topps inception',
            'topps luminaries', 'topps museum collection',
            'topps series 2', 'topps series 1',
            'topps tier one', 'topps tribute', 'topps now',
            'topps high tek', 'topps finest',
            # Bowman sub-sets
            'bowman chrome', 'bowman draft', 'bowman platinum',
            'bowman sterling', 'bowman best', "bowman's best",
            # Stadium Club
            'stadium club chrome', 'stadium club',
            'gypsy queen',
            # Panini sub-sets
            'panini prizm', 'panini select', 'panini mosaic',
            'panini donruss optic', 'panini donruss',
            'panini chronicles', 'panini contenders',
            'panini revolution', 'panini hoops',
            'panini flawless', 'panini national treasures',
            'panini immaculate', 'panini spectra',
            # Leaf sub-sets (order matters - most specific first)
            'leaf certified materials', 'leaf certified',
            'leaf limited', 'leaf rookies & stars', 'leaf rookies and stars',
            'leaf rookie achievement', 'leaf rookie stars',
            'leaf exclusive rookie', 'leaf exclusive legends',
            'leaf legend exclusive', 'leaf prized legend',
            'leaf collective promo', 'leaf collective',
            'leaf baseball lore', 'leaf draft',
            'leaf perfect game', 'leaf studio',
            'leaf flag rookie', 'leaf silver',
            'leaf legend', 'leaf rookie', 'leaf og',
        ]
        
        for card_set in specific_sets:
            if card_set in title_lower:
                matched_set = card_set.title()
                # Check if title also contains an insert sub-set name
                # (often separated from set name by player name)
                insert_names = [
                    '1984 topps', '1985 topps', '1986 retro', '1972 retro',
                    '35th anniversary', '50th anniversary',
                    'all etch', 'all-topps', 'all topps',
                    'all time rookie', 'chrome connection',
                    "decade's next", 'decades next',
                    'lord of the diamonds', 'master of the game',
                    'milestone', 'national chicle',
                    'opening day', 'power players',
                    'record numbers', 'rookie cup',
                    'torres terrors', 'cup card',
                ]
                for ins in insert_names:
                    if ins in title_lower and ins not in card_set:
                        return f"{matched_set} {ins.title()}"
                return matched_set
        
        # Then try to extract insert/sub-set names from title
        # Pattern: "YEAR SetName PlayerName" or "PlayerName YEAR SetName"
        # Look for known insert keywords
        insert_keywords = [
            'rookie performers', 'rookie salute', 'year in review',
            'rookie debut', 'rookie cup', 'future stars',
            'all-star', 'all star', 'home run derby',
            'postseason', 'world series',
            'my 1st bowman', '1st bowman',
        ]
        for kw in insert_keywords:
            if kw in title_lower:
                # Find the parent set
                for parent in ['topps heritage', 'topps chrome', 'topps update', 'topps', 'bowman chrome', 'bowman']:
                    if parent in title_lower:
                        return f"{parent} {kw}".title()
                return kw.title()
        
        # Generic single-word sets
        generic_sets = [
            'prizm', 'optic', 'select', 'mosaic', 'donruss',
            'chronicles', 'hoops', 'revolution', 'contenders',
            'topps', 'bowman', 'heritage', 'leaf',
        ]
        for card_set in generic_sets:
            if card_set in title_lower:
                return card_set.title()
        
        # Fallback brands
        brands = ['panini', 'topps', 'upper deck', 'leaf', 'fleer']
        for brand in brands:
            if brand in title_lower:
                return brand.title()
        
        return 'Unknown'
    
    def _extract_parallel(self, title: str) -> str:
        """
        Extract full parallel/variant name from title.
        
        Captures the complete variant phrase (e.g. "Lime Green Refractor",
        "Blue Foil Pattern II", "Light Blue Sparkle") instead of just the
        base color, so cards can be matched 1:1 with SCP.
        """
        if not title:
            return 'Base'
        
        title_lower = title.lower()
        
        # Multi-word parallels - most specific first (order matters)
        # Each entry is matched as-is against the lowercased title
        specific_parallels = [
            # Foil patterns (Bowman Inception etc.)
            'blue foil pattern ii', 'gold foil pattern ii', 'red foil pattern ii',
            'blue foil pattern iii', 'gold foil pattern iii',
            # Light/Lime/Sky/Royal color variants (BEFORE plain foils)
            'light blue sparkle chrome', 'light blue sparkle',
            'light blue foil', 'light blue',
            'lime green refractor', 'lime green foil', 'lime green',
            'sky blue refractor', 'sky blue',
            'royal blue', 'navy blue',
            # Plain foils (after light/lime/sky variants)
            'blue foil', 'gold foil', 'red foil', 'green foil',
            'orange foil', 'purple foil', 'pink foil',
            # Shimmer refractors
            'green shimmer refractor', 'blue shimmer refractor',
            'gold shimmer refractor', 'orange shimmer refractor',
            'red shimmer refractor', 'purple shimmer refractor',
            'pink shimmer refractor', 'black shimmer refractor',
            'fuchsia shimmer refractor', 'shimmer refractor',
            # Geometric refractors
            'green geometric refractor', 'blue geometric refractor',
            'gold geometric refractor',
            # Sparkle refractors
            'green sparkle refractor', 'blue sparkle refractor',
            'gold sparkle refractor',
            # Speckle refractors
            'green speckle refractor', 'blue speckle refractor',
            'gold speckle refractor', 'speckle refractor',
            # Color + refractor
            'silver refractor',
            'green refractor', 'blue refractor', 'gold refractor',
            'red refractor', 'orange refractor', 'purple refractor',
            'pink refractor', 'black refractor', 'yellow refractor',
            'aqua refractor', 'fuchsia refractor',
            # Mojo / Mega Box
            'mega box mojo refractor', 'mega box mojo', 'mojo refractor', 'mojo',
            # Xfractors
            'green xfractor', 'red xfractor', 'blue xfractor', 'xfractor',
            # Sapphire
            'sapphire',
            # Lava refractors
            'yellow lava refractor', 'red lava refractor',
            'blue lava refractor', 'green lava refractor', 'lava refractor',
            # Gilded refractors
            'gold gilded refractor', 'gilded refractor',
            # Prism refractors
            'prism refractor',
            # Wave refractors
            'raywave refractor', 'ray wave refractor',
            'green wave refractor', 'blue wave refractor',
            'gold wave refractor', 'aqua wave refractor',
            'red wave refractor', 'orange wave refractor',
            'purple wave refractor', 'pink wave refractor',
            'wave refractor',
            # Plain refractor
            'refractor',
            # Ice variants (Prizm)
            'red ice', 'blue ice', 'green ice', 'orange ice', 'pink ice',
            # Prizm specific
            'tiger stripe', 'neon green', 'fast break', 'choice', 'hyper',
            # Sparkle / Chrome (non-refractor)
            'blue sparkle', 'gold sparkle', 'green sparkle',
            'red sparkle', 'sparkle',
            # Crackleboard
            'silver crackleboard', 'gold crackleboard', 'crackleboard',
            # Sepia / Black & White
            'sepia', 'black and white', 'black & white',
            # SP (short print)
            'sp',
            # Autograph (check before colors to catch "Gold Auto" etc.)
            'autograph', 'auto',
        ]
        
        for p in specific_parallels:
            if p in title_lower:
                return p.title()
        
        # Single color parallels - only if no modifier was found above
        colors = ['silver', 'gold', 'orange', 'green', 'blue', 'red',
                  'purple', 'pink', 'black', 'yellow', 'aqua', 'fuchsia']
        for color in colors:
            if re.search(rf'\b{color}\b', title_lower):
                return color.title()
        
        # Numbered parallels (e.g. /99, /50) - only if no color found
        if re.search(r'/\d+', title):
            return 'Numbered'
        
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
                # Get best image URL
                image_url = None
                thumbs = item.get('thumbnailImages', [])
                if thumbs:
                    image_url = thumbs[0].get('imageUrl')
                if not image_url:
                    img = item.get('image', {})
                    image_url = img.get('imageUrl') if img else None
                items.append({
                    'ebay_item_id': item.get('itemId'),
                    'title': item.get('title'),
                    'price': float(item.get('price', {}).get('value', 0)),
                    'listing_type': 'auction' if 'AUCTION' in item.get('buyingOptions', []) else 'buy_it_now',
                    'card_info': card_info,
                    'image_url': image_url
                })
            
            return items
        except requests.exceptions.RequestException as e:
            print(f"Error fetching active listings: {e}")
            return []


if __name__ == '__main__':
    from backend.utils.database import SessionLocal
    from backend.models import Card, Sale
    from backend.services.data_pipeline import DataPipeline
    from collections import Counter
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--players', nargs='+', help='Specific players to import (default: use discover_players)')
    parser.add_argument('--days', type=int, default=30, help='Days back to search')
    args = parser.parse_args()
    
    if args.players:
        # Manual player list from command line
        PLAYERS = [(name, 'Baseball') for name in args.players]
    else:
        # Use volume-based discovery
        from backend.discover_players import discover_top_players
        print("Running volume-based player discovery...")
        print("=" * 70)
        discovered = discover_top_players(days=7, limit=20, sport='Baseball')
        PLAYERS = [(p['player_name'], p['sport']) for p in discovered]
        print(f"\nDiscovered {len(PLAYERS)} players. Importing sold listings...")
    
    scraper = EbayScraper()
    pipeline = DataPipeline()
    db = SessionLocal()
    
    print("\nFetching eBay sold listings...")
    print("=" * 70)
    
    from backend.config.sets import get_set_queries

    for player_name, sport in PLAYERS:
        print(f"\n{player_name}")
        queries = [f"{player_name} card"] + get_set_queries(player_name, sport)
        seen_ids = set()

        for qi, query in enumerate(queries):
            label = "generic" if qi == 0 else query.split(player_name)[-1].strip()
            print(f"  [{label}]...", end=" ", flush=True)
            sales = scraper.search_sold_listings(query, days_back=args.days, player_name=player_name, sport=sport)
            imported = 0

            for sale in sales:
                if sale['ebay_item_id'] in seen_ids:
                    continue
                seen_ids.add(sale['ebay_item_id'])

                sale['player_name'] = player_name
                sale['sport'] = sport

                card = pipeline.find_or_create_card(db, sale)

                if sale.get('image_url') and not card.image_url:
                    card.image_url = sale['image_url']

                existing = db.query(Sale).filter(Sale.ebay_item_id == sale['ebay_item_id']).first()
                if not existing:
                    sale_date = sale['sale_date']
                    if isinstance(sale_date, str):
                        sale_date = sale_date.replace('Z', '+00:00')
                        sale_date = datetime.fromisoformat(sale_date)

                    sale_record = Sale(
                        card_id=card.id,
                        sale_price=sale['price'],
                        sale_date=sale_date,
                        ebay_item_id=sale['ebay_item_id'],
                        listing_title=sale['title'],
                        graded=sale.get('graded', False),
                        grade_company=sale.get('grade_company'),
                        grade_value=sale.get('grade_value')
                    )
                    db.add(sale_record)
                    imported += 1

            db.commit()
            print(f"{len(sales)} found, {imported} new")
    
    print("\n" + "=" * 70)
    print("MOST POPULAR PLAYERS:")
    print("=" * 70)
    
    sales = db.query(Sale).join(Card).all()
    player_counts = Counter([sale.card.player_name for sale in sales])
    
    for i, (player, count) in enumerate(player_counts.most_common(), 1):
        print(f"{i:2d}. {player:25s} {count:4d} sales")
    
    db.close()
