# Trading Card Platform - Product Overview

## Purpose
A data-driven arbitrage opportunity finder for trading card dealers that identifies profitable card flips using **volume-based discovery** and **budget-first filtering**.

## Core Value Proposition
- **Volume-Based Discovery**: Find players with highest trading activity (ignore price initially)
- **Budget-First Filtering**: Only show opportunities within user's budget
- **Arbitrage Detection**: Buy below market, flip for profit after fees
- **Strategy Modes**: Quick Flip (high turnover) vs Sit & Wait (patient strategy)

## System Architecture (3 Phases)

### Phase 1: Volume Discovery
- Find top 100 players by **sales volume only** (last 90 days)
- Sort by: Total cards sold
- **Ignore price completely**
- Output: Ranked list of most-traded players

### Phase 2: Budget Filtering  
- User sets budget (e.g., $100)
- For each player (starting with #1 by volume):
  - Check if ANY cards exist ≤ budget
  - If YES: Add to target list (max 20 players)
  - If NO: Skip to next player
- Stop when 20 players found

### Phase 3: Opportunity Analysis
- Only analyze the 20 budget-friendly players
- Find cards with:
  - Quick sell (high velocity)
  - High margins (profit after fees)
  - Low error (price consistency)
  - High frequency (lots of sales)
  - High confidence (momentum signals)

## Key Features

### Opportunity Finder (Primary Feature)
- **BIN + Auction pipelines**: unified command runs both sequentially
- **Three-tier pricing**: SCP primary, 130point sold comps secondary, eBay BIN comps tertiary
- **Multi-pass SCP matching**: exact parallel -> strict text match -> fuzzy word-overlap (50%+ match) -> signal match (RC/Auto/Relic/print_run)
- **SCP caching**: Selenium results cached 24h in `scp_cache` table, instant on re-runs
- **Auction pipeline**: eBay-first, 110 value+player queries (was 101 set-specific), pagination up to 1000/query, MLB Stats API for 2,269 player roster
- **Player extraction**: MLB API + accent normalization + period stripping (Jr./Sr.) + eBay aspects fallback (Player/Athlete/Player Name) for retired/minor league players
- **Expired auction filtering**: API auto-hides ended auctions, frontend shows "Ended" label
- **BIN/Auction classification**: checks eBay `buyingOptions` field, tags hybrids as `auction_bin`, uses `currentBidPrice` for actual bid
- **BIN sanity check**: if hybrid listing's BIN price < 50% of SCP, reject (seller knows the card's value)
- **Lot detection**: multiple # signs, X & Y & Z patterns, "N cards" language
- **Volume filtering**: rejects cards with "rare", "1 sale per year", "2 sales per year"
- **Price floor**: BIN below 30% of SCP hard-rejected
- **Suspicious flagging**: BIN between 30-50% of SCP flagged for "Needs Review"
- **Factory set filter**: complete set, montgomery club, walmart/target exclusive
- **Reprint filter**: replica, project 2020, shoebox treasures, sticker, ACEO
- **Wrong set detection**: rejects listings with mismatched set names
- **DB cross-check**: validates SCP URL matches parallel name to catch bad data
- **Direct buy links**: clickable eBay listing URLs
- **Card images from eBay thumbnails**
- **SCP verification links**
- **All 3 SCP price tiers shown (Ungraded, Grade 9, PSA 10)**
- **QA validation**: post-pipeline background rules (extreme_roi, card_number_mismatch, etc.)

## Target Users
- **Professional Card Dealers**: Primary audience - users who buy and flip cards for profit
- **Serious Collectors**: Secondary audience - collectors tracking portfolio value and market trends
- **Card Investors**: Users treating cards as investment vehicles with ROI focus

## Use Cases

### Primary Use Case: Find Profitable Flips
1. User sets budget filter ($100-$500)
2. Platform shows cards selling below market rate
3. User sees profit after fees ($45 profit, 35% ROI)
4. Momentum signals validate (rising prices, high velocity)
5. User purchases card and tracks in inventory
6. User sells card and records profit

### Secondary Use Case: Portfolio Management
1. User records card purchase ($150)
2. Platform tracks current market value ($210)
3. User sees real-time profit ($60, 40% ROI)
4. User decides to sell or hold based on momentum
5. User records sale and realizes profit

### Tertiary Use Case: Market Research
1. User monitors watchlist of target cards
2. Platform alerts when prices hit targets
3. User analyzes price history and grading trends
4. User identifies emerging opportunities

### Quaternary Use Case: Automated Target Discovery (NEW)
1. System discovers 100+ trending cards from eBay at 1 AM
2. Scores by sales volume (50%) + price velocity (30%) + price range (20%)
3. Auto-updates targets.yaml with top 50 cards (preserves manual favorites)
4. Regular scraper runs at 2 AM using auto-generated list
5. User sees fresh opportunities daily with zero manual research

## Data Sources (9 Total)

| Source | Purpose | Status |
|--------|---------|--------|
| eBay Browse API | Sold listings, active listings | Working (Real Data) |
| SportsCardsPro | Market rates (Ungraded/Grade 9/PSA 10) | Working (Selenium/Firefox, graduated search + set validation) |
| 130point.com | eBay sold comps (actual sale prices + volume) | Working (HTTP POST, background worm) |
| MLB Stats API | Player roster (2,269 players) | Working (free, no auth) |
| eBay Trending Discovery | Auto-discover hot cards | Code Ready (Testing) |
| PSA Population | Grading spikes | Infrastructure Ready (Testing) |
| Card Ladder | Price velocity, benchmarks | Infrastructure Ready (Testing) |
| Sell-Through Rates | Market confidence | Code Ready (Need eBay Data) |
| Terapeak | Sell-through rates | Planned |
| Twitter/Reddit | Social sentiment | Planned |
| Release Calendars | New releases | Planned |

**Current Status**: 4/11 sources with real data, 2/11 infrastructure ready

## Cross-Platform Strategy

eBay is the primary marketplace (best API, highest volume). Other platforms tracked for price comparison and universal inventory intake.

| Platform | Integration | Priority |
|----------|------------|----------|
| eBay | Full API (Browse + OAuth) | DONE |
| SportsCardsPro | Selenium scraping | DONE |
| Mercari | Price comparison scrape | Medium |
| COMC | Price comparison scrape | Medium |
| Whatnot | Manual intake, monitor later | Medium |
| Facebook | Manual intake, NovaAct later | Low |
| MySlabs | Price comparison scrape | Low |
| StockX | Monitor if API opens | Low |
| Card Shows/LCS | Manual intake only | Low |

Key principle: Inventory tracks cards from ANY source. Users buy on eBay, Whatnot, Facebook, card shows -- all tracked the same way with platform-specific fee rates (eBay 13%, Mercari 10%, Whatnot 9.5%+2.9%, Facebook 0%, COMC 20%).

See `docs/ROADMAP.md` Milestone 7 for full details.

## eBay API Strategy

### Current Tier
- Individual Developer: 5,000 Browse API calls/day
- ~1,200 calls per full 40-player opportunity scan

### Planned: Compatible Application Status
- Apply at https://developer.ebay.com/my/keys
- Ragnarok Gaming drives purchases on eBay -- legitimate commerce app
- Expected: 50,000-200,000+ calls/day
- Costs nothing, takes a few days to approve

### Per-User eBay OAuth Integration
- Users link their eBay account via OAuth consent flow
- Auto-import purchases to Inventory (match by eBay item ID)
- Auto-track sales for P&L (monitor selling activity)
- User tokens count against APP quota, not user quota
- Helps with functionality, not rate limits

### Call Budget Optimization (ADR-004)
- Cache search results aggressively
- One search per variation, shared across all users
- Active listing end dates are deterministic -- don't re-query
- Sold listings are immutable -- fetch once, store forever
- SCP prices trusted for 24 hours

## Deployment
- **Domain**: ragnarokgamez.com
- **ACM cert**: `arn:aws:acm:us-east-1:635601810497:certificate/8dda492b-b16f-45bf-965e-9268abaabe78`
- **Infrastructure**: 100% AWS (ECS, RDS, CloudFront) -- no Lambda for scheduling
- **RDS**: deployed at `cardpulse-db.ckvp9bhavaww.us-east-1.rds.amazonaws.com` (legacy name)
- **Deployment**: CloudFormation (Infrastructure as Code)
- **Refresh**: Demand-driven (ADR-004), no crons
- **Worker**: Separate process from core app, trickle-inserts to DB
- **Current Phase**: Milestone 1 -- get opportunities into the UI
- **Database**: 23 migrations tracked (schema_migrations), latest: scheduled_bids table
- **Database targets**: Local PostgreSQL + RDS (synced via `migrate.py --both`)
- **Primary DB**: RDS (`cardpulse-db.ckvp9bhavaww.us-east-1.rds.amazonaws.com`)
- **Full roadmap**: `docs/ROADMAP.md`
