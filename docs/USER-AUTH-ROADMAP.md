# User Authentication & eBay OAuth - Roadmap

**Priority:** Phase 5 (After Frontend MVP)  
**Status:** Planned

## Overview

Allow users to register accounts and connect their own eBay accounts via OAuth, enabling personalized card tracking and collections.

## Features

### Phase 1: Basic User Auth
- [ ] User registration (email/password)
- [ ] Login/logout
- [ ] JWT token authentication
- [ ] Password reset flow
- [ ] Email verification

### Phase 2: eBay OAuth Integration
- [ ] "Connect eBay Account" button
- [ ] eBay OAuth 2.0 flow
- [ ] Store user tokens securely
- [ ] Token refresh automation
- [ ] Handle token expiration

### Phase 3: Per-User Features
- [ ] Personal card collections
- [ ] Custom watchlists
- [ ] Price alerts
- [ ] Email notifications
- [ ] User preferences

## Technical Implementation

### Database Schema

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    email_verified BOOLEAN DEFAULT FALSE
);

-- eBay connections
CREATE TABLE ebay_connections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    ebay_user_id VARCHAR(255),
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- User watchlists
CREATE TABLE user_watchlists (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    card_id INTEGER REFERENCES cards(id),
    alert_price DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, card_id)
);

-- User collections
CREATE TABLE user_collections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    card_id INTEGER REFERENCES cards(id),
    purchase_price DECIMAL(10, 2),
    purchase_date DATE,
    quantity INTEGER DEFAULT 1,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Backend API Endpoints

```python
# Authentication
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
POST /api/auth/refresh
POST /api/auth/reset-password

# eBay OAuth
GET  /api/ebay/connect          # Redirect to eBay OAuth
GET  /api/ebay/callback         # eBay redirects here
POST /api/ebay/disconnect
GET  /api/ebay/status

# User Features
GET  /api/user/profile
PUT  /api/user/profile
GET  /api/user/watchlist
POST /api/user/watchlist
DELETE /api/user/watchlist/{id}
GET  /api/user/collection
POST /api/user/collection
```

### Frontend Components

```
src/
├── pages/
│   ├── Login.jsx
│   ├── Register.jsx
│   ├── Dashboard.jsx
│   ├── Watchlist.jsx
│   └── Collection.jsx
├── components/
│   ├── Auth/
│   │   ├── LoginForm.jsx
│   │   ├── RegisterForm.jsx
│   │   └── ProtectedRoute.jsx
│   └── eBay/
│       ├── ConnectButton.jsx
│       └── ConnectionStatus.jsx
```

## eBay OAuth Flow

### 1. User Clicks "Connect eBay"
```javascript
// Frontend
const connectEbay = () => {
  window.location.href = '/api/ebay/connect';
};
```

### 2. Backend Redirects to eBay
```python
@router.get("/ebay/connect")
def connect_ebay(current_user: User):
    redirect_uri = "https://cards.jgaffiliates.com/api/ebay/callback"
    ebay_auth_url = f"https://auth.ebay.com/oauth2/authorize?client_id={EBAY_APP_ID}&redirect_uri={redirect_uri}&response_type=code&scope=https://api.ebay.com/oauth/api_scope"
    return RedirectResponse(ebay_auth_url)
```

### 3. eBay Redirects Back with Code
```python
@router.get("/ebay/callback")
def ebay_callback(code: str, current_user: User):
    # Exchange code for tokens
    tokens = exchange_code_for_tokens(code)
    
    # Store in database
    save_ebay_connection(
        user_id=current_user.id,
        access_token=tokens['access_token'],
        refresh_token=tokens['refresh_token'],
        expires_at=tokens['expires_at']
    )
    
    return RedirectResponse("/dashboard?ebay=connected")
```

### 4. Use User's Token for API Calls
```python
def get_user_ebay_token(user_id: int):
    connection = db.query(EbayConnection).filter(
        EbayConnection.user_id == user_id
    ).first()
    
    # Check if expired
    if connection.token_expires_at < datetime.now():
        # Refresh token
        new_tokens = refresh_ebay_token(connection.refresh_token)
        connection.access_token = new_tokens['access_token']
        connection.token_expires_at = new_tokens['expires_at']
        db.commit()
    
    return connection.access_token
```

## Security Considerations

- [ ] Hash passwords with bcrypt
- [ ] Use HTTPS only
- [ ] Implement rate limiting
- [ ] Validate email addresses
- [ ] Secure token storage (encrypted)
- [ ] CSRF protection
- [ ] XSS prevention
- [ ] SQL injection prevention (use ORM)

## Benefits

### For Users:
- Personal card tracking
- Custom alerts
- Private collections
- No shared API limits
- Track purchase history

### For Platform:
- User engagement
- Recurring users
- Monetization potential (premium features)
- User data for analytics
- Community features

## Monetization Options (Future)

- **Free Tier:** Basic tracking, 10 watchlist items
- **Pro Tier ($5/month):** Unlimited watchlist, price alerts, email notifications
- **Premium Tier ($15/month):** Advanced analytics, portfolio tracking, API access

## Timeline

**Phase 5 (Month 3-4):**
- Week 1-2: User authentication backend
- Week 3-4: eBay OAuth integration
- Week 5-6: Frontend auth pages
- Week 7-8: User features (watchlist, collections)

## Dependencies

- Frontend dashboard (Phase 4)
- REST API (Phase 2) ✅
- Database (Phase 1) ✅

## References

- [eBay OAuth Documentation](https://developer.ebay.com/api-docs/static/oauth-tokens.html)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [OAuth 2.0 Spec](https://oauth.net/2/)

---

**Status:** Planned for Phase 5  
**Next:** Complete frontend MVP first
