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
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional


def _browse_datetime_utc_z(dt: datetime) -> str:
    """eBay Browse ``itemEndDate`` filters expect UTC with a ``Z`` suffix."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
from backend.config.settings import config
from backend.utils.listing_card_identity import card_number_tokens_from_free_text


def collect_browse_item_image_urls(item: Dict) -> List[str]:
    """
    All distinct image URLs eBay exposes on a Browse API item (search summary or GET /item).

    Uses ``image``, ``thumbnailImages``, and ``additionalImages`` only — no HTML scraping.
    CDN URLs are usually fetchable without hitting www.ebay.com (avoids browser bot walls
    for downstream vision / multimodal models).
    """
    urls: List[str] = []
    seen: set = set()

    def add(u: Optional[str]) -> None:
        if u and isinstance(u, str) and u not in seen:
            seen.add(u)
            urls.append(u)

    img = item.get("image")
    if isinstance(img, dict):
        add(img.get("imageUrl"))

    for th in item.get("thumbnailImages") or []:
        if isinstance(th, dict):
            add(th.get("imageUrl"))

    for ex in item.get("additionalImages") or []:
        if isinstance(ex, dict):
            add(ex.get("imageUrl"))
        elif isinstance(ex, str):
            add(ex)

    return urls


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
        
        # Browse search expects a marketplace; omitting headers can yield empty totals on some clients.
        self.headers = {
            "Authorization": f"Bearer {self.token_manager.get_token()}",
            "Content-Type": "application/json",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
            "X-EBAY-C-ENDUSERCTX": "contextualLocation=country%3DUS",
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
            "filter": (
                "buyingOptions:{AUCTION|FIXED_PRICE},"
                f"itemEndDate:[{_browse_datetime_utc_z(start_date)}..{_browse_datetime_utc_z(end_date)}]"
            ),
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
            
            image_urls = collect_browse_item_image_urls(item)
            image_url = image_urls[0] if image_urls else None

            parsed = {
                'ebay_item_id': item.get('itemId'),
                'title': title,
                'price': float(item.get('price', {}).get('value', 0)),
                'currency': item.get('price', {}).get('currency'),
                'sale_date': item.get('itemEndDate') or datetime.now().isoformat(),  # Fallback to now
                'condition': item.get('condition'),
                'listing_type': 'auction' if 'AUCTION' in item.get('buyingOptions', []) else 'buy_it_now',
                'image_url': image_url,
                'image_urls': image_urls,
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

    @staticmethod
    def _coerce_browse_text(val) -> str:
        """Normalize Browse API text fields (string or {value: ...})."""
        if val is None:
            return ''
        if isinstance(val, dict):
            return str(val.get('value') or val.get('text') or '').strip()
        return str(val).strip()

    @staticmethod
    def _html_to_plain(text: str) -> str:
        if not text:
            return ''
        plain = re.sub(r'<[^>]+>', ' ', text)
        plain = re.sub(r'&nbsp;|&amp;|&lt;|&gt;|&#\d+;', ' ', plain, flags=re.I)
        plain = re.sub(r'\s+', ' ', plain).strip()
        return plain

    @staticmethod
    def _item_description_plain_text(item_data: dict) -> str:
        parts = []
        for key in ('shortDescription', 'description', 'additionalProductDetails'):
            raw = item_data.get(key)
            parts.append(EbayScraper._coerce_browse_text(raw))
        return EbayScraper._html_to_plain(' '.join(p for p in parts if p))

    @staticmethod
    def _first_hashtag_card_number(text: str) -> Optional[str]:
        if not text:
            return None
        m = re.search(r'#\s*([A-Za-z0-9][A-Za-z0-9-]*)', text)
        return m.group(1) if m else None

    @staticmethod
    def _first_reasonable_year_in_text(text: str) -> Optional[int]:
        """First 4-digit year in 1980..(UTC year+1) — release year in description."""
        if not text:
            return None
        now_y = datetime.utcnow().year + 1
        for m in re.finditer(r'\b(19[89]\d|20\d{2})\b', text):
            y = int(m.group(1))
            if 1980 <= y <= now_y:
                return y
        return None
    
    def get_full_item_details(self, item_id: str) -> Optional[Dict]:
        """
        Get full item details including card number and all aspects
        
        Args:
            item_id: eBay item ID (e.g., "v1|123456789|0")
            
        Returns:
            Dictionary with card_number, parallel, grade_company, grade_value, player_name,
            image_urls (ordered CDN URLs from Browse GET /item for gallery / vision).
            
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
            
            data = self._extract_from_aspects(aspects)
            data['image_urls'] = collect_browse_item_image_urls(item_data)
            need_blob = (not data.get('card_number')) or (not data.get('card_year'))
            blob = self._item_description_plain_text(item_data) if need_blob else ''
            if blob:
                if not data.get('card_number'):
                    toks = card_number_tokens_from_free_text(blob)
                    if toks:
                        data['card_number'] = toks[0]
                if not data.get('card_year'):
                    y = self._first_reasonable_year_in_text(blob)
                    if y is not None:
                        data['card_year'] = y
            return data
            
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
                val = value if value else 'Base'
                # Strip brackets if eBay returns "[Base]" literally
                if isinstance(val, str) and val.startswith('[') and val.endswith(']'):
                    val = val[1:-1]
                data['parallel'] = val
            
            # Grading
            elif name in ['Professional Grader', 'Grader']:
                data['grade_company'] = value
            elif name == 'Grade':
                try:
                    data['grade_value'] = float(value)
                except (ValueError, TypeError):
                    pass
            
            # Card details
            elif name in ('Player', 'Player/Athlete', 'Athlete', 'Player Name'):
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
    
    def get_active_listings(self, query: str, max_total: int = 1000) -> List[Dict]:
        """
        Get current active listings (BIN + auction) for a query.

        Paginates with ``offset`` (200 per page) up to ``max_total`` (default 1000),
        matching auction pipeline depth for opportunity coverage.
        """
        all_items: List[Dict] = []
        seen_ids: set = set()
        offset = 0

        try:
            while offset < max_total:
                params = {
                    "q": query,
                    "filter": "buyingOptions:{AUCTION|FIXED_PRICE}",
                    "limit": 200,
                    "offset": offset,
                }
                self.headers["Authorization"] = f"Bearer {self.token_manager.get_token()}"
                response = requests.get(
                    f"{self.base_url}/item_summary/search",
                    headers=self.headers,
                    params=params,
                    timeout=30,
                )
                if response.status_code == 401:
                    self.token_manager._refresh_token()
                    self.headers["Authorization"] = f"Bearer {self.token_manager.get_token()}"
                    response = requests.get(
                        f"{self.base_url}/item_summary/search",
                        headers=self.headers,
                        params=params,
                        timeout=30,
                    )
                response.raise_for_status()
                time.sleep(0.5)

                page = response.json().get("itemSummaries", []) or []
                for item in page:
                    iid = item.get("itemId")
                    if not iid or iid in seen_ids:
                        continue
                    seen_ids.add(iid)
                    card_info = self._extract_card_info(item.get("title", ""), item.get("condition"))
                    image_urls = collect_browse_item_image_urls(item)
                    image_url = image_urls[0] if image_urls else None
                    all_items.append({
                        "ebay_item_id": iid,
                        "title": item.get("title"),
                        "price": float(item.get("price", {}).get("value", 0)),
                        "listing_type": (
                            "auction" if "AUCTION" in item.get("buyingOptions", []) else "buy_it_now"
                        ),
                        "card_info": card_info,
                        "image_url": image_url,
                        "image_urls": image_urls,
                    })
                if len(page) < 200:
                    break
                offset += 200

            return all_items
        except requests.exceptions.RequestException as e:
            print(f"Error fetching active listings: {e}")
            return []

    def search_active_bin_comps(self, query: str, category_id: str = '261328') -> List[Dict]:
        """Search active BIN listings as market comps for a specific card.

        Returns BIN prices only (no auctions) for calculating median market value.
        Used as fallback when SCP has no matching variant.

        Args:
            query: Specific card search (e.g. "Juan Soto 2026 Topps Mojo Refractor #91C-44")
            category_id: eBay category (default 261328 = Trading Card Singles)

        Returns:
            List of dicts with price, title, condition, listing_type
        """
        filter_str = f"buyingOptions:{{FIXED_PRICE}}"
        if category_id:
            filter_str += f",categoryId:{{{category_id}}}"

        params = {
            "q": query,
            "filter": filter_str,
            "sort": "price",
            "limit": 50,
        }

        try:
            self.headers["Authorization"] = f"Bearer {self.token_manager.get_token()}"
            response = requests.get(
                f"{self.base_url}/item_summary/search",
                headers=self.headers,
                params=params,
                timeout=30,
            )
            if response.status_code == 401:
                self.token_manager._refresh_token()
                self.headers["Authorization"] = f"Bearer {self.token_manager.get_token()}"
                response = requests.get(
                    f"{self.base_url}/item_summary/search",
                    headers=self.headers,
                    params=params,
                    timeout=30,
                )
            response.raise_for_status()
            time.sleep(0.5)

            results = []
            for item in response.json().get('itemSummaries', []):
                price = float(item.get('price', {}).get('value', 0))
                if price < 1.0:
                    continue
                buying = item.get('buyingOptions', [])
                if 'AUCTION' in buying and 'FIXED_PRICE' not in buying:
                    continue
                results.append({
                    'price': price,
                    'title': item.get('title', ''),
                    'condition': item.get('condition', 'Ungraded'),
                })
            return results
        except requests.exceptions.RequestException as e:
            print(f"Error fetching BIN comps for '{query}': {e}")
            return []

    def search_auctions_ending_soon(
        self,
        query: str,
        hours: int = 48,
        offset: int = 0,
        category_id: str = '261328',
        meta_out: Optional[dict] = None,
    ) -> List[Dict]:
        """
        Search for auction-only listings ending within `hours`.

        Returns richer data than get_active_listings: shipping cost,
        bid count, end time, and item aspects (for card number extraction).

        Args:
            query: Search term (e.g. "2024 Topps Chrome")
            hours: Max hours until auction ends (default 48)
            offset: Pagination offset
            category_id: eBay category (default 261328 = Trading Card Singles)

        Returns:
            List of auction dicts with title, price, shipping, bid_count,
            end_time, card_info, image_url, ebay_item_id, aspects
        """
        end_deadline = datetime.now() + timedelta(hours=hours)

        filter_str = f"buyingOptions:{{AUCTION}},itemEndDate:[..{_browse_datetime_utc_z(end_deadline)}]"
        if category_id:
            filter_str += f",categoryId:{{{category_id}}}"

        params = {
            "q": query,
            "filter": filter_str,
            "sort": "endTimeSoonest",
            "limit": 200,
            "offset": offset,
            "fieldgroups": "EXTENDED",
        }

        try:
            self.headers["Authorization"] = f"Bearer {self.token_manager.get_token()}"

            response = None
            for attempt in range(6):
                if attempt > 0:
                    time.sleep(1.0)
                response = requests.get(
                    f"{self.base_url}/item_summary/search",
                    headers=self.headers,
                    params=params,
                    timeout=30,
                )

                if response.status_code == 401:
                    self.token_manager._refresh_token()
                    self.headers["Authorization"] = f"Bearer {self.token_manager.get_token()}"
                    response = requests.get(
                        f"{self.base_url}/item_summary/search",
                        headers=self.headers,
                        params=params,
                        timeout=30,
                    )

                if response.status_code == 429:
                    try:
                        ra = int(response.headers.get("Retry-After", "60"))
                    except ValueError:
                        ra = 60
                    wait = min(max(ra, 5), 120)
                    if attempt < 5:
                        print(f"  eBay 429 rate limit — sleeping {wait}s then retry ({attempt + 1}/5)...")
                        time.sleep(wait)
                        continue
                    response.raise_for_status()

                response.raise_for_status()
                break

            time.sleep(0.5)

            data = response.json()
            if meta_out is not None and offset == 0:
                t = data.get('total')
                if t is not None:
                    try:
                        meta_out['ebay_total'] = int(t)
                    except (TypeError, ValueError):
                        meta_out['ebay_total'] = t

            items = []

            for item in data.get('itemSummaries', []):
                title = item.get('title', '')
                if not title:
                    continue

                price = float(item.get('price', {}).get('value', 0))
                if price < 1.0:
                    continue

                # Shipping
                shipping = 0.0
                ship_opts = item.get('shippingOptions', [])
                if ship_opts:
                    cost = ship_opts[0].get('shippingCost', {})
                    shipping = float(cost.get('value', 0))

                # Bid count
                bid_count = item.get('bidCount', 0)

                # End time
                end_time = item.get('itemEndDate')

                image_urls = collect_browse_item_image_urls(item)
                image_url = image_urls[0] if image_urls else None

                card_info = self._extract_card_info(title, item.get('condition'))

                # Item aspects from EXTENDED fieldgroup
                aspects = {}
                for aspect in item.get('localizedAspects', []):
                    name = aspect.get('name', '')
                    val = aspect.get('value', '')
                    if isinstance(val, list):
                        val = val[0] if val else ''
                    aspects[name] = val

                short_plain = self._html_to_plain(
                    self._coerce_browse_text(item.get('shortDescription'))
                )

                # Check actual buyingOptions -- eBay returns hybrid listings
                buying_options = item.get('buyingOptions', [])
                if 'FIXED_PRICE' in buying_options and 'AUCTION' not in buying_options:
                    continue  # Pure BIN -- skip, not an auction

                listing_type = 'auction'
                bin_price = None
                current_bid = price  # default: eBay's price field
                if 'FIXED_PRICE' in buying_options and 'AUCTION' in buying_options:
                    listing_type = 'auction_bin'  # Hybrid -- auction with BIN option
                    # For hybrids, price field is BIN. currentBidPrice is the actual bid.
                    bid_obj = item.get('currentBidPrice', {})
                    if bid_obj and bid_obj.get('value'):
                        bin_price = price  # Store BIN separately
                        current_bid = float(bid_obj['value'])

                items.append({
                    'ebay_item_id': item.get('itemId'),
                    'title': title,
                    'price': current_bid,
                    'bin_price': bin_price,
                    'shipping': shipping,
                    'bid_count': bid_count,
                    'end_time': end_time,
                    'listing_type': listing_type,
                    'card_info': card_info,
                    'aspects': aspects,
                    'image_url': image_url,
                    'image_urls': image_urls,
                    'condition': item.get('condition'),
                    'short_description': short_plain or None,
                })

            return items
        except requests.exceptions.RequestException as e:
            print(f"Error fetching auctions for '{query}': {e}")
            time.sleep(2.0)  # avoid tight loop of failures (e.g. 429 after retries exhausted)
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
