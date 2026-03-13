"""
NovaAct eBay Scraper Template

Scrapes eBay WEBSITE (not API) for sold listings.
Bypasses API rate limits by scraping HTML directly.

Target URL: https://www.ebay.com/sch/i.html?_nkw={PLAYER_NAME}+rookie&_sacat=0&LH_Sold=1&LH_Complete=1

Data to Extract from each listing:
- Title
- Sale price
- Sale date
- Condition (graded/ungraded)
- Item ID

Webhook Endpoint: POST http://localhost:8000/api/webhooks/novaact/ebay

Expected JSON Format:
{
    "player_name": "Victor Wembanyama",
    "title": "2023 Panini Prizm Victor Wembanyama RC PSA 10",
    "sale_price": 450.00,
    "sale_date": "2026-02-10",
    "ebay_item_id": "123456789",
    "condition": "Graded",
    "card_year": 2023,
    "card_set": "Prizm",
    "is_rookie": true,
    "graded": true,
    "grade_company": "PSA",
    "grade_value": 10.0
}

Instructions for NovaAct:
1. Read targets from: config/targets.yaml
2. For each player, search eBay sold listings
3. Extract last 30 days of sales
4. POST each sale to webhook
5. Run daily at 2:00 AM

NovaAct Configuration:
- Schedule: Daily at 2:00 AM
- Retry: 3 attempts on failure
- Timeout: 60 minutes
- Rate limit: 1 request per 2 seconds to webhook
- User agent rotation: Enabled
- Proxy rotation: Optional but recommended

eBay Search URL Pattern:
https://www.ebay.com/sch/i.html?_nkw={PLAYER_NAME}+rookie+PSA&_sacat=0&LH_Sold=1&LH_Complete=1&_sop=13

CSS Selectors (may need adjustment):
- Listing container: .s-item
- Title: .s-item__title
- Price: .s-item__price
- Date: .s-item__endedDate
- Item ID: data-itemid attribute
"""

print("""
NovaAct eBay Website Scraper Template

This scrapes eBay's WEBSITE (not API) to bypass rate limits.

Setup Instructions:
1. Copy this template to NovaAct
2. Configure NovaAct to read config/targets.yaml
3. For each player in targets, scrape eBay sold listings
4. Set webhook URL: http://localhost:8000/api/webhooks/novaact/ebay
5. Schedule: Daily at 2:00 AM
6. Enable user agent rotation to avoid detection

eBay Search URL:
https://www.ebay.com/sch/i.html?_nkw={PLAYER}+rookie+PSA&LH_Sold=1&LH_Complete=1

Expected Data Per Sale:
{
    "player_name": "Victor Wembanyama",
    "title": "2023 Panini Prizm Victor Wembanyama RC PSA 10",
    "sale_price": 450.00,
    "sale_date": "2026-02-10",
    "ebay_item_id": "123456789",
    "condition": "Graded",
    "card_year": 2023,
    "card_set": "Prizm",
    "is_rookie": true,
    "graded": true,
    "grade_company": "PSA",
    "grade_value": 10.0
}

Webhook: POST /api/webhooks/novaact/ebay

This bypasses eBay API rate limits completely!
""")
