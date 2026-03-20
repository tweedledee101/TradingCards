# ADR-004: Demand-Driven Data Refresh (No Crons)

**Date:** 2026-03-20
**Status:** Accepted
**Deciders:** Development Team

## Context

The platform collects data from multiple external sources (eBay API, SportsCardsPro) and computes opportunities from that data. We need a strategy for keeping data fresh without wasting compute or API calls.

Traditional approach: cron jobs that run on fixed schedules (e.g., daily at 2 AM). This is the default pattern for most data pipelines.

## Decision

We will use **demand-driven refresh with deterministic staleness** instead of scheduled cron jobs.

No data is fetched unless someone needs it. No compute runs unless the existing data can no longer be trusted.

## Design Philosophy

Elegant simplicity. Effective, precise, decisive results. Costs managed as tightly as the code.

## How It Works

### Principle: The Data Knows When It's Stale

We already have enough information in the database to determine freshness without re-querying external sources:

- **Active listings**: eBay listings have end dates. At end_date + 1 second, we know it's gone. No API call needed.
- **Sold listings**: Immutable. A sale from March 18 is the same sale forever. Never re-fetch.
- **SCP market rates**: Move slowly (daily at most). Timestamp the last scrape. Trust it for 24 hours.
- **Opportunities**: Only stale when underlying listing expires/sells OR SCP price updates. Calculable from existing data.

### Refresh Triggers

Data is refreshed ONLY when:

1. **User requests data** and cached results are older than the staleness threshold
2. **Valid opportunity pool drops below a threshold** (too many listings expired)
3. **Manual trigger** via API endpoint (admin/developer use)

Data is NEVER refreshed because:
- A clock says it's 2 AM
- A fixed interval elapsed
- "Just in case" someone might need it

### Request Flow

```
User opens Opportunities page
    |
    v
API checks: do we have results < X hours old?
    |
    +-- YES --> serve cached results instantly
    |
    +-- NO  --> serve stale results with "refreshing" indicator
                kick off async background refresh
                update cache when done
                job_tracker prevents duplicate runs
```

### Staleness Thresholds

| Data Type | Staleness Threshold | Rationale |
|-----------|-------------------|-----------|
| Opportunities | 4-6 hours | Listings sell/expire throughout the day |
| Active listings | Known from end_date | Deterministic, no threshold needed |
| Sold listings | Never stale | Immutable historical data |
| SCP market rates | 24 hours | Prices update ~daily |
| Player rankings | 24 hours | Volume shifts slowly |

### Duplicate Run Prevention

The `job_runs` table (already built) prevents concurrent refreshes:

1. Before starting refresh, check: `is_running('opportunity_finder')`
2. If already running, skip -- another request triggered it
3. If not running, start and record in job_runs
4. All subsequent requests get the cache until refresh completes

## Alternatives Considered

### 1. Cron-Based Scheduling (Rejected)
**Pros:**
- Simple to implement (APScheduler, crontab, CloudWatch Events)
- Predictable execution times

**Cons:**
- Runs whether anyone needs the data or not (wasted compute)
- Fixed schedule can't adapt to demand patterns
- At scale, scheduled runs during peak hours degrade performance
- Costs accumulate regardless of usage
- "Dumb" -- no awareness of whether data actually changed

### 2. Polling-Based Refresh (Rejected)
**Pros:**
- Always fresh data

**Cons:**
- Constant API calls burn through eBay's 5,000/day limit
- SCP Selenium calls are expensive (browser spin-up)
- Most polls return "nothing changed"

### 3. Hybrid: Cron + On-Demand (Rejected)
**Pros:**
- Baseline freshness from cron, responsiveness from on-demand

**Cons:**
- Two systems to maintain
- Cron still wastes compute during low-usage periods
- Complexity without proportional benefit

## Consequences

**Positive:**
- Zero wasted compute -- every API call and scrape produces value
- AWS costs directly proportional to actual usage
- System scales naturally with demand (more users = more refreshes, fewer users = near-zero cost)
- No "the cron didn't run" debugging
- Deterministic staleness means no unnecessary external API calls

**Negative:**
- First request after long idle period sees stale data (mitigated by serving stale + refreshing)
- Slightly more complex than "just add a cron"
- Need to define and tune staleness thresholds

**Neutral:**
- Job tracker table already exists (migration_006)
- Background task execution needed (asyncio, ECS task, or Lambda on AWS)

## Worker/Core Separation

The data gathering workload (Selenium browsers, eBay API calls, opportunity computation) MUST run in a separate process from the core application (API, frontend, database reads).

### Core Application (always fast)
- API serves cached results from database
- Frontend renders from API responses
- Database handles reads during normal operation
- Never blocked by scraping or computation

### Worker (separate process, separate resources)
- Runs SCP Selenium scraping
- Makes eBay API calls
- Computes opportunities
- Writes results to database in small batches (not one giant transaction)
- Trickle-insert: 10 rows at a time, small commits, brief pauses between batches
- Database barely notices. API never hiccups.

### Why Not In-Process?
- Selenium spins up Firefox -- heavy CPU and memory
- eBay API calls block on network I/O
- A 40-player scan takes 30-60 minutes
- None of that should touch the process serving user requests

## AWS Implementation Path

- **Core app**: ECS service (always running, right-sized for serving)
- **Worker**: ECS task or Lambda (spins up on demand, dies when done, separate CPU/memory)
- **Database**: RDS -- worker writes to primary, API reads (read replica if needed)
- **No CloudWatch Events for scheduling** -- demand-driven only
- Worker triggered by API when cache is stale, not by a clock

## Related Decisions

- ADR-001: PostgreSQL database (cache storage)
- Job tracking system (migration_006_job_runs.sql, backend/utils/job_tracker.py)
