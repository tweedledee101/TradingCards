"""
NovaAct PWCC Scraper Template

This template should be run in NovaAct to scrape PWCC auction results.
NovaAct will handle the browser automation and send results via webhook.

Target URL: https://www.pwccmarketplace.com (find correct sold lots page)

Data to Extract:
- Card title/description
- Sale price
- Sale date
- Player name (from title)
- Card year
- Card set
- Sport

Webhook Endpoint: POST http://localhost:8000/api/webhooks/novaact/pwcc

Expected JSON Format:
{
    "player_name": "Victor Wembanyama",
    "sport": "Basketball",
    "card_year": 2023,
    "card_set": "Prizm",
    "sale_price": 450.00,
    "sale_date": "2026-02-13",
    "is_rookie": true,
    "graded": true,
    "title": "2023 Panini Prizm Victor Wembanyama RC PSA 10"
}

Instructions for NovaAct:
1. Navigate to PWCC sold lots page
2. Extract recent sales (last 7 days)
3. For each sale, extract the data above
4. POST each sale to the webhook endpoint
5. Run daily at 12:00 AM (before discovery at 1:00 AM)

NovaAct Configuration:
- Schedule: Daily at 12:00 AM
- Retry: 3 attempts on failure
- Timeout: 30 minutes
- Rate limit: 1 request per second to webhook
"""

# This is a template file - actual scraping happens in NovaAct
# The webhook endpoint below receives the data

print("""
NovaAct PWCC Scraper Template

Setup Instructions:
1. Copy this template to NovaAct
2. Configure NovaAct to scrape PWCC sold lots
3. Set webhook URL: http://localhost:8000/api/webhooks/novaact/pwcc
4. Schedule: Daily at 12:00 AM
5. Test with a few sales first

Expected Data Format:
{
    "player_name": "Victor Wembanyama",
    "sport": "Basketball", 
    "card_year": 2023,
    "card_set": "Prizm",
    "sale_price": 450.00,
    "sale_date": "2026-02-13",
    "is_rookie": true,
    "graded": true,
    "title": "2023 Panini Prizm Victor Wembanyama RC PSA 10"
}

Webhook Endpoint: POST /api/webhooks/novaact/pwcc
""")
