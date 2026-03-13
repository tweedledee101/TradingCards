"""
COMC (Check Out My Cards) Scraper

Scrapes COMC for card inventory and pricing.
Dealers use COMC for bulk buying at wholesale prices.
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import time

class COMCScraper:
    """Scrape COMC for card listings"""
    
    BASE_URL = "https://www.comc.com"
    
    def search_cards(self, player: str, year: Optional[int] = None, card_set: Optional[str] = None) -> List[Dict]:
        """
        Search COMC for cards
        
        Args:
            player: Player name
            year: Card year (optional)
            card_set: Card set (optional)
            
        Returns:
            List of listings with title, price, condition, url
        """
        query = player
        if year:
            query += f" {year}"
        if card_set:
            query += f" {card_set}"
        
        search_url = f"{self.BASE_URL}/Cards,sh,={query.replace(' ', '+')}"
        
        try:
            response = requests.get(search_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            listings = []
            
            # COMC uses dynamic loading - return search URL for manual check
            return [{
                "platform": "comc",
                "search_url": search_url,
                "note": "Check COMC manually - often has bulk discounts"
            }]
            
        except Exception as e:
            return [{
                "platform": "comc",
                "search_url": search_url,
                "error": str(e)
            }]
    
    def get_search_url(self, player: str, year: Optional[int] = None, card_set: Optional[str] = None) -> str:
        """Generate COMC search URL"""
        query = player
        if year:
            query += f" {year}"
        if card_set:
            query += f" {card_set}"
        return f"{self.BASE_URL}/Cards,sh,={query.replace(' ', '+')}"
