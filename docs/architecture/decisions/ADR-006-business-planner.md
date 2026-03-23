# ADR-006: Business Operating System (Business Planner)

**Date:** 2026-06-01
**Status:** Proposed
**Deciders:** Development Team

## Context

The platform currently finds opportunities (buy signals) and tracks inventory (what you own). These are disconnected systems. Neither one answers the question a card dealer actually asks every day: **"What should I do right now to hit my income goal?"**

The user's real constraints:
- $1,000 starting capital (no bailout money)
- Full-time job (~2-3 hours/day weekdays, more on weekends)
- Kids and life obligations
- Goal: replace $120K/year salary with card business income
- ~1,000 cards in hand (mostly base, low individual value)
- 60 active eBay listings
- All sales through eBay so far

The platform needs a layer that sits ON TOP of Opportunity Finder + Inventory and produces daily actionable plans tied to a financial goal.

## Decision

Build a Business Planner that connects goals, capital, inventory, time, and opportunities into a single operating system.

## What It Does

The Business Planner answers five questions every time the user opens the app:

1. **Where am I?** -- Capital, inventory value, monthly revenue run rate, profit to date
2. **Where should I be?** -- Daily/weekly/monthly targets derived from annual goal
3. **Am I on track?** -- Actual vs target, with trend (ahead/behind/on pace)
4. **What do I do today?** -- Prioritized action list given available time and capital
5. **What changed?** -- Market moves, new opportunities, sold cards, expired listings

## Data Model

### `business_goals` table
```sql
CREATE TABLE business_goals (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,                          -- future: FK to users
    annual_income_target DECIMAL(10,2),       -- $120,000
    starting_capital DECIMAL(10,2),           -- $1,000
    weekly_hours_weekday DECIMAL(4,1),        -- 2.5 hrs/day * 5 = 12.5
    weekly_hours_weekend DECIMAL(4,1),        -- 4 hrs/day * 2 = 8
    target_margin_pct DECIMAL(5,2),           -- 25% (conservative default)
    avg_shipping_cost DECIMAL(6,2),           -- $4.50 default
    platform_fee_pct DECIMAL(5,2),            -- 13% eBay default
    reinvest_pct DECIMAL(5,2),               -- 100% (reinvest all profit early)
    goal_start_date DATE,                     -- when the clock starts
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### `daily_snapshots` table
```sql
CREATE TABLE daily_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL UNIQUE,
    available_capital DECIMAL(10,2),          -- cash available to buy
    inventory_count INTEGER,                  -- total cards owned
    inventory_cost_basis DECIMAL(10,2),       -- what you paid for everything
    inventory_market_value DECIMAL(10,2),     -- what it's worth today (SCP/comps)
    listed_count INTEGER,                     -- cards currently listed
    unlisted_count INTEGER,                   -- cards owned but not listed
    revenue_today DECIMAL(10,2),             -- sales revenue today
    profit_today DECIMAL(10,2),              -- net profit today
    revenue_mtd DECIMAL(10,2),               -- month to date
    profit_mtd DECIMAL(10,2),                -- month to date
    revenue_ytd DECIMAL(10,2),               -- year to date
    profit_ytd DECIMAL(10,2),                -- year to date
    cards_bought_today INTEGER,
    cards_sold_today INTEGER,
    cards_listed_today INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### `daily_plans` table
```sql
CREATE TABLE daily_plans (
    id SERIAL PRIMARY KEY,
    plan_date DATE NOT NULL,
    available_hours DECIMAL(4,1),             -- how much time today
    target_revenue DECIMAL(10,2),             -- what you need to sell today
    target_listings INTEGER,                  -- how many cards to list
    target_buys INTEGER,                      -- how many cards to buy
    buy_budget DECIMAL(10,2),                 -- capital allocated for buying
    status VARCHAR(20) DEFAULT 'pending',     -- pending/in_progress/completed
    actions JSONB,                            -- prioritized action list (see below)
    results JSONB,                            -- end-of-day actual vs plan
    created_at TIMESTAMP DEFAULT NOW()
);
```

### `daily_plans.actions` JSONB structure
```json
[
    {
        "priority": 1,
        "type": "list",
        "description": "List 4 highest-margin unlisted cards",
        "cards": [
            {"inventory_id": 42, "player": "Elly De La Cruz", "est_profit": 18.50, "est_time_min": 12}
        ],
        "est_time_min": 48,
        "est_revenue": 74.00
    },
    {
        "priority": 2,
        "type": "buy",
        "description": "Buy 2 opportunities within budget",
        "opportunities": [
            {"opportunity_id": 117, "player": "Bobby Witt Jr", "cost": 34.00, "est_profit": 15.20}
        ],
        "est_time_min": 15,
        "est_cost": 68.00
    },
    {
        "priority": 3,
        "type": "reprice",
        "description": "Drop price on 3 stale listings (>14 days)",
        "cards": [
            {"inventory_id": 19, "current_price": 45.00, "suggested_price": 38.00, "days_listed": 21}
        ],
        "est_time_min": 10
    },
    {
        "priority": 4,
        "type": "lot_clear",
        "description": "Lot 50 base cards as team lot",
        "details": "Group Yankees base into lot of 50, list at $12-15",
        "est_time_min": 20,
        "est_revenue": 13.00
    }
]
```

## Core Logic

### Goal Decomposition

Annual goal -> monthly -> weekly -> daily, adjusted for compounding capital.

```
Year 1 reality with $1K starting capital at 25% margin, 7-day avg turnover:

Month 1:  $1,000 capital -> ~$250 profit  (reinvest all)
Month 2:  $1,250 capital -> ~$312 profit
Month 3:  $1,562 capital -> ~$390 profit
Month 6:  ~$3,800 capital -> ~$950/mo profit
Month 9:  ~$7,400 capital -> ~$1,850/mo profit
Month 12: ~$14,500 capital -> ~$3,625/mo profit

Year 1 total profit: ~$14,500 (NOT $120K -- that's the honest math)
```

The system must show this trajectory honestly. $120K/year is a Year 3-4 goal at 25% margins starting from $1K. The planner shows the real curve and adjusts targets accordingly.

If margins improve to 30% (which the Opportunity Finder enables) and turnover drops to 5 days, the curve accelerates:
```
Month 6:  ~$5,700 capital -> ~$1,710/mo
Month 12: ~$32,000 capital -> ~$9,600/mo
Year 2:   potentially $120K run rate if compounding holds
```

The planner recalculates the trajectory every day based on ACTUAL performance, not projections.

### Daily Target Calculation

```python
def calculate_daily_target(goal, snapshot):
    """
    What do you need to do TODAY to stay on the compounding curve?
    """
    days_remaining = (goal.goal_start_date + timedelta(days=365) - date.today()).days
    profit_remaining = goal.annual_income_target - snapshot.profit_ytd
    
    # Naive daily target (linear)
    linear_daily = profit_remaining / max(days_remaining, 1)
    
    # Adjusted for compounding (early months have lower targets)
    # Capital today determines what's achievable today
    max_daily_profit = snapshot.available_capital * goal.target_margin_pct
    achievable_daily = min(linear_daily, max_daily_profit)
    
    return achievable_daily
```

### Catch-Up Logic

When you miss a day (kid's soccer game, long work day, just tired):

```python
def calculate_catchup(goal, snapshot, missed_days):
    """
    Don't panic. Spread the deficit over the next 7 days.
    Never try to make up everything in one day.
    """
    deficit = snapshot.target_profit_wtd - snapshot.profit_wtd
    if deficit <= 0:
        return 0  # ahead of pace, no catchup needed
    
    # Spread over next 7 days (or remaining days in week, whichever is less)
    catchup_days = min(7, days_remaining_in_week)
    daily_catchup = deficit / catchup_days
    
    return daily_catchup
```

### Action Prioritization

Given N available hours tonight, what produces the most value?

Priority order:
1. **List high-margin unlisted cards** -- zero capital required, immediate revenue potential. Time: ~12 min/card (photo, title, description, price).
2. **Buy opportunities within budget** -- uses capital but compounds. Time: ~5-8 min/card (review, purchase, record).
3. **Reprice stale listings** -- cards listed >14 days need price drops. Time: ~3 min/card.
4. **Lot low-value base cards** -- clear dead inventory for small revenue. Time: ~20 min per lot of 50.
5. **Research/evaluate** -- check new opportunities, review market moves. Time: variable.

```python
def generate_daily_plan(goal, snapshot, available_hours):
    available_minutes = available_hours * 60
    actions = []
    remaining_minutes = available_minutes
    
    # 1. Unlisted cards with known market value, sorted by margin
    unlisted = get_unlisted_cards_by_margin()
    listing_batch = []
    for card in unlisted:
        if remaining_minutes < 12:
            break
        listing_batch.append(card)
        remaining_minutes -= 12
    if listing_batch:
        actions.append({"priority": 1, "type": "list", "cards": listing_batch})
    
    # 2. Buy opportunities within available capital
    if snapshot.available_capital > 20:
        opps = get_opportunities(max_budget=snapshot.available_capital)
        buy_batch = []
        for opp in opps:
            if remaining_minutes < 8 or snapshot.available_capital < opp.cost:
                break
            buy_batch.append(opp)
            remaining_minutes -= 8
            snapshot.available_capital -= opp.cost
        if buy_batch:
            actions.append({"priority": 2, "type": "buy", "opportunities": buy_batch})
    
    # 3. Reprice stale listings
    stale = get_stale_listings(days=14)
    # ... same pattern
    
    return actions
```

### Time Estimation Model

Every action has a time cost. The system learns YOUR actual pace over time.

| Action | Default Estimate | Learns From |
|--------|-----------------|-------------|
| List a card (photo + title + price) | 12 min | Time between "listed" status changes |
| Buy an opportunity (review + purchase) | 8 min | Time between opportunity view + inventory add |
| Reprice a listing | 3 min | Batch size / session duration |
| Lot 50 base cards | 20 min | Historical lot listing times |
| Ship a sold card | 8 min | Not tracked (future: shipping label timestamps) |

Initially uses defaults. After 2-3 weeks of usage, adjusts to actual pace.

### Capital Tracking

The system must always know how much cash you have available to spend.

```
Available Capital = Starting Capital
    + Revenue from sales (sale_price received)
    - Cost of purchases (cards bought)
    - Fees paid (eBay, shipping supplies)
    - Withdrawals (money taken out for personal use)
    + Deposits (money added to the business)
```

Every sale increases available capital. Every purchase decreases it. The system never recommends buying more than you can afford.

### Inventory Intelligence

For the ~1,000 cards currently owned:

**Triage categories:**
- **List now**: Cards with known market value > $5 and positive margin. Worth the 12 minutes to list.
- **Lot and clear**: Base cards worth < $2 each. Group by team, list as lots of 25-50.
- **Hold**: Cards with rising SCP prices. Don't sell into a climbing market.
- **Dump**: Cards with falling prices or no market data. Cut losses, free up capital.
- **Grade candidates**: Raw cards where PSA 10 price is 3x+ ungraded price and the card looks gradeable.

The system needs market data on owned cards to make these calls. This connects to the existing SCP/130point/eBay comp infrastructure.

## API Endpoints

```
GET  /api/business/dashboard     -- today's snapshot + plan + progress
GET  /api/business/trajectory    -- projected income curve (monthly)
GET  /api/business/plan/today    -- today's action list
POST /api/business/goals         -- set/update annual goal + constraints
POST /api/business/snapshot      -- record end-of-day actuals (or auto-generate)
GET  /api/business/history       -- daily snapshots over time (chart data)
POST /api/business/capital       -- record deposit/withdrawal
```

### Dashboard Response Shape
```json
{
    "today": {
        "date": "2026-06-01",
        "available_capital": 847.00,
        "daily_target_profit": 12.50,
        "profit_so_far_today": 0.00,
        "status": "behind",
        "catchup_amount": 8.30
    },
    "week": {
        "target_profit": 87.50,
        "actual_profit": 42.20,
        "pct_complete": 48.2,
        "days_remaining": 3
    },
    "month": {
        "target_profit": 375.00,
        "actual_profit": 189.50,
        "pct_complete": 50.5
    },
    "year": {
        "target_profit": 14500.00,
        "actual_profit": 2340.00,
        "pct_complete": 16.1,
        "projected_annual": 15200.00,
        "on_track": true
    },
    "plan": {
        "available_hours": 2.5,
        "actions": [...]
    },
    "inventory": {
        "total_cards": 1047,
        "listed": 60,
        "unlisted": 987,
        "total_cost_basis": 1420.00,
        "total_market_value": 1890.00,
        "unrealized_profit": 470.00
    }
}
```

## UI: Business Dashboard Page

New page at `/dashboard` -- becomes the HOME page (replaces Trending).

### Layout (top to bottom):

**1. Goal Strip** (always visible)
```
Annual Goal: $14,500 (Year 1)  |  YTD: $2,340 (16.1%)  |  On Track: YES
Available Capital: $847  |  Inventory Value: $1,890
```

**2. Today's Plan** (the main event)
```
Tonight: 2.5 hours available  |  Target: $12.50 profit

[ ] List 4 cards (est. 48 min, est. $74 revenue)
    - Elly De La Cruz 2023 Topps Chrome RC #150 -- est. profit $18.50
    - Bobby Witt Jr 2022 Bowman Chrome #BCP-1 -- est. profit $15.20
    - Gunnar Henderson 2023 Topps #1 RC -- est. profit $12.80
    - Corbin Carroll 2023 Topps Chrome Refractor -- est. profit $11.40

[ ] Buy 2 opportunities ($68 capital needed, est. $30.40 profit)
    - [link] Bobby Witt Jr 2024 Topps Chrome Gold /50 -- $34 buy, $15.20 profit
    - [link] Elly De La Cruz 2023 Bowman 1st Auto -- $34 buy, $15.20 profit

[ ] Reprice 3 stale listings (est. 10 min)
    - Card X: $45 -> $38 (listed 21 days, no watchers)
```

**3. Weekly Progress Bar**
```
Week 22: [$42.20 / $87.50] ==================---------- 48%
Mon: $18.50  Tue: $23.70  Wed: --  Thu: (today)  Fri: --  Sat: --  Sun: --
```

**4. Monthly Trend Chart**
Line chart: daily cumulative profit vs target line.

**5. Trajectory Chart**
12-month projection: capital growth curve + income curve, actual vs projected.

## What Exists vs What Needs Building

### Exists (can reuse):
- `inventory` + `inventory_sales` tables and API (CRUD + stats)
- `opportunities` table and API (buy signals)
- `sell_through_calculator.py` (days-to-sell estimates)
- SCP/130point/eBay comp pricing infrastructure
- Ragnarok Gaming UI theme + component patterns

### Needs Building:

| Component | Effort | Depends On |
|-----------|--------|------------|
| `business_goals` table + migration | Small | Nothing |
| `daily_snapshots` table + migration | Small | Nothing |
| `daily_plans` table + migration | Small | Nothing |
| Goal decomposition engine | Medium | business_goals |
| Daily plan generator | Medium | Inventory + Opportunities + Goals |
| Capital tracker | Medium | inventory_sales + business_goals |
| Snapshot auto-generator (nightly) | Small | All tables |
| Catch-up calculator | Small | daily_snapshots |
| Inventory triage logic | Medium | SCP/comp pricing on owned cards |
| Time estimation model | Small | daily_plans history |
| `/api/business/*` endpoints (6) | Medium | All backend |
| Dashboard page (frontend) | Large | All API endpoints |
| Stale listing detection | Small | active_listings + inventory |

**Estimated total effort: 3-4 focused sessions** (assuming Opportunity Finder is stable)

## Dependencies

- Inventory must have real data (user needs to enter their cards)
- Opportunity Finder must be producing reliable results
- SCP/comp pricing must work for owned cards (not just pipeline-discovered cards)

The biggest chicken-and-egg problem: the planner needs inventory data to generate plans, but entering 1,000 cards manually is a massive time investment. Solutions:
1. Start with just the 60 listed cards (pull from eBay via API -- Milestone 3)
2. Bulk import via CSV (user exports from eBay seller hub)
3. Ignore base cards entirely at first -- only track cards worth >$5
4. Lot the base cards as the FIRST action the planner recommends

## Relationship to Existing Milestones

This feature spans multiple existing milestones:
- **Milestone 1** (Make Money From UI): Dashboard becomes the primary UI
- **Milestone 3** (eBay Account Integration): Auto-import purchases/sales feeds the planner automatically
- **Milestone 4** (Smarter Decisions): Sell-through rates, price velocity feed into action prioritization
- **Milestone 5** (Ship It): Dashboard is the landing page at ragnarokgamez.com

Suggested insertion: **Milestone 2.5** -- after "Trust the Data" (need reliable pricing) and before eBay OAuth (which automates data entry).

## Consequences

**Positive:**
- Transforms the platform from "tool" to "business operating system"
- Forces honest math about income trajectory (no fantasy projections)
- Connects every feature (opportunities, inventory, pricing) into one workflow
- Daily plans reduce decision fatigue -- user opens app, sees what to do
- Capital tracking prevents overextending

**Negative:**
- Requires inventory data entry (cold start problem)
- Daily snapshot generation adds a background job
- Goal math might be discouraging early on ($1K -> $120K is a multi-year journey)
- Adds complexity to an already feature-rich system

## Open Questions

1. Should the planner account for shipping supply costs (boxes, tape, labels)?
2. Should it track time spent per session for pace learning?
3. How aggressive should catch-up recommendations be? (Never more than 1.5x normal day?)
4. Should it recommend WHEN to withdraw profits vs reinvest? (e.g., "You've hit $5K capital -- consider taking $500 out")
5. Should base card lots be auto-generated (group by team/year) or manual?

## Related Decisions

- ADR-004: Demand-driven refresh (snapshot generation is event-driven, not cron)
- ADR-005: User model (business_goals scoped to user_id from day one)
- Milestone 3: eBay OAuth (auto-feeds inventory + sales data)
- Milestone 8: Card recognition (solves the bulk inventory entry problem)
