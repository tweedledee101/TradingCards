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
        self.base_url = "https://api.ebay.com/buy/browse/v1"
        self.headers = {
            "Authorization": f"Bearer {config.EBAY_TOKEN}",
            "Content-Type": "application/json"
        }
    
    def search_sold_listings(self, query: str, days_back: int = 7) -> List[Dict]:
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
            response = requests.get(
                f"{self.base_url}/item_summary/search",
                headers=self.headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return self._parse_results(response.json())
        except requests.exceptions.RequestException as e:
            print(f"Error fetching eBay data for '{query}': {e}")
            return []
    
    def _parse_results(self, data: dict) -> List[Dict]:
        """
        Parse eBay API response into structured data
        
        Args:
            data: Raw JSON response from eBay API
            
        Returns:
            List of dictionaries with sale and card details
        """
        items = []
        
        for item in data.get('itemSummaries', []):
            parsed = {
                'ebay_item_id': item.get('itemId'),
                'title': item.get('title'),
                'price': float(item.get('price', {}).get('value', 0)),
                'currency': item.get('price', {}).get('currency'),
                'sale_date': item.get('itemEndDate'),
                'condition': item.get('condition'),
                'listing_type': 'auction' if 'AUCTION' in item.get('buyingOptions', []) else 'buy_it_now'
            }
            
            # Extract card details from title
            card_info = self._extract_card_info(parsed['title'])
            parsed.update(card_info)
            
            items.append(parsed)
        
        return items
    
    def _extract_card_info(self, title: str) -> Dict:
        """
        Extract player name, year, rookie status, grading from listing title
        
        Uses regex patterns to identify:
        - Rookie cards (RC, rookie)
        - Year (4-digit)
        - Grading company and grade (PSA 10, BGS 9.5, etc.)
        
        Args:
            title: eBay listing title
            
        Returns:
            Dictionary with extracted card attributes
            
        Example:
            >>> info = self._extract_card_info("2023 Panini Prizm Victor Wembanyama RC PSA 10")
            >>> print(info['is_rookie'])  # True
            >>> print(info['grade_value'])  # 10.0
        """
        title_lower = title.lower()
        
        # Check if rookie card
        is_rookie = bool(re.search(r'\brc\b|\brookie\b', title_lower))
        
        # Extract year (4 digits, 19xx or 20xx)
        year_match = re.search(r'\b(19|20)\d{2}\b', title)
        year = int(year_match.group()) if year_match else None
        
        # Check if graded
        graded = bool(re.search(r'\bpsa\b|\bbgs\b|\bsgc\b', title_lower))
        grade_company = None
        grade_value = None
        
        if graded:
            # PSA grading
            if 'psa' in title_lower:
                grade_company = 'PSA'
                grade_match = re.search(r'psa\s*(\d+(?:\.\d)?)', title_lower)
                if grade_match:
                    grade_value = float(grade_match.group(1))
            
            # BGS/Beckett grading
            elif 'bgs' in title_lower or 'beckett' in title_lower:
                grade_company = 'BGS'
                grade_match = re.search(r'(?:bgs|beckett)\s*(\d+(?:\.\d)?)', title_lower)
                if grade_match:
                    grade_value = float(grade_match.group(1))
            
            # SGC grading
            elif 'sgc' in title_lower:
                grade_company = 'SGC'
                grade_match = re.search(r'sgc\s*(\d+(?:\.\d)?)', title_lower)
                if grade_match:
                    grade_value = float(grade_match.group(1))
        
        # Extract card set (common patterns)
        card_set = self._extract_card_set(title)
        
        return {
            'is_rookie': is_rookie,
            'card_year': year,
            'graded': graded,
            'grade_company': grade_company,
            'grade_value': grade_value,
            'card_set': card_set
        }
    
    def _extract_card_set(self, title: str) -> Optional[str]:
        """
        Extract card set name from title
        
        Common sets: Prizm, Optic, Select, Topps Chrome, Bowman, etc.
        
        Args:
            title: eBay listing title
            
        Returns:
            Card set name or None
        """
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
        
        for card_set in sets:
            if card_set in title_lower:
                return card_set.title()
        
        return None
    
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
            response = requests.get(
                f"{self.base_url}/item_summary/search",
                headers=self.headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            items = []
            for item in response.json().get('itemSummaries', []):
                items.append({
                    'ebay_item_id': item.get('itemId'),
                    'title': item.get('title'),
                    'price': float(item.get('price', {}).get('value', 0)),
                    'listing_type': 'auction' if 'AUCTION' in item.get('buyingOptions', []) else 'buy_it_now'
                })
            
            return items
        except requests.exceptions.RequestException as e:
            print(f"Error fetching active listings: {e}")
            return []
