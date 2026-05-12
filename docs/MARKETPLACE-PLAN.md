# Ragnarok Gaming - Marketplace Platform Plan

## Vision
Ragnarok Gaming becomes a multi-seller trading card marketplace where users can list and sell their cards, while the admin team uses proprietary arbitrage tools to source inventory.

## Roles & Access

### Admin (Joshua, designated team members)
- Full access to everything
- Opportunities page (arbitrage finder)
- Business dashboard (P&L, capital, goals)
- Pipeline controls (run/stop/configure)
- User management
- Site configuration

### Seller (registered users)
- List their own cards for sale on ragnarokgamez.com
- Manage their inventory (add, edit, remove listings)
- View their own sales history and analytics
- Connect their eBay account (import listings)
- Set pricing, shipping options
- Receive notifications on sales/offers

### Buyer (public, no account required)
- Browse the shop
- Search/filter cards
- Click through to purchase (eBay or on-site)
- View card details, images, pricing

### Buyer (registered)
- Everything above plus:
- Save favorites/watchlist
- Get price drop alerts
- Purchase history
- Leave reviews/ratings for sellers

---

## User Stories

### Seller Stories
1. As a seller, I want to create an account so I can list my cards for sale.
2. As a seller, I want to connect my eBay account so my existing listings appear on Ragnarok automatically.
3. As a seller, I want to manually add a card listing with photos, price, and description.
4. As a seller, I want to see how many views my listings get.
5. As a seller, I want to be notified when someone purchases my card.
6. As a seller, I want to set my own shipping rates and policies.
7. As a seller, I want to see my total sales, revenue, and fees.
8. As a seller, I want to edit or remove my listings at any time.
9. As a seller, I want my cards to appear in search results alongside other sellers.

### Buyer Stories
1. As a buyer, I want to browse all cards for sale across all sellers.
2. As a buyer, I want to search by player, year, set, parallel, sport.
3. As a buyer, I want to filter by price range, condition, graded/raw.
4. As a buyer, I want to see the seller's rating and feedback.
5. As a buyer, I want to click "Buy" and be taken to complete the purchase.
6. As a buyer, I want to save cards to a wishlist for later.
7. As a buyer, I want to get notified when a card I'm watching drops in price.

### Admin Stories
1. As an admin, I want to access the arbitrage opportunity finder.
2. As an admin, I want to see business dashboards (P&L, capital, pipeline health).
3. As an admin, I want to manage users (approve sellers, ban bad actors).
4. As an admin, I want to configure pipeline settings without code changes.
5. As an admin, I want to see all seller activity and platform metrics.
6. As an admin, I want to feature/promote specific listings on the homepage.

---

## Business Cases

### Revenue Streams
1. **Seller fees** -- % commission on sales made through the platform (5-10%)
2. **Featured listings** -- sellers pay to boost visibility ($2-5/listing)
3. **Premium seller tools** -- analytics, pricing suggestions, bulk listing ($9.99/mo)
4. **Direct sales** -- admin's own inventory sold through the shop
5. **eBay affiliate** -- commission on clicks through to eBay purchases

### Cost Structure
- AWS infrastructure (RDS, Lambda, S3, CloudFront) -- ~$50-100/mo
- Nova/Bedrock API calls -- ~$10-30/mo
- eBay API (free with Compatible Application status)
- Domain/SSL -- ~$15/yr

### Competitive Advantage
- Arbitrage tools (no other marketplace has this)
- SCP price integration (instant market value on every card)
- Volume data (know which cards actually sell)
- Multi-platform (eBay listings + native listings in one place)

---

## Technical Architecture

### Authentication & Authorization
- **Cognito** (already deployed: `us-east-1_7WksfnG6T`)
- User pools: buyers, sellers, admins
- Groups: `admin`, `seller`, `buyer`
- Custom attributes: `seller_approved`, `ebay_connected`
- JWT tokens with role claims for API authorization

### API Authorization Middleware
```python
# Route protection by role
@require_role('admin')      # Opportunities, Business Dashboard, Pipeline
@require_role('seller')     # Inventory management, listing CRUD
@require_auth              # Any logged-in user (watchlist, purchase history)
# No decorator             # Public routes (shop browse, search)
```

### Database Schema Additions
```sql
-- Seller profiles
CREATE TABLE seller_profiles (
    id SERIAL PRIMARY KEY,
    cognito_user_id TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    bio TEXT,
    avatar_url TEXT,
    ebay_username TEXT,
    ebay_refresh_token TEXT,  -- encrypted
    approved BOOLEAN DEFAULT FALSE,
    rating NUMERIC(3,2) DEFAULT 0,
    total_sales INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Listings (multi-seller)
CREATE TABLE listings (
    id SERIAL PRIMARY KEY,
    seller_id INTEGER REFERENCES seller_profiles(id),
    title TEXT NOT NULL,
    description TEXT,
    player_name TEXT,
    card_year INTEGER,
    card_set TEXT,
    card_number TEXT,
    parallel TEXT,
    condition TEXT,  -- Raw, PSA 10, BGS 9.5, etc.
    price NUMERIC(10,2) NOT NULL,
    shipping_cost NUMERIC(6,2) DEFAULT 0,
    quantity INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active',  -- active, sold, removed, draft
    source TEXT DEFAULT 'manual',  -- manual, ebay_import
    ebay_item_id TEXT,
    ebay_url TEXT,
    image_urls JSONB DEFAULT '[]',
    sport TEXT DEFAULT 'Baseball',
    views INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Orders
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    listing_id INTEGER REFERENCES listings(id),
    buyer_cognito_id TEXT,
    seller_id INTEGER REFERENCES seller_profiles(id),
    amount NUMERIC(10,2) NOT NULL,
    platform_fee NUMERIC(10,2),
    status TEXT DEFAULT 'pending',  -- pending, paid, shipped, delivered, cancelled
    shipping_tracking TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Reviews
CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    reviewer_cognito_id TEXT NOT NULL,
    seller_id INTEGER REFERENCES seller_profiles(id),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Watchlist (buyer)
CREATE TABLE user_watchlist (
    id SERIAL PRIMARY KEY,
    cognito_user_id TEXT NOT NULL,
    listing_id INTEGER REFERENCES listings(id),
    target_price NUMERIC(10,2),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Directory Structure (Proposed Refactor)

```
TradingCards/
├── backend/
│   ├── api/
│   │   ├── main.py
│   │   ├── middleware/
│   │   │   ├── auth.py              # JWT validation, role checking
│   │   │   └── cors.py
│   │   ├── routes/
│   │   │   ├── public/              # No auth required
│   │   │   │   ├── shop.py          # Browse, search, card detail
│   │   │   │   ├── health.py
│   │   │   │   └── auth_callbacks.py # eBay OAuth callback
│   │   │   ├── authenticated/       # Any logged-in user
│   │   │   │   ├── watchlist.py
│   │   │   │   ├── profile.py
│   │   │   │   └── orders.py
│   │   │   ├── seller/              # Seller role required
│   │   │   │   ├── listings.py      # CRUD for seller's own listings
│   │   │   │   ├── inventory.py     # Manage stock
│   │   │   │   ├── analytics.py     # Seller's own stats
│   │   │   │   └── ebay_sync.py     # Import from eBay
│   │   │   └── admin/               # Admin role required
│   │   │       ├── opportunities.py
│   │   │       ├── business.py
│   │   │       ├── pipeline.py      # Start/stop/configure
│   │   │       ├── users.py         # User management
│   │   │       └── platform.py      # Site-wide metrics
│   │   └── schemas/                 # Pydantic models
│   │       ├── listing.py
│   │       ├── order.py
│   │       ├── user.py
│   │       └── opportunity.py
│   ├── services/
│   │   ├── match_engine.py          # Card matching (existing)
│   │   ├── listing_service.py       # Listing CRUD logic
│   │   ├── order_service.py         # Purchase flow
│   │   ├── ebay_sync_service.py     # Pull seller's eBay listings
│   │   ├── notification_service.py  # Email/push alerts
│   │   ├── pricing_service.py       # SCP price lookups
│   │   └── search_service.py        # Full-text search across listings
│   ├── pipeline/                    # Arbitrage pipeline (admin only)
│   │   ├── auction_v2.py            # Main pipeline
│   │   ├── worm_scp.py             # SCP price refresh
│   │   ├── worm_130point.py        # Sold comps
│   │   └── scheduler.py            # Cron management
│   ├── models/
│   │   ├── __init__.py
│   │   ├── listing.py
│   │   ├── order.py
│   │   ├── seller.py
│   │   ├── opportunity.py
│   │   └── migrations/
│   ├── config/
│   │   └── settings.py
│   └── utils/
│       ├── database.py
│       ├── auth.py                  # Cognito token validation
│       ├── encryption.py            # For storing eBay tokens
│       └── logger.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── auth/
│   │   │   ├── AuthContext.jsx
│   │   │   ├── ProtectedRoute.jsx
│   │   │   └── RoleGate.jsx         # Show/hide based on role
│   │   ├── pages/
│   │   │   ├── public/
│   │   │   │   ├── Landing.jsx       # Marketing/homepage
│   │   │   │   ├── Shop.jsx          # Browse all listings
│   │   │   │   ├── CardDetail.jsx    # Single listing view
│   │   │   │   ├── SellerProfile.jsx # Public seller page
│   │   │   │   └── Privacy.jsx
│   │   │   ├── authenticated/
│   │   │   │   ├── Watchlist.jsx
│   │   │   │   ├── Profile.jsx
│   │   │   │   └── Orders.jsx
│   │   │   ├── seller/
│   │   │   │   ├── Dashboard.jsx     # Seller home
│   │   │   │   ├── MyListings.jsx    # Manage listings
│   │   │   │   ├── AddListing.jsx    # Create new listing
│   │   │   │   ├── Analytics.jsx     # Sales stats
│   │   │   │   └── EbaySync.jsx      # Import from eBay
│   │   │   └── admin/
│   │   │       ├── Opportunities.jsx
│   │   │       ├── Business.jsx
│   │   │       ├── Pipeline.jsx
│   │   │       ├── Users.jsx
│   │   │       └── Platform.jsx
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── PublicNav.jsx
│   │   │   │   ├── SellerNav.jsx
│   │   │   │   ├── AdminNav.jsx
│   │   │   │   └── Footer.jsx
│   │   │   ├── cards/
│   │   │   │   ├── CardGrid.jsx
│   │   │   │   ├── CardTile.jsx
│   │   │   │   └── CardDetail.jsx
│   │   │   ├── forms/
│   │   │   │   ├── ListingForm.jsx
│   │   │   │   └── SearchFilters.jsx
│   │   │   └── shared/
│   │   │       ├── PriceTag.jsx
│   │   │       ├── SellerBadge.jsx
│   │   │       └── SportFilter.jsx
│   │   └── api/
│   │       ├── client.js             # Axios instance with auth
│   │       ├── listings.js
│   │       ├── orders.js
│   │       └── admin.js
│   └── public/
├── infrastructure/
│   ├── cloudformation/
│   │   ├── frontend.yaml
│   │   ├── api.yaml
│   │   ├── database.yaml
│   │   └── auth.yaml
│   └── scripts/
│       ├── deploy-frontend.sh
│       ├── deploy-api.sh
│       └── run-migration.sh
├── scripts/
│   ├── diagnostics/
│   ├── ops/
│   └── dev/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── qa/
├── docs/
│   ├── architecture/
│   ├── ROADMAP.md
│   ├── PIPELINE-QUALITY-STANDARDS.md
│   ├── UI-REDESIGN.md
│   └── MARKETPLACE-PLAN.md (this file)
└── experiments/
```

---

## Implementation Phases

### Phase 1: Foundation (1-2 weeks)
- [ ] Role-based access control (admin gate on Opportunities/Business)
- [ ] Directory restructure (routes into public/authenticated/seller/admin)
- [ ] Database migrations for seller_profiles, listings, orders
- [ ] Landing page that sells the product (not just a sign-in button)

### Phase 2: Seller MVP (2-3 weeks)
- [ ] Seller registration + approval flow
- [ ] Manual listing creation (title, photos, price, condition)
- [ ] eBay import (pull seller's active listings via OAuth)
- [ ] Seller dashboard (my listings, views, sales)
- [ ] Public seller profile page

### Phase 3: Buyer Experience (1-2 weeks)
- [ ] Unified search across all sellers
- [ ] Filters (sport, player, year, set, price, condition)
- [ ] Card detail page with seller info
- [ ] Purchase flow (link to eBay or on-site checkout)
- [ ] Buyer watchlist with price alerts

### Phase 4: Monetization (1 week)
- [ ] Platform fee on sales (configurable %)
- [ ] Featured listing boost (pay to promote)
- [ ] eBay affiliate link integration
- [ ] Seller subscription tiers

### Phase 5: Growth (ongoing)
- [ ] Reviews/ratings system
- [ ] Seller analytics (what's selling, pricing suggestions)
- [ ] Multi-sport expansion (Basketball, Football ready)
- [ ] Mobile-responsive redesign (Norse aesthetic)
- [ ] Push notifications
- [ ] SEO optimization for card search

---

## Key Decisions Needed

1. **Payment processing** -- Stripe? PayPal? Or eBay-only for now (no on-site checkout)?
2. **Listing approval** -- auto-approve all listings, or admin reviews first?
3. **Seller approval** -- open registration, or invite-only to start?
4. **Pricing** -- what % commission on sales? Free tier vs paid?
5. **Shipping** -- sellers handle their own, or offer Ragnarok shipping labels?
6. **Disputes** -- how to handle buyer/seller conflicts?

---

## Cost-Effective Tech Choices

| Need | Solution | Cost |
|------|----------|------|
| Auth | Cognito (already deployed) | Free tier (50k MAU) |
| API | Lambda + API Gateway (already deployed) | Pay per request |
| Database | RDS PostgreSQL (already deployed) | ~$15/mo |
| Storage | S3 for card images | Pennies |
| CDN | CloudFront (already deployed) | ~$5/mo |
| Search | PostgreSQL full-text search (no Elasticsearch needed) | Free |
| Email | SES for notifications | $0.10/1000 emails |
| Payments | Stripe Connect (if on-site checkout) | 2.9% + $0.30/txn |

Total incremental cost: ~$10-20/mo on top of existing infrastructure.
