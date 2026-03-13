# Action Plan: Use eBay Structured Fields for Variants

## Current Problem
- Parsing titles with regex → unreliable
- Many "Unknown" values for parallel, grade
- User is correct: should use eBay's structured data

## eBay API Provides Structured Fields

The `localizedAspects` field contains:
- `Parallel/Variety` → parallel type
- `Professional Grader` → grade company (PSA, BGS, SGC)
- `Grade` → grade value (9, 10, etc.)
- `Player` → player name
- `Year` → card year
- `Set` → card set

## Implementation Plan

### Step 1: Update eBay Scraper
Modify `_parse_results()` to:
1. For each item, call `_get_player_from_product(item_id)` 
2. Extract `localizedAspects` from full item response
3. Parse aspects for parallel, grade, player, year, set
4. Only fall back to title parsing if aspects missing

### Step 2: Handle API Call Cost
- Full item details = 1 extra API call per item
- With 200 items per search, this doubles API usage
- **Solution**: Only fetch full details for items we'll save (after filtering)

### Step 3: Update Extraction Logic
```python
def _extract_from_aspects(self, aspects):
    data = {
        'parallel': 'Base',
        'grade_company': 'Raw',
        'grade_value': None,
        'player_name': None,
        'card_year': None,
        'card_set': None
    }
    
    for aspect in aspects:
        name = aspect.get('name', '')
        value = aspect.get('value', '')
        
        if name == 'Parallel/Variety':
            data['parallel'] = value
        elif name == 'Professional Grader':
            data['grade_company'] = value
        elif name == 'Grade':
            data['grade_value'] = float(value)
        elif name == 'Player':
            data['player_name'] = value
        elif name == 'Year':
            data['card_year'] = int(value)
        elif name == 'Set':
            data['card_set'] = value
    
    return data
```

## When to Implement
- **After eBay API limit resets** (midnight PST)
- Test with real data to see aspect field coverage
- Measure how many items have complete aspect data vs need title parsing

## Expected Improvement
- 80-90% of cards will have accurate variant data
- Remaining 10-20% fall back to title parsing
- Much better than current 100% title parsing
