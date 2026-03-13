"""
130point.com Market Rate Scraper

Gets variant-specific market rates for trading cards.
Zero eBay API calls - uses web scraping instead.

Data Flow:
    130point.com → parse_html() → variant_market_rate

Usage:
    scraper = Point130Scraper()
    rate = scraper.get_market_rate("Victor Wembanyama", 2023, "Prizm", "Silver", "PSA", 9)
"""
import requests
from bs4 import BeautifulSoup
import re
from typing import Optional, Dict, List
import time

class Point130Scraper:
    """
    Scraper for 130point.com variant-specific market rates
    
    Provides accurate pricing for specific card variants without eBay API usage
    """
    
    def __init__(self):
        self.base_url = "https://130point.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_market_rate(
        self,
        player_name: str,
        card_year: int,
        card_set: str,
        parallel: Optional[str] = None,
        grade_company: Optional[str] = None,
        grade_value: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Get market rate for specific card variant
        
        Args:
            player_name: Player name (e.g., "Victor Wembanyama")
            card_year: Card year (e.g., 2023)
            card_set: Card set (e.g., "Prizm")
            parallel: Parallel type (e.g., "Silver", "Red Ice")
            grade_company: Grading company (e.g., "PSA", "BGS")
            grade_value: Grade value (e.g., 9, 10)
            
        Returns:
            Dictionary with market_rate, sales_count, last_sale_date
            
        Example:
            >>> scraper = Point130Scraper()
            >>> rate = scraper.get_market_rate("Victor Wembanyama", 2023, "Prizm", "Silver", "PSA", 9)
            >>> print(rate['market_rate'])  # 245.00
        """
        # Build search query
        query = f"{player_name} {card_year} {card_set}"
        if parallel and parallel.lower() != 'base':
            query += f" {parallel}"
        if grade_company and grade_company.lower() != 'raw':
            query += f" {grade_company} {grade_value}"
        
        try:
            # Search for card
            search_url = f"{self.base_url}/sales"
            params = {'q': query, 'sport': 'basketball'}
            
            response = self.session.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            # Parse results
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find matching card listing
            card_data = self._parse_card_listing(soup, parallel, grade_company, grade_value)
            
            if card_data:
                time.sleep(1)  # Rate limiting
                return card_data
            
            return None
            
        except Exception as e:
            print(f"Error scraping 130point for {query}: {e}")
            return None
    
    def _parse_card_listing(
        self,
        soup: BeautifulSoup,
        parallel: Optional[str],
        grade_company: Optional[str],
        grade_value: Optional[float]
    ) -> Optional[Dict]:
        """
        Parse card listing from search results
        
        Args:
            soup: BeautifulSoup object of search results page
            parallel: Expected parallel type
            grade_company: Expected grading company
            grade_value: Expected grade value
            
        Returns:
            Dictionary with market data or None
        """
        # Find all card listings
        listings = soup.find_all('div', class_='card-listing')
        
        for listing in listings:
            # Extract variant info from listing
            variant_text = listing.find('span', class_='variant')
            grade_text = listing.find('span', class_='grade')
            
            # Check if this matches our target variant
            if parallel and variant_text:
                if parallel.lower() not in variant_text.text.lower():
                    continue
            
            if grade_company and grade_text:
                if grade_company.lower() not in grade_text.text.lower():
                    continue
                if grade_value and str(int(grade_value)) not in grade_text.text:
                    continue
            
            # Extract market rate
            price_elem = listing.find('span', class_='market-price')
            if not price_elem:
                continue
            
            price_text = price_elem.text.strip()
            market_rate = self._parse_price(price_text)
            
            if not market_rate:
                continue
            
            # Extract sales count
            sales_elem = listing.find('span', class_='sales-count')
            sales_count = 0
            if sales_elem:
                sales_match = re.search(r'(\d+)', sales_elem.text)
                if sales_match:
                    sales_count = int(sales_match.group(1))
            
            # Extract last sale date
            date_elem = listing.find('span', class_='last-sale')
            last_sale_date = None
            if date_elem:
                last_sale_date = date_elem.text.strip()
            
            return {
                'market_rate': market_rate,
                'sales_count': sales_count,
                'last_sale_date': last_sale_date,
                'source': '130point.com'
            }
        
        return None
    
    def _parse_price(self, price_text: str) -> Optional[float]:
        """
        Parse price from text
        
        Args:
            price_text: Price string (e.g., "$245.00", "$1,250")
            
        Returns:
            Float price or None
        """
        # Remove currency symbols and commas
        cleaned = re.sub(r'[$,]', '', price_text)
        
        try:
            return float(cleaned)
        except ValueError:
            return None
    
    def get_all_variants(
        self,
        player_name: str,
        card_year: int,
        card_set: str
    ) -> List[Dict]:
        """
        Get market rates for all variants of a card
        
        Args:
            player_name: Player name
            card_year: Card year
            card_set: Card set
            
        Returns:
            List of dictionaries with variant data
            
        Example:
            >>> scraper = Point130Scraper()
            >>> variants = scraper.get_all_variants("Victor Wembanyama", 2023, "Prizm")
            >>> for v in variants:
            ...     print(f"{v['parallel']} {v['grade']}: ${v['market_rate']}")
        """
        query = f"{player_name} {card_year} {card_set}"
        
        try:
            search_url = f"{self.base_url}/sales"
            params = {'q': query, 'sport': 'basketball'}
            
            response = self.session.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            variants = []
            listings = soup.find_all('div', class_='card-listing')
            
            for listing in listings:
                variant_elem = listing.find('span', class_='variant')
                grade_elem = listing.find('span', class_='grade')
                price_elem = listing.find('span', class_='market-price')
                
                if not price_elem:
                    continue
                
                parallel = variant_elem.text.strip() if variant_elem else 'Base'
                grade_text = grade_elem.text.strip() if grade_elem else 'Raw'
                market_rate = self._parse_price(price_elem.text)
                
                if market_rate:
                    # Parse grade
                    grade_company = None
                    grade_value = None
                    
                    if grade_text.lower() != 'raw':
                        grade_match = re.match(r'(PSA|BGS|SGC)\s*(\d+(?:\.\d)?)', grade_text)
                        if grade_match:
                            grade_company = grade_match.group(1)
                            grade_value = float(grade_match.group(2))
                    
                    variants.append({
                        'parallel': parallel,
                        'grade_company': grade_company or 'Raw',
                        'grade_value': grade_value,
                        'market_rate': market_rate
                    })
            
            time.sleep(1)  # Rate limiting
            return variants
            
        except Exception as e:
            print(f"Error scraping variants for {query}: {e}")
            return []


if __name__ == '__main__':
    # Test scraper
    scraper = Point130Scraper()
    
    # Test single variant
    print("Testing single variant lookup...")
    rate = scraper.get_market_rate(
        "Victor Wembanyama",
        2023,
        "Prizm",
        "Silver",
        "PSA",
        9
    )
    
    if rate:
        print(f"✓ Market Rate: ${rate['market_rate']}")
        print(f"  Sales Count: {rate['sales_count']}")
        print(f"  Last Sale: {rate['last_sale_date']}")
    else:
        print("✗ No data found")
    
    # Test all variants
    print("\nTesting all variants lookup...")
    variants = scraper.get_all_variants("Victor Wembanyama", 2023, "Prizm")
    
    if variants:
        print(f"✓ Found {len(variants)} variants:")
        for v in variants[:5]:  # Show first 5
            grade = f"{v['grade_company']} {v['grade_value']}" if v['grade_value'] else "Raw"
            print(f"  - {v['parallel']:15s} {grade:10s} ${v['market_rate']:.2f}")
    else:
        print("✗ No variants found")
