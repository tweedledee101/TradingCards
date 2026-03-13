# eBay API Fields for Variant Detection

## Problem
Currently parsing titles for variant info (parallel, grade). This is unreliable and leads to "Unknown" values.

## eBay Browse API - Available Fields

According to eBay Browse API documentation, each item has:

### Item Summary Fields
```json
{
  "itemId": "v1|123456789|0",
  "title": "2023 Panini Prizm Victor Wembanyama Silver RC PSA 10",
  "price": {
    "value": "245.00",
    "currency": "USD"
  },
  "condition": "Graded",  // or "New", "Used", etc.
  "itemEndDate": "2026-02-17T10:30:00.000Z",
  "buyingOptions": ["FIXED_PRICE"],
  
  // IMPORTANT: These fields contain structured variant data
  "localizedAspects": [
    {
      "name": "Player",
      "value": "Victor Wembanyama"
    },
    {
      "name": "Parallel/Variety",
      "value": "Silver"
    },
    {
      "name": "Grade",
      "value": "10"
    },
    {
      "name": "Professional Grader",
      "value": "PSA"
    },
    {
      "name": "Year",
      "value": "2023"
    },
    {
      "name": "Set",
      "value": "Prizm"
    }
  ]
}
```

## Solution

Instead of parsing titles, extract from `localizedAspects`:
- **Parallel**: Look for "Parallel/Variety" aspect
- **Grade Company**: Look for "Professional Grader" aspect  
- **Grade Value**: Look for "Grade" aspect
- **Player**: Look for "Player" aspect
- **Year**: Look for "Year" aspect
- **Set**: Look for "Set" aspect

## Implementation

Update `ebay_scraper.py`:
1. Use `_get_player_from_product()` to fetch full item details
2. Extract `localizedAspects` from response
3. Parse aspects for structured data
4. Fall back to title parsing only if aspects missing

## Benefits
- More accurate variant detection
- Fewer "Unknown" values
- No regex parsing errors
- Uses eBay's structured data

## Note
This requires calling the full item endpoint (`/buy/browse/v1/item/{item_id}`) which costs 1 additional API call per item. 

**Trade-off**: More API calls but much better data quality.

**Alternative**: Only fetch full details for items we want to save (after initial filtering).
