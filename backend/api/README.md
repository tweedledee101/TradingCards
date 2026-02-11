# REST API Documentation

FastAPI-based REST API for the Trading Card Platform.

## Quick Start

### 1. Start the API Server
```bash
# Option 1: Using Python
python -m backend.api.run

# Option 2: Using uvicorn directly
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Access the API
- **API Base URL:** http://localhost:8000
- **Interactive Docs (Swagger):** http://localhost:8000/docs
- **Alternative Docs (ReDoc):** http://localhost:8000/redoc

## Endpoints

### Health Check
```
GET /health
```
Check if API is running.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-02-11T10:30:00",
  "service": "trading-card-api"
}
```

### Get Trending Cards
```
GET /api/trending?limit=10
```
Get top trending cards by hotness score.

**Query Parameters:**
- `limit` (optional): Number of cards to return (1-100, default: 10)

**Response:**
```json
{
  "count": 10,
  "cards": [
    {
      "player_name": "Victor Wembanyama",
      "card_year": 2023,
      "card_set": "Prizm",
      "is_rookie": true,
      "avg_price": 450.00,
      "sales_count": 15,
      "velocity_score": 187.5,
      "hotness_score": 85.3,
      "category": "🔥 FIRE"
    }
  ]
}
```

### Get Trending Rookies
```
GET /api/trending/rookies?limit=10
```
Get top trending rookie cards only.

**Query Parameters:**
- `limit` (optional): Number of cards to return (1-100, default: 10)

**Response:** Same format as `/api/trending`

### Get Card Details
```
GET /api/cards/{card_id}
```
Get detailed information about a specific card.

**Response:**
```json
{
  "id": 1,
  "player_name": "Victor Wembanyama",
  "card_year": 2023,
  "card_set": "Prizm",
  "card_number": "1",
  "is_rookie": true,
  "sport": "Basketball",
  "recent_sales": [
    {
      "price": 450.00,
      "date": "2025-02-10T15:30:00",
      "graded": true,
      "grade_company": "PSA",
      "grade_value": 10.0
    }
  ],
  "trend": {
    "avg_price": 450.00,
    "sales_count": 15,
    "velocity_score": 187.5,
    "hotness_score": 85.3,
    "trend_date": "2025-02-11"
  },
  "active_listings_count": 8
}
```

### Search Cards
```
GET /api/cards?player=Wembanyama&year=2023&rookie_only=true&limit=20
```
Search for cards by player name, year, or rookie status.

**Query Parameters:**
- `player` (optional): Player name (partial match)
- `year` (optional): Card year
- `rookie_only` (optional): Only return rookie cards (default: false)
- `limit` (optional): Number of results (default: 20)

**Response:**
```json
{
  "count": 5,
  "cards": [
    {
      "id": 1,
      "player_name": "Victor Wembanyama",
      "card_year": 2023,
      "card_set": "Prizm",
      "is_rookie": true,
      "sport": "Basketball"
    }
  ]
}
```

## Usage Examples

### cURL
```bash
# Get trending cards
curl http://localhost:8000/api/trending?limit=5

# Get card details
curl http://localhost:8000/api/cards/1

# Search for cards
curl "http://localhost:8000/api/cards?player=Wembanyama&rookie_only=true"
```

### Python
```python
import requests

# Get trending cards
response = requests.get("http://localhost:8000/api/trending", params={"limit": 10})
trending = response.json()

for card in trending["cards"]:
    print(f"{card['player_name']}: Hotness {card['hotness_score']}")

# Get card details
response = requests.get("http://localhost:8000/api/cards/1")
card = response.json()
print(f"Average price: ${card['trend']['avg_price']}")
```

### JavaScript
```javascript
// Get trending cards
fetch('http://localhost:8000/api/trending?limit=10')
  .then(response => response.json())
  .then(data => {
    data.cards.forEach(card => {
      console.log(`${card.player_name}: ${card.hotness_score}`);
    });
  });
```

## Error Responses

### 404 Not Found
```json
{
  "detail": "Card not found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["query", "limit"],
      "msg": "ensure this value is less than or equal to 100",
      "type": "value_error"
    }
  ]
}
```

## CORS

CORS is enabled for all origins in development. Update `backend/api/main.py` for production.

## Next Steps

- [ ] Add authentication
- [ ] Add rate limiting
- [ ] Add caching
- [ ] Add pagination
- [ ] Add filtering by sport
- [ ] Add price history endpoint
- [ ] Add WebSocket for real-time updates
