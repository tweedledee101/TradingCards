"""
130point.com eBay Sold Data Scraper

Hits 130point's backend API directly (plain HTTP POST).
Returns actual completed eBay sale prices -- not asking prices.

Rate limit: 10 requests/minute, 429 = blocked 1 hour.
We enforce 7s between calls (safe margin under 10/min).

Usage:
    scraper = OneThirtyPointScraper()
    sales = scraper.search('Juan Soto 2026 Topps Mojo Refractor')
    print(f'{len(sales)} sold, median ${scraper.median_price(sales):.2f}')
"""
import re
import time
import requests
import statistics
from bs4 import BeautifulSoup
from backend.utils.logger import get_logger

log = get_logger('130point')

RATE_LIMIT_DELAY = 7  # seconds between calls (10/min limit)
RETRY_WAIT = 600      # 10 minutes on 429 (130point blocks ~1 hour, but often clears sooner)
MAX_RETRIES = 3
API_URL = 'https://back.130point.com/sales/'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0',
    'Origin': 'https://130point.com',
    'Referer': 'https://130point.com/sales/',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'X-Requested-With': 'XMLHttpRequest',
}


class OneThirtyPointScraper:

    def __init__(self):
        self._last_call = 0

    def _throttle(self):
        elapsed = time.time() - self._last_call
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self._last_call = time.time()

    def search(self, query: str) -> list:
        """Search 130point for eBay sold listings.

        Returns list of dicts: {title, price, sale_type, sale_date, raw_row}
        """
        self._throttle()

        data = {
            'query': query.replace(' ', '+'),
            'type': 2,
            'subcat': -1,
            'tab_id': 1,
            'tz': 'America/New_York',
            'sort': 'EndTimeSoonest',
        }

        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = requests.post(API_URL, headers=HEADERS, data=data, timeout=30)
                if resp.status_code == 429:
                    if attempt < MAX_RETRIES:
                        log.warn(f'130point rate limited (429), waiting {RETRY_WAIT}s (attempt {attempt+1}/{MAX_RETRIES})', category='130point_throttle')
                        time.sleep(RETRY_WAIT)
                        self._last_call = time.time()
                        continue
                    log.warn('130point rate limited (429), max retries exhausted', category='130point_throttle')
                    return []
                if resp.status_code != 200:
                    return []
                return self._parse_response(resp.text, query)
            except Exception as e:
                log.warn(f'130point request failed: {e}', category='130point_error')
                return []
        return []

    def _parse_response(self, html: str, query: str) -> list:
        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.find_all('tr')
        sales = []

        for row in rows:
            cells = row.find_all('td')
            if not cells:
                continue

            row_text = row.get_text(' ', strip=True)

            # Extract price
            price_match = re.search(r'Sale Price:\s*([\d,.]+)', row_text)
            if not price_match:
                price_match = re.search(r'\$([\d,.]+)', row_text)
            if not price_match:
                continue

            try:
                price = float(price_match.group(1).replace(',', ''))
            except ValueError:
                continue

            if price < 0.50:
                continue

            # Title: longest cell text that isn't a price/date
            title = ''
            for cell in cells:
                t = cell.get_text(strip=True)
                if len(t) > len(title) and '$' not in t and 'Sale Price' not in t:
                    title = t

            # Sale type
            sale_type = 'auction' if 'Auction' in row_text else 'fixed'

            # Date
            date_match = re.search(r'(\w+ \d+, \d{4})', row_text)
            sale_date = date_match.group(1) if date_match else ''

            sales.append({
                'title': title,
                'price': price,
                'sale_type': sale_type,
                'sale_date': sale_date,
                'query': query,
            })

        return sales

    @staticmethod
    def median_price(sales: list, ungraded_only: bool = True) -> float:
        """Calculate median sold price. Returns 0 if insufficient data."""
        if not sales:
            return 0
        prices = [s['price'] for s in sales]
        if not prices:
            return 0
        return statistics.median(prices)

    @staticmethod
    def volume(sales: list) -> int:
        return len(sales)
