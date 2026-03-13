"""
Whatnot Scraper

Scrapes Whatnot for live auction data.
Dealers use Whatnot to snipe deals during live streams.
"""
import requests
from typing import List, Dict, Optional

class WhatnotScraper:
    """Scrape Whatnot for live auctions"""
    
    BASE_URL = "https://www.whatnot.com"
    
    def search_cards(self, player: str, year: Optional[int] = None, card_set: Optional[str] = None) -> List[Dict]:
        """
        Search Whatnot for cards
        
        Args:
            player: Player name
            year: Card year (optional)
            card_set: Card set (optional)
            
        Returns:
            List of live streams and listings
        """
        query = player
        if year:
            query += f" {year}"
        if card_set:
            query += f" {card_set}"
        
        search_url = f"{self.BASE_URL}/search?query={query.replace(' ', '%20')}"
        
        return [{
            "platform": "whatnot",
            "search_url": search_url,
            "note": "Check live streams - can snipe deals during auctions"
        }]
    
    def get_search_url(self, player: str, year: Optional[int] = None, card_set: Optional[str] = None) -> str:
        """Generate Whatnot search URL"""
        query = player
        if year:
            query += f" {year}"
        if card_set:
            query += f" {card_set}"
        return f"{self.BASE_URL}/search?query={query.replace(' ', '%20')}"
