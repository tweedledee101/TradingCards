"""
SportsCardsPro Market Rate Scraper

Gets accurate ungraded/Grade 9/PSA 10 prices for trading cards.
Uses Selenium (Firefox) to bypass Cloudflare protection.

URL Pattern: https://www.sportscardspro.com/search-products?q={query}&type=prices

Usage:
    scraper = SportsCardsProScraper()
    results = scraper.search("paul skenes 2024 bowman 87")
    for card in results:
        print(f"{card['title']} - Ungraded: ${card['ungraded']} PSA 10: ${card['psa_10']}")
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from urllib.parse import quote_plus
import logging
import time
import re

logger = logging.getLogger(__name__)


class SportsCardsProScraper:
    """Scrape SportsCardsPro for accurate card market rates"""

    BASE_URL = "https://www.sportscardspro.com"

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None

    def _init_driver(self):
        """Initialize Firefox WebDriver"""
        if self.driver:
            return

        options = Options()
        if self.headless:
            options.add_argument("--headless")
        options.set_preference("general.useragent.override",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0")
        options.binary_location = "/usr/bin/firefox"

        service = Service(executable_path="/usr/local/bin/geckodriver")
        self.driver = webdriver.Firefox(options=options, service=service)
        self.driver.set_page_load_timeout(30)

    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def search(self, query: str) -> List[Dict]:
        """
        Search SportsCardsPro for card prices

        Args:
            query: Search term (e.g., "paul skenes 2024 bowman 87")

        Returns:
            List of cards with ungraded, grade_9, and psa_10 prices
        """
        self._init_driver()
        encoded_query = quote_plus(query)
        url = f"{self.BASE_URL}/search-products?q={encoded_query}&type=prices"

        logger.info(f"Searching SportsCardsPro: {query}")

        try:
            try:
                self.driver.get(url)
            except Exception as e:
                # Page load timeout - page may still have loaded partially
                logger.warning(f"Page load timeout (may still have data): {e}")

            # Wait for page to load (check for table)
            for _ in range(4):
                time.sleep(2)
                if len(self.driver.page_source) > 5000:
                    break

            return self._parse_results(self.driver.page_source)

        except Exception as e:
            logger.error(f"Error searching SportsCardsPro: {e}")
            return []

    def _parse_results(self, html: str) -> List[Dict]:
        """Parse search results from HTML"""
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", id="games_table")
        
        if not table:
            logger.warning("No results table found")
            return []

        results = []
        rows = table.find_all("tr")[1:]  # Skip header

        for row in rows:
            card = self._parse_row(row)
            if card:
                results.append(card)

        logger.info(f"Found {len(results)} cards")
        return results

    def _parse_row(self, row) -> Optional[Dict]:
        """Parse a single table row"""
        try:
            title_td = row.find("td", class_="title")
            if not title_td:
                return None

            # Get title text from the link only (avoids concatenation with set)
            link = title_td.find("a")
            if link:
                raw_title = link.get_text(strip=True)
                href = link.get("href", "")
            else:
                raw_title = title_td.get_text(strip=True)
                href = ""

            # Get set from its own column (next sibling td after title)
            set_td = title_td.find_next_sibling("td")
            set_text = set_td.get_text(strip=True) if set_td else ""

            # Get prices
            used_td = row.find("td", class_="used_price")
            grade9_td = row.find("td", class_="cib_price")
            new_td = row.find("td", class_="new_price")

            ungraded = self._parse_price(used_td.get_text(strip=True)) if used_td else None
            grade_9 = self._parse_price(grade9_td.get_text(strip=True)) if grade9_td else None
            psa_10 = self._parse_price(new_td.get_text(strip=True)) if new_td else None

            # Parse card details from title
            card_info = self._parse_title(raw_title)

            # Parse set and year from set column (e.g. "2024 Bowman Chrome (Baseball)")
            set_year_match = re.match(r'(\d{4})\s+(.+?)\s*\(', set_text)
            if set_year_match:
                card_info["card_year"] = int(set_year_match.group(1))
                card_info["card_set"] = set_year_match.group(2).strip()
            elif set_text:
                card_info["card_set"] = re.sub(r'\s*\([^)]*\)\s*$', '', set_text).strip()

            card_info.update({
                "raw_title": raw_title,
                "set_text": set_text,
                "url": href,
                "ungraded": ungraded,
                "grade_9": grade_9,
                "psa_10": psa_10,
            })

            return card_info

        except Exception as e:
            logger.debug(f"Error parsing row: {e}")
            return None

    def _parse_title(self, title: str) -> Dict:
        """Extract card details from title text (just the title column, not set)"""
        info = {
            "player_name": None,
            "card_number": None,
            "card_set": None,
            "parallel": "Base",
            "card_year": None,
        }

        # Extract parallel (in brackets like [Silver], [X-fractor])
        parallel_match = re.search(r'\[([^\]]+)\]', title)
        if parallel_match:
            parallel = parallel_match.group(1)
            if parallel != "RC":
                info["parallel"] = parallel

        # Extract card number (#USC35, #29, #M1B-8, #II-AA, etc.)
        num_match = re.search(r'#([A-Za-z0-9-]+)', title)
        if num_match:
            info["card_number"] = num_match.group(1)

        # Extract numbered parallel (/50, /299, /5, etc.)
        numbered_match = re.search(r'/(\d+)\s*$', title)
        if numbered_match:
            info["print_run"] = int(numbered_match.group(1))

        # Extract player name (before first [ or #)
        name_match = re.match(r'^([A-Za-z\s.\'/-]+?)(?:\s*\[|\s*#)', title)
        if name_match:
            info["player_name"] = name_match.group(1).strip().rstrip('.')

        return info

    def _parse_price(self, text: str) -> Optional[float]:
        """Parse a price string to float"""
        if not text or text.strip() == "":
            return None
        cleaned = re.sub(r'[^0-9.]', '', text.replace(',', ''))
        try:
            val = float(cleaned)
            return val if val > 0 else None
        except (ValueError, TypeError):
            return None

    def scrape_product_page(self, url: str) -> Optional[Dict]:
        """
        Scrape prices directly from an SCP product page URL.
        No searching, no matching -- just load the page and read prices.

        Args:
            url: Full SCP product URL (e.g., https://www.sportscardspro.com/game/...)

        Returns:
            Dict with ungraded, grade_9, psa_10 prices, or None on failure
        """
        self._init_driver()
        logger.info(f"Direct scrape: {url}")

        try:
            try:
                self.driver.get(url)
            except Exception:
                pass  # timeout ok, page may still have loaded

            time.sleep(2)
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Price IDs on product page:
            #   td#used_price = Ungraded
            #   td#graded_price = Grade 9
            #   td#manual_only_price = PSA 10
            ungraded_td = soup.find("td", id="used_price")
            grade9_td = soup.find("td", id="graded_price")
            psa10_td = soup.find("td", id="manual_only_price")

            ungraded = self._extract_first_price(ungraded_td) if ungraded_td else None
            grade_9 = self._extract_first_price(grade9_td) if grade9_td else None
            psa_10 = self._extract_first_price(psa10_td) if psa10_td else None

            if not any([ungraded, grade_9, psa_10]):
                logger.warning(f"No prices found on product page: {url}")
                return None

            return {
                "ungraded": ungraded,
                "grade_9": grade_9,
                "psa_10": psa_10,
                "url": url,
            }

        except Exception as e:
            logger.error(f"Error scraping product page {url}: {e}")
            return None

    def _extract_first_price(self, td_element) -> Optional[float]:
        """Extract the main price from a td element (first span.price)"""
        price_span = td_element.find("span", class_="price")
        if price_span:
            return self._parse_price(price_span.get_text(strip=True))
        return self._parse_price(td_element.get_text(strip=True))

    def get_market_rate(
        self,
        player_name: str,
        card_year: int = None,
        card_set: str = None,
        card_number: str = None,
        parallel: str = "Base"
    ) -> Optional[Dict]:
        """
        Get market rate for a specific card variant

        Args:
            player_name: Player name
            card_year: Card year (e.g., 2024)
            card_set: Set name (e.g., "Topps Chrome")
            card_number: Card number (e.g., "87", "USC35")
            parallel: Parallel type (Base, X-fractor, etc.)

        Returns:
            Best matching card with prices, or None
        """
        # Build search query
        parts = [player_name]
        if card_year:
            parts.append(str(card_year))
        if card_set:
            parts.append(card_set)
        if card_number:
            parts.append(f"#{card_number}")

        query = " ".join(parts)
        results = self.search(query)

        if not results:
            return None

        # Find best match by parallel
        parallel_lower = parallel.lower()
        for card in results:
            card_parallel = (card.get("parallel") or "Base").lower()
            if card_parallel == parallel_lower:
                return card

        # Fall back to first result (usually Base)
        return results[0]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    scraper = SportsCardsProScraper(headless=True)

    try:
        print("Testing SportsCardsPro scraper...")
        print("=" * 70)

        # Test 1: Wyatt Langford
        print("\nSearch: Wyatt Langford 2024 Topps Chrome USC35")
        results = scraper.search("Wyatt Langford 2024 Topps Chrome USC35")
        print(f"Found {len(results)} results")
        for card in results[:5]:
            title = card.get("raw_title", "Unknown")[:60]
            ungraded = f"${card['ungraded']:.2f}" if card.get("ungraded") else "N/A"
            psa_10 = f"${card['psa_10']:.2f}" if card.get("psa_10") else "N/A"
            parallel = card.get("parallel", "Base")
            print(f"  [{parallel}] {title}")
            print(f"    Ungraded: {ungraded}  |  PSA 10: {psa_10}")

        # Test 2: Paul Skenes
        print("\n" + "=" * 70)
        print("\nSearch: Paul Skenes 2024 Bowman 87")
        results = scraper.search("Paul Skenes 2024 Bowman 87")
        print(f"Found {len(results)} results")
        for card in results[:5]:
            title = card.get("raw_title", "Unknown")[:60]
            ungraded = f"${card['ungraded']:.2f}" if card.get("ungraded") else "N/A"
            psa_10 = f"${card['psa_10']:.2f}" if card.get("psa_10") else "N/A"
            parallel = card.get("parallel", "Base")
            print(f"  [{parallel}] {title}")
            print(f"    Ungraded: {ungraded}  |  PSA 10: {psa_10}")

    finally:
        scraper.close()
