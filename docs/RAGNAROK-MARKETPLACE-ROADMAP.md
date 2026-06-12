# Ragnarok Gamez Marketplace Roadmap

## Vision
Multi-seller marketplace for trading cards and collectibles (sports, Pokémon, TCG, anything). Sellers list and ship their own inventory. Ragnarok takes $1 per sale. Buyers get a unified shopping experience across all sellers.

---

## Phase 1: Two-Seller MVP (Target: 1-2 weeks)

**Goal:** You and your friend can both sell cards on ragnarokgamez.com with direct checkout.

### Milestones

1.1 **Stripe Connect Setup**
- Create Stripe Connect platform account
- Onboard you + friend as connected sellers (bank accounts linked)
- Payment splits: seller gets (card + shipping), you get $1, Stripe gets their cut
- Buyer sees one "processing fee" line

1.2 **Seller Profiles**
- Extend existing Cognito auth with seller role
- Seller profile: display name, bio, avatar
- Public seller page: `/seller/tweedledee101`
- Seller dashboard: view own listings, orders, earnings

1.3 **Multi-Seller Listings**
- Add `seller_id` to inventory/listings
- Sellers can create listings: title, description, price, category, photos, shipping profile
- Categories: Baseball, Football, Basketball, Pokémon, Other TCG, Misc
- Listing status: draft → active → sold → shipped → delivered

1.4 **Buy Now Checkout**
- Stripe Checkout session per listing
- Collects shipping address from buyer
- On success: mark sold, notify seller, email buyer confirmation
- Card removed from shop immediately

1.5 **Seller Order Dashboard**
- Seller sees incoming orders
- Seller enters tracking number manually
- Buyer gets email with tracking

**Deliverables:** Working checkout, two sellers live, money flows correctly.

---

## Phase 2: Offers & Communication (Target: 2-3 weeks after Phase 1)

**Goal:** Buyers can negotiate. Sellers get real-time notifications.

### Milestones

2.1 **Offer System**
- Buyer submits offer (any amount)
- Seller gets email/push notification
- Seller accepts → buyer gets checkout link at agreed price
- Seller counters → buyer sees counter, can accept or re-offer
- Seller declines → buyer notified
- Offers expire after 48 hours

2.2 **Notifications**
- Email notifications (AWS SES): new order, offer received, offer accepted, shipped, delivered
- Optional: SMS via SNS for sellers on new orders
- In-app notification bell

2.3 **Messaging (lightweight)**
- Buyer can ask seller a question on a listing
- Not full chat — just Q&A visible on the listing page

2.4 **Seller Analytics Dashboard**
- Listing views & click-through rate
- Total sales / revenue (week, month, all-time)
- Sell-through rate (% of listings sold)
- Average days to sell
- Average sale price
- Top performing categories

**Deliverables:** Offer flow working, email notifications live, seller analytics visible.

---

## Phase 3: Shipping & Fulfillment (Target: 2 weeks after Phase 2)

**Goal:** Automated label buying and tracking notifications.

### Milestones

3.1 **Shippo Integration**
- Seller clicks "Buy Label" from order dashboard
- Generates USPS label (1oz PWE or 4oz BMWT options)
- Tracking number auto-saved to order

3.2 **Tracking Webhooks**
- Shippo sends tracking events
- Auto-email buyer: label created → in transit → delivered
- Order status updates automatically

3.3 **Shipping Profiles**
- Sellers define their shipping options & prices
- PWE ($1), BMWT ($4), Priority ($8), etc.
- Buyer picks at checkout

**Deliverables:** One-click label generation, automated tracking emails.

---

## Phase 4: Trust & Safety (Target: 2 weeks after Phase 3)

**Goal:** Buyers trust the platform, disputes are handled.

### Milestones

4.1 **Seller Ratings & Reviews**
- Buyer leaves rating (1-5 stars) + comment after delivery
- Seller profile shows rating, # of sales, member since
- Cannot review until item marked delivered

4.2 **Buyer Protection Policy**
- Define return/refund policy
- If item not received within 14 days → automatic refund eligibility
- If item significantly not as described → dispute process
- Stripe handles refunds via their dispute system

4.3 **Seller Verification**
- New sellers require approval (manual for now)
- Verified badge after 10+ sales with 4.5+ rating

**Deliverables:** Review system live, protection policy published, trust signals visible.

---

## Phase 5: Growth & Inventory Sync (Target: 3-4 weeks after Phase 4)

**Goal:** Cross-platform sync, more sellers, marketing.

### Milestones

5.1 **eBay Inventory Sync**
- When sold on Ragnarok → auto-end eBay listing via Trading API
- When sold on eBay → mark as sold on Ragnarok (via compliance webhook)
- Optional: auto-import eBay listings to Ragnarok

5.2 **Whatnot Sync (when API available)**
- Same concept — sold on one, removed from other

5.3 **Discord Integration**
- Webhook notifications: new listings, sales, milestones
- Activity feed for your community

5.4 **More Sellers Onboarding**
- Application form for new sellers
- Self-service Stripe Connect onboarding
- Seller guidelines & TOS

5.5 **SEO & Marketing**
- Individual card pages with proper meta tags
- Google Shopping feed
- Social sharing cards

**Deliverables:** Full sync working, open to new sellers, discoverable via search.

---

## Phase 6: Advanced Features (Future)

- Auction listings (timed)
- Collection tracking for buyers
- Watchlists with price drop alerts
- Bulk listing tools (CSV import for sellers)
- Mobile app
- Live sales (mini-Whatnot shows?)
- Analytics dashboard for sellers

---

## Tech Stack (existing + additions)

| Layer | Current | Adding |
|-------|---------|--------|
| Frontend | React + Vite + Tailwind | Checkout pages, seller dashboard |
| Backend | FastAPI + SQLAlchemy | Orders, offers, payouts endpoints |
| Auth | AWS Cognito | Seller role, buyer accounts |
| Payments | — | Stripe Connect |
| Shipping | — | Shippo API |
| Email | — | AWS SES (already available) |
| Database | PostgreSQL (RDS) | Orders, offers, reviews tables |
| Hosting | AWS CloudFront + Lambda | Same |

---

## Cost to Run (estimated at scale of 10 sellers, 50 sales/month)

| Service | Monthly |
|---------|---------|
| Stripe | $0 (per-txn only) |
| Shippo | $0 (pay per label) |
| AWS SES | $0 (free tier) |
| Existing AWS infra | ~$30-50 (already paying) |
| **Total new fixed costs** | **$0** |

Revenue at 50 sales/month: **$50/month** from $1 fees.

---

## Decision Points (Need Your Input)

- [ ] Flat shipping or seller-defined?
- [ ] Open marketplace or invite-only sellers?
- [ ] Return policy: 7 days? 14 days? No returns?
- [ ] Minimum listing price? (avoid $0.50 listings where fee > profit)
- [ ] Ragnarok branding for shipping labels or seller's own?
