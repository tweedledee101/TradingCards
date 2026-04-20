# Feature Roadmap

**Last Updated:** 2026-04-05

## Milestone 3 -- "Public Ragnarok + Store" (backlog)

**Product split (see [ADR-007](./architecture/decisions/ADR-007-public-surfaces-vs-admin-and-commerce.md)):**

- **Admin only (you):** Opportunities, Business dashboard, internal inventory ops, arbitrage/tooling — **not** offered as a public product; keeps logic private.
- **Public:** Landing page (marketing + screenshots/walkthroughs of **safe** surfaces), **storefront** (browse what you sell — sync from eBay listings / inventory), no access to ops tools.
- **Future:** On-site **checkout** (**Stripe**); **Plaid** (or similar) if bank-link / payout flows need it; **breaks**; **livestreams**; **dynamic calendar** (whether customers need accounts TBD).

### 3.1 Public landing + IA
- **Done (frontend):** **`/`** is a public **landing** (marketing / brand / storefront-coming); **Market movers** (trending) moved to **`/market`** (private shell). Signed-in users hitting **`/`** redirect to **`/market`**. **Admin gate** (Cognito group / API enforcement) still TBD.
- Public routes **unauthenticated**; admin app behind login + **admin gate**.

### 3.2 Storefront v1 (no checkout)
- Read-only catalog mirroring **your live eBay listings** (or DB sync); messaging: buy direct / fee narrative; CTA to eBay or contact until checkout exists.

### 3.3 Checkout + payments
- Stripe Checkout or Payment Element; orders tied to inventory/listings; taxes/shipping rules TBD.

### 3.4 Events
- Breaks + livestream links + calendar (access model TBD).

---

## Milestone 1 -- "Make Money From the UI"

### 1.1 Store Opportunities in Database -- DONE
Opportunities table exists with full pipeline results. BIN and auction opportunities stored with listing_type, shipping, bid_count, end_time.

### 1.2 Wire Pipeline Into UI -- DONE
API serves opportunities from database. Frontend Opportunities page shows BIN and Auction tabs with eBay buy links, card images, profit/ROI, SCP verification links.

### 1.3 Worker Separation
Data gathering must run in a separate process from the core app.
- Worker: heavy compute, Selenium browsers, network I/O
- Core app: API + frontend -- always fast, always responsive
- Worker trickle-inserts results so DB never locks up
- Job tracker prevents duplicate runs
- See ADR-004

## Milestone 2 -- "Trust the Data"

### 2.0a Velocity-first, 130point-led discovery (backlog / target architecture)

**Problem:** eBay Browse–first **player** discovery burns quota and does not match “liquid players = those with real sold volume.” **Target:** rank **~top 100** players from **`sold_comps`** / **`sales`** aggregates; enforce **$5–$1000** + **fast sell-through** proxies; **CE + SCP** identity before **narrow** eBay listing pull. Spec: **[docs/OPPORTUNITY-FINDER.md](./OPPORTUNITY-FINDER.md)** → *Target evolution: 130point-led…* Success measured from DB/QA metrics, not anecdotal rows.

### 2.0b Multi-platform listing discovery via web search (active research)

**Problem:** eBay Browse API is the bottleneck — 5,000 calls/day, ~1,200 per 40-player scan, and the BIN pipeline is extremely slow (16+ hours for full variation sweep). Auctions are where the real margins live, so freeing Browse budget for auction-specific calls is strategic.

**Approach:** Replace Browse API as the listing discovery mechanism with free web search using TLS fingerprint impersonation. A text search like `"shohei ohtani 2024 bowman chrome 85" site:ebay.com` returns actual eBay listing pages — zero API calls. Same approach works across eBay, Mercari, COMC, Whatnot, Fanatics.

**Key findings (Session 83):**
- Google Shopping via curl fails (requires JS + TLS fingerprint detection at protocol level)
- DDG Lite works with curl but rate limits aggressively after ~15-20 requests
- `deedy5/ddgs` (2,434 stars) solves this: `primp` (Rust HTTP client) impersonates real browser TLS fingerprints; multi-engine rotation (Google, Brave, DDG, Yahoo, Yandex, Mojeek) with deduplication; XPath parsing of raw HTML (no Selenium)
- Google serves server-rendered HTML to mobile UAs when TLS fingerprint matches a real browser
- Bing is disabled in ddgs (too aggressive blocking); Brave is cleanest implementation

**Blocker:** `primp` and `ddgs` require Python 3.10+. **Python 3.12.11 already installed** at `/usr/local/bin/python3.12` (deadsnakes). Alternative: `curl_cffi` (Python 3.8-compatible TLS impersonation, not yet tested).

**Not a significant architectural shift** — just swapping the listing discovery function. All existing pipeline rules still apply (min profit, volume, variant matching). Visual confirmation via Collectors Edge remains mandatory.

**Next steps:** (1) Verify `primp` installs on 3.12 and TLS impersonation bypasses Google from our IP, (2) OR test `curl_cffi` on 3.8, (3) Build thin search adapter that returns same shape as Browse API results.

### 2.0 Listing identity verification (eBay ↔ SCP ↔ Collectors Edge ↔ 130point) — IN PROGRESS / REQUIRED

**Problem:** Opportunities sometimes show an eBay listing whose **visual card** does not match the **SCP catalog row** (wrong parallel, wrong year, wrong variation). That is unacceptable for trading decisions. With multiple independent sources (eBay, SCP art, CE, **130point `sold_comps`**), **persistent discrepancy after validation = ineffectiveness in process or code** — not something the operator should “just know to ignore.”

**Target behavior:**

- For rows that surface on **RagnarokGamez**, treat **identity as unverified** until a defined verification pass succeeds (or explicitly **`conflict`** if sources disagree).
- **Inputs:** eBay listing images (Browse CDN), **SCP product image** from the matched SCP URL, **Collectors Edge** photo/result, and **sold history** for the resolved SKU via **`sold_comps` / 130point** where available.
- **Method:** Visual + structured compare (Nova vision queue, `collectors_edge_photo_run`, `ce_pipeline_analysis`, `scp_lookup_from_ce_json`); evolve toward **mandatory** gates or clear **UI badges** (`verified` / `pending` / `conflict`).
- **UI (admin Opportunities):** Trust callout + badge legend; per-row **`verification_status`** / **`verification_detail`** from API; modal explains pending vs verified vs conflict. Flipping status from pipeline/QA jobs remains **in progress**.
- **Measurement:** Disagreement rates and funnel metrics live in [docs/testing/strategy.md](./testing/strategy.md) (Layer B + C); goal is **no philosophical debate** — daily data shows whether each stage meets expectations.
- **Process:** [PIPELINE-OPS.md](../PIPELINE-OPS.md), [KNOWN-ISSUES.md](./KNOWN-ISSUES.md).

### 2.1 Sold Price Validation (Recent Comps)
Before buying a $7 card that SCP says is worth $92, show recent eBay sold data for that exact variation.
- One extra eBay sold-listings search per opportunity
- Display: "Recent comps: $45, $62, $78, $91" alongside SCP price
- Flag opportunities where SCP price diverges significantly from eBay sold median
- Dramatically increases confidence in each deal

### 2.2 Demand-Driven Refresh
No crons. Data refreshes only when needed.
- API checks cache age on request. If stale, serves cached + triggers background worker
- Active listings have end dates -- staleness is deterministic, no API call needed
- Sold listings are immutable -- never re-fetch
- SCP prices trusted for 24 hours
- See ADR-004

### 2.3 Listing Freshness / Age
Show how long ago each eBay listing was posted.
- "Listed 2 hours ago" vs "Listed 14 days ago"
- Helps prioritize which deals to jump on first
- eBay API already returns listing dates -- just surface them

## Milestone 2.5 -- "Business Operating System" -- DONE

Transform the platform from a tool into a daily business planner. Connects goals, capital, inventory, time, and opportunities into one workflow.

See [ADR-006](./architecture/decisions/ADR-006-business-planner.md) for full scope.

### 2.5.1 Goal Setting & Capital Tracking -- DONE
- `business_goals` table: annual income target, starting capital, weekly hours, margin targets
- Capital tracker: available cash updated on every buy/sell, deposits/withdrawals
- Goal decomposition: annual -> monthly -> weekly -> daily targets, adjusted for compounding
- Honest trajectory math: $1K starting capital at 25% margin = ~$12.2K Year 1, not $120K
- `capital_transactions` table: deposits, withdrawals, purchases, sales with optional FK to opportunities/inventory

### 2.5.2 Daily Plan Generator -- DONE
- `daily_plans` table with prioritized action list (buy opportunities, list cards, reprice stale, research)
- Time-aware: knows you have 2.5 hours tonight, fills that time with highest-value actions
- Connects Opportunity Finder (what to buy) + Inventory (what to list) + Market Data (what to reprice)
- Catch-up logic: missed yesterday? Deficit spread over next 7 days, never panic-mode
- Pulls REAL pipeline opportunities sorted by ROI

### 2.5.3 Daily Snapshots & Progress Tracking -- DONE
- `daily_snapshots` table: capital, inventory count/value, revenue/profit (daily/MTD/YTD)
- Weekly progress bar, monthly trend, 12-month trajectory projection
- Actual vs target tracking at every level (day, week, month, year)
- Auto-generated from inventory/sales tables (upserts)

### 2.5.4 Business Dashboard -- DONE
- Goal setup form with all parameters (annual target, capital, hours, margins, fees, reinvest %)
- Top stats: available capital, daily target, today's profit, YTD profit
- Week + month progress bars with color-coded fill
- Inventory summary: total cards, listed, unlisted, cost basis
- Today's action plan: expandable cards with buy links, ROI, profit per item
- 12-month trajectory chart (Recharts: cumulative profit + working capital)
- Capital transaction recording (deposit, sale, purchase, withdrawal)
- Hours override for plan regeneration
- Route: `/business`, nav link in main navigation
- Ragnarok Gaming dark theme, consistent with all other pages

### 2.5.5 Inventory Triage
- Categorize owned cards: list now, lot and clear, hold, dump, grade candidates
- Stale listing detection (>14 days, recommend price drops)
- Base card lot recommendations (group by team, list as lots of 25-50)

### Dependencies
- Opportunity Finder producing reliable results (Milestone 1)
- Reliable pricing data (Milestone 2)
- Inventory data entry (cold start -- start with 60 listed cards, ignore base initially)
- eBay OAuth (Milestone 3) solves the data entry problem long-term

## Milestone 3 -- "eBay Account Integration"

### 3.1 eBay OAuth User Login
Users link their eBay account to Ragnarok Gaming via OAuth consent flow.
- "Allow Ragnarok Gaming to view your purchases and selling activity"
- Standard eBay OAuth2 user token flow
- Tokens stored securely per user, refreshed automatically

### 3.2 Auto-Import Purchases
When a user buys a card on eBay, automatically add it to their Inventory.
- Poll user's eBay purchase history (GetMyeBayBuying / Buy Order API)
- If purchased item ID matches an opportunity we showed them, auto-import
- Records: purchase price, SCP market rate at time of purchase, eBay listing URL
- User sees it appear in Inventory automatically -- zero clicks
- On-demand check (not polling on a timer) -- per ADR-004

### 3.3 Auto-Track Sales
When a user sells a card on eBay, automatically record the sale.
- Monitor user's selling activity via eBay API
- Match sold items to Inventory entries
- Auto-calculate realized profit (sale price - purchase price - fees)
- Move from "In Hand" to "Sold" automatically

### 3.4 Opportunity Dismissal / "Already Checked"
Track which opportunities a user has already reviewed.
- Mark as "checked", "passed", or "purchased" per eBay item ID
- Next scan only shows NEW opportunities by default
- Filter toggle: "Show all" vs "Show new only"

## Milestone 4 -- "Smarter Decisions"

### 4.1 Grading Scenario Calculator
For each opportunity, show flip-raw vs grade-and-sell scenarios.
- SCP already has Ungraded, Grade 9, and PSA 10 prices
- Show: "Buy raw $20, sell raw = $59 profit"
- Show: "Grade to PSA 10 ($30 grading + $20 card = $50), sell PSA 10 at $280 = $194 profit"
- Factor in grading turnaround time and success rates

### 4.2 Sell-Through Rate Per Variation
Not all $90 cards sell equally fast.
- Calculate from existing sold data: avg days between sales for each variation
- Show: "avg 12 days to sell" vs "avg 45 days to sell"
- Helps pick quick flips over slow movers

### 4.3 Price Velocity Alerts
Surface SCP price changes over time.
- Track SCP prices across scans
- Flag: "SCP price up 30% this week" -- market heating up
- Flag: "SCP price down 20% this week" -- possible correction
- Overlay on opportunity cards

### 4.4 Daily Digest / Summary View
Dashboard summary instead of scrolling 50 individual opportunities.
- "Today: 47 opportunities. Top 5 by profit. 3 new since last scan. Total potential: $1,240"
- Quick signal on whether it's worth diving deeper today

### 4.5 UI Behavior Tracking
Track how users interact with opportunities to build a feedback loop between QA flags and user decisions.
- `user_events` table: event_type, opportunity_id, metadata (JSONB), created_at
- `/api/events` POST endpoint -- frontend fires on key actions
- Events tracked: view_opportunity, click_buy_link, click_scp_link, dismiss, add_to_watchlist, filter_change, sort_change
- Time-on-opportunity tracking (how long user spends evaluating each card)
- Join user_events to opportunities.qa_flags for pattern detection:
  - "User dismisses 90% of extreme_roi flags" -> auto-reject those
  - "User always clicks SCP link on needs_review" -> surface SCP more prominently
  - "User never clicks opportunities under $15 profit" -> raise min threshold suggestion
- Post-session analysis: what did the user do when they encountered flagged listings? How did they resolve them?
- Feeds into price spike prediction (Milestone 9) as a signal source

## Milestone 5 -- "Ship It"

### 5.1 AWS Deployment
- Core app on ECS (always running, right-sized for serving)
- Worker on ECS task or Lambda (spins up on demand, dies when done)
- Database on RDS PostgreSQL
- Frontend on CloudFront + S3
- ragnarokgamez.com goes live

### 5.2 Redesign Remaining Pages
Inventory, Watchlist, CardDetail pages updated to Ragnarok Gaming theme.

### 5.3 Mobile-Responsive Layout
Opportunities page optimized for phone screens.
- At a card show, pull up the app and check if a card is a deal
- Touch-friendly buy links and filters

### 5.4 Export to CSV
Download button on Opportunities and Inventory pages.
- Dealers track everything in spreadsheets
- Integrate with existing workflows

## Milestone 6 -- "Scale It"

### 6.1 Multi-Sport Expansion
Basketball and Football support.
- Seed players and sets already configured in `backend/config/sets.py`
- Pipeline is sport-agnostic -- just needs SCP data and eBay listings

### 6.2 Notification System
Push notifications when high-value opportunities appear.
- Match criteria: player, min profit, min ROI
- Don't refresh the page all day -- the app tells you when to act

### 6.3 Additional Data Sources
- PSA Population (grading spikes -- infrastructure ready)
- Card Ladder (price velocity -- infrastructure ready)
- Terapeak (sell-through rates)

## Milestone 7 -- "See the Whole Market"

eBay is the right primary focus, but real money moves through other channels. The goal isn't to scrape everything -- it's to know what exists elsewhere and let users log deals from any source.

### 7.1 Cross-Platform Price Comparison
When an opportunity is found on eBay, check if the same card is available elsewhere.
- **Mercari**: Lower fees (10%), smaller audience, cards often priced lower. Has web search -- scrape product pages for price comparison.
- **COMC (Check Out My Cards)**: Consignment marketplace with massive inventory and fixed pricing. Cards sit because less traffic. Web-searchable.
- **MySlabs**: Graded card marketplace, growing fast, lower fees. Web-searchable.
- Display: "Also available on: Mercari $15, COMC $18" alongside eBay listing.
- Not for arbitrage calc (SCP is the price source) -- for confidence and alternative buying options.

### 7.2 Whatnot Integration
Live auction platform, massive in the card space. Cards often sell below market due to live auction pressure.
- No public API currently.
- **Phase 1**: Manual intake -- user logs Whatnot purchases into Inventory (seller name, break type, price paid).
- **Phase 2**: If Whatnot releases an API or partner program, integrate seller dashboard data.
- **Phase 3**: Monitor Whatnot listings/schedules for upcoming breaks featuring target players.

### 7.3 Facebook Marketplace / Groups
Huge peer-to-peer market. No fees, so sellers price lower. Private groups move serious volume.
- No API. Facebook actively blocks scraping.
- **Phase 1**: Manual intake -- user logs Facebook purchases into Inventory.
- **Phase 2**: NovaAct browser automation for monitoring specific groups (already have `acquisition/facebook_marketplace/novaact_intake.py` scaffolded).
- **Phase 3**: Alert user when a target card appears in monitored groups.

### 7.4 Universal Inventory Intake
Users buy cards from everywhere -- eBay, Whatnot, Facebook, card shows, LCS (local card shops), Mercari, trades.
- Inventory "Add Card" must support ANY source, not just eBay.
- Fields: source platform, purchase price, seller (optional), notes, date.
- Dropdown: eBay / Mercari / Whatnot / Facebook / Card Show / LCS / COMC / Other
- eBay purchases auto-imported (Milestone 3). Everything else is manual entry until APIs exist.
- All cards tracked the same way regardless of source -- same P&L, same ROI, same portfolio view.

### 7.5 Sell-Anywhere Tracking
Users don't just sell on eBay. Track sales across platforms.
- Record sale with: platform sold on, sale price, fees (different per platform), buyer (optional).
- Fee presets: eBay 13%, Mercari 10%, Whatnot 9.5% + 2.9%, Facebook 0%, COMC 20%, Card Show 0%.
- P&L calculation adjusts fees based on where the card was sold.

### 7.6 StockX Cards
Bid/ask marketplace model (like a stock exchange for cards).
- Has a trading card category with fixed pricing.
- Potential API access through partner program.
- Good for price discovery on high-end graded cards.
- Lower priority -- smaller selection, focused on PSA 10 slabs.

### Platform Integration Priority

| Platform | Volume | API Available | Fee Rate | Integration Approach | Priority |
|----------|--------|---------------|----------|---------------------|----------|
| eBay | Highest | Yes (Browse API) | 13% | Full API integration | DONE |
| SportsCardsPro | N/A (pricing) | No (Selenium) | N/A | Selenium scraping | DONE |
| Mercari | High | No (web search) | 10% | Price comparison scrape | Medium |
| COMC | Medium | No (web search) | 20% | Price comparison scrape | Medium |
| Whatnot | High | No | 9.5%+2.9% | Manual intake, monitor later | Medium |
| Facebook | High | No (blocked) | 0% | Manual intake, NovaAct later | Low |
| MySlabs | Growing | No (web search) | ~8% | Price comparison scrape | Low |
| StockX | Low (cards) | Partner only | ~10% | Monitor if API opens | Low |
| Card Shows/LCS | Varies | N/A | 0% | Manual intake only | Low |
## Milestone 8 -- "Lot Evaluation & Card Recognition"

The biggest unsolved problem for card dealers: evaluating lots. A seller posts 3,000 cards, shows their best 10. Is the lot worth the asking price? Today this requires hours of manual research. Image recognition + statistical modeling can solve this.

### 8.1 Card Recognition from Images
Identify individual cards from photos (listing images or user uploads).
- Input: photo containing one or more trading cards
- Output: for each card -- player name, year, set, card number, parallel, estimated grade
- Look up SCP price for each identified card automatically
- Display: "Identified 8 of 12 visible cards. Total visible value: $347"

**Technology options (in order of pragmatism):**
1. **Amazon Bedrock (Claude/Nova) with vision** -- send card images to multimodal LLM. Zero training data needed. "What card is this?" works well on clear photos. Cheapest to start, good enough for v1.
2. **OCR (Tesseract / AWS Textract)** -- read text printed on card face (player name, card number, set logo). Match extracted text against SCP catalog. Works on clear, well-lit photos.
3. **AWS Rekognition Custom Labels** -- train a custom model on card images. Needs labeled training data (thousands of card photos). Most accurate once trained, highest upfront cost.
4. **Hybrid** -- OCR for text extraction + Bedrock for visual features (parallel color, refractor pattern, insert design). Best accuracy, most complex.

### 8.2 Automated Lot Analysis
System reads the ENTIRE listing -- title, description, all photos, price, shipping -- and produces a verdict. No manual input.

**What the system reads:**
- Title: "3,000 Card Baseball Lot - Autos, Numbered, Chrome, Prizm"
- Description: seller's text about what's included, years, sets, conditions
- All photos: run card recognition on every image
- Price + shipping: total cost to acquire
- Seller history: feedback score, past lot sales

**What the system produces:**
- Every identified card with SCP price
- Description-informed model of hidden inventory (seller says "mostly 2022-2024 Topps Chrome" + visible cards confirm Chrome parallels = composition skew toward Chrome)
- Statistical estimate for unidentified cards based on description clues + visible card quality
- Total estimated value vs asking price
- Verdict: buy / pass / investigate further
- Risk assessment: "Visible cards cover 70% of asking price. Remaining 2,990 cards are upside."

**The system thinks like a dealer:**
- Seller showing their best cards? Assume the rest is lower quality.
- Seller mentions specific sets/years? Use that to narrow the composition model.
- Seller has history of lot sales? Check if previous buyers left feedback about accuracy.
- Shipping cost high? Factor into total acquisition cost.
- Description vague? Higher risk -- discount the estimate.

### 8.3 Post-Purchase Cataloging
After buying a lot, scan cards with phone camera to catalog inventory.
- User photographs cards one at a time (or in small groups)
- System identifies each card, adds to Inventory automatically
- Running total: "Cataloged 847 of 3,000. Value so far: $412. Remaining estimate: $180-$290."
- Flags high-value finds: "Found a Bobby Witt Jr Topps Chrome Gold /50 -- SCP value $185"
- At completion: full inventory with total value, P&L vs purchase price

### 8.4 Lot Opportunity Detection
Automatically find and evaluate lot listings across platforms.
- Scan eBay lot listings (keyword: "lot", "collection", "bulk")
- For each listing: pull all images, description, price -- run full 8.2 analysis
- Flag lots where visible card value alone justifies the price
- Flag lots where description + visible cards suggest high upside
- Same approach works for Facebook Marketplace lots, Mercari lots, etc.
- This is what dealers spend hours doing manually -- the system does it in seconds per listing

### Why This Matters
- Lots are where the biggest margins hide -- sellers don't know what they have
- Facebook Marketplace lots are especially underpriced (no fees, casual sellers)
- Card shows have boxes of unsorted cards -- quick phone scan tells you if it's worth buying
- No competitor does this well. Most tools focus on individual card pricing.
- Competitive moat: the more lots users catalog, the better the statistical model gets

## Milestone 9 -- "Predict the Spike"

Predict card price spikes before they happen by combining standard leading indicators with nuanced, hard-to-detect signals that the market misses.

### 9.1 Standard Leading Indicators
Industry-accepted signals that correlate with price movement.
- **Sales velocity acceleration**: sudden increase in sales volume for a specific card/player
- **PSA submission spikes**: more people grading a card = expected supply increase OR demand signal
- **SCP price velocity**: week-over-week price changes across Ungraded/Grade 9/PSA 10
- **eBay sold price trends**: median sold price moving up over 7/14/30 day windows
- **Active listing count changes**: supply drying up (fewer listings) or flooding (more listings)
- **Bid count acceleration**: auctions getting more bids than historical average

### 9.2 Nuanced / Non-Obvious Signals
The edge. Signals that most tools and dealers miss entirely.
- **Social media attention**: Twitter/X mentions, Instagram posts, Reddit threads about a player or card. A viral highlight reel or controversy can move prices within hours.
- **Artist features**: Cards designed by specific artists (e.g., Topps Project 70 artists, Topps Chrome Black artists) spike when the artist gains attention or announces new work. Track artist social accounts.
- **Local community behavior**: Facebook group chatter, Discord server activity, Whatnot break schedules featuring specific players. Local hype precedes market-wide price movement.
- **Prospect call-ups / roster moves**: Minor league player gets called up to MLB -- their prospect cards spike immediately. MLB Stats API already integrated, monitor transaction feeds.
- **Award announcements / milestones**: MVP voting, All-Star selections, milestone games (3000 hits, 500 HR). Predictable calendar events that move prices.
- **Injury news**: Player returns from injury (prices spike) or gets injured (prices crash). Real-time news feeds.
- **New product releases**: When a new Topps Chrome or Prizm set drops, existing cards of featured players can spike or dip depending on the new card's reception.
- **Breaker schedule analysis**: When major Whatnot/YouTube breakers schedule breaks of specific products, demand for those players increases in the 24-48 hours before the break.
- **Cross-sport correlation**: NBA/NFL draft picks who played multiple sports -- their baseball cards spike when drafted in another sport.
- **International events**: World Baseball Classic, Olympics -- international player cards spike during and after.

### 9.3 Signal Scoring Engine
Weight and combine signals into a "spike probability" score.
- Each signal source produces a normalized score (0-100)
- Weighted combination based on historical accuracy of each signal
- Confidence level based on how many independent signals agree
- Time horizon: "likely within 24 hours" vs "likely within 7 days" vs "likely within 30 days"
- Output: player + card + spike_probability + confidence + time_horizon + contributing_signals

### 9.4 Alert System
Notify user when spike probability exceeds threshold.
- "Bobby Witt Jr cards likely to spike in 24h -- social media volume 5x normal + All-Star announcement tomorrow"
- Pair with existing opportunity finder: if a spike is predicted AND underpriced listings exist, that's the highest-priority alert
- User configurable: which players, what confidence threshold, what time horizon

### 9.5 Backtesting Framework
Validate prediction accuracy against historical data.
- Replay past signals against actual price movements
- Track prediction accuracy over time: "predicted 47 spikes, 31 actually happened (66% accuracy)"
- Use accuracy data to retune signal weights
- Feeds back into 9.3 scoring engine

### Data Sources Required
| Source | Signal Type | Integration |
|--------|------------|-------------|
| Twitter/X API | Social mentions, viral moments | API (paid tier) or scrape |
| Reddit API | r/baseballcards, r/sportscards discussion | Free API |
| Instagram | Player/artist posts, card community posts | Scrape or Meta API |
| Discord | Community server activity | Bot integration |
| MLB Stats API | Call-ups, roster moves, milestones | Already integrated (free) |
| ESPN/sports news | Injuries, awards, trades | RSS feeds or API |
| Whatnot | Break schedules, live auction activity | Scrape or future API |
| YouTube | Breaker schedules, card review videos | YouTube Data API (free tier) |
| Topps/Panini | Product release calendars | Scrape announcement pages |
| Facebook Groups | Local community chatter | NovaAct (already scaffolded) |

---

## Backlog: Brand, commerce & content (unscheduled)

Captured so ideas are not lost; **not** current sprint work.

### Developer docs in UI

- Serve project documentation (architecture, ADRs, pipeline ops, known issues) through the frontend as a `/docs` page.
- Render existing repo markdown files (or a curated subset) in the Ragnarok Gaming theme.
- Audience: operator / future contributors — not public users.

### Print-on-demand merch (no home inventory)

- Small-run kitsch: mugs, T-shirts, keychains, stickers — fine for one or two buyers at first.
- **Print-on-demand (POD)** fulfillment: vendor manufactures and ships from their facility; operator does not hold stock.
- When ready: pick one POD path (e.g. storefront + Printful/Printify, or marketplace + POD) — mostly separate from the trading app unless we embed a simple “Shop” link.

### In-app “buy this card”

- Today: pain point is **no purchase inside the platform**; realistic v1 is **deep links** to eBay (already aligned with driving traffic to listings).
- Full **checkout in-app** implies merchant-of-record, payments, shipping, disputes — a deliberate product/legal decision, not a small UI tweak.
- Future: weigh **affiliate / partner** flows vs owning checkout; ties to Milestone 3 (eBay OAuth) for “I bought this” tracking.

### Blog: voice, personas, and reacting to the ecosystem

- **Tone:** positive, upbeat, optionally light snark — define **guardrails** (no punching down, no pile-ons on individuals).
- **Personas:** a few consistent voices (e.g. data-first flipper, set-builder arbitrager, auction sniper) for variety without a writing staff.
- **Cadence:** “daily” is heavy for one person; consider **fewer longer posts** or a **weekly digest** unless content is short/templated.
- **Format:** link out to others’ articles/posts/data; **summarize, cite, then support / refute / extend** with Ragnarok’s own stats, filters, or extra variables readers should consider.
- **Engagement:** occasional thoughtful comment on someone else’s post can work; avoid spammy brand drive-bys. A **“reads of the week”** post that links 5 sources + your take is lower risk than mass commenting.
- **Discovery:** start with **RSS, newsletters, Reddit threads, YouTube descriptions** — before building a **custom blog scraper**, check **robots.txt, ToS, rate limits**, and attribution norms.
- **Quality / trust:** if any step is **AI-drafted**, plan for **human review** before publish and **clear disclosure** if you adopt a public policy.

---

## eBay API Strategy

### Current State
- **Tier**: Individual Developer (default)
- **Limit**: 5,000 Browse API calls/day
- **Usage**: ~1,200 calls per full 40-player opportunity scan

### ACTION ITEM: Apply for Compatible Application Status
eBay's Compatible Application program grants higher API limits to apps that drive purchases on eBay. Ragnarok Gaming qualifies -- it literally sends users to buy things on eBay.

**How to apply:**
1. Go to https://developer.ebay.com/my/keys
2. Navigate to the Compatible Application program
3. Describe the app: "Ragnarok Gaming helps trading card dealers find underpriced listings on eBay by comparing active listing prices to SportsCardsPro market rates. Users click through to eBay to purchase cards directly."
4. Expected approval: 50,000-200,000+ calls/day

**Why eBay will approve this:**
- App drives direct purchases on eBay (they make money from every transaction)
- Not scraping or competing with eBay -- enhancing their marketplace
- Legitimate commerce use case

### Per-User OAuth Token Architecture
Each user links their eBay account. This enables:
- Auto-import purchases (zero manual entry)
- Auto-track sales (automatic P&L)
- Access to user's buying/selling history

**Important**: API calls made with user OAuth tokens still count against the APP's quota, not the user's. Per-user tokens don't help with rate limits -- they help with functionality.

### Call Budget Optimization
- Cache search results aggressively (ADR-004)
- One search per variation, shared across all users
- Active listing end dates are deterministic -- don't re-query to check if sold
- Sold listings are immutable -- fetch once, store forever
- SCP prices trusted for 24 hours
- Target: <2,000 calls/day for full operation at current scale
