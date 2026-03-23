# ADR-005: User Model, Personalization, and Opportunity Scoping

**Date:** 2026-03-22
**Status:** Accepted
**Deciders:** Development Team

## Context

Before deploying to AWS, we need to answer three questions:

1. How do users authenticate and what's the user model?
2. How do users personalize their experience (settings, filters, pipeline strategy)?
3. How do we prevent 500 users from competing for the same single eBay listing?

## Decisions

### 1. Solo Users First (Option A)

Launch with single-user accounts. No teams, no social features, no shared profiles.

Future tiers (designed for but not built):
- **Business/team**: one billing account, multiple seats, shared inventory, role-based access
- **Friends/social**: view-only access to each other's profiles, shared watchlists

To avoid painful retrofitting, the database will include `user_id` on all user-scoped tables from day one, even though there's only one user at launch.

### 2. Personalized Pipeline Results

Each user's pipeline runs produce results scoped to their `user_id`. The Opportunities page shows only their results.

User settings (stored as JSONB in `user_settings` table):
- Theme preference (dark/light/custom)
- Default filters: min profit, max budget, ROI threshold, sports, players
- Pipeline strategy presets (configurable filter combinations)
- Notification preferences

Settings persist across sessions. The user never has to re-enter their preferences.

### 3. Opportunity Scoping

The core problem: one eBay listing = one buyer. Showing the same listing to everyone creates a frustrating race.

**Launch (solo users)**: Each user runs their own filters, sees their own results. No conflict because there's one user.

**Multi-user (future)**: Personalized filters naturally reduce overlap (different budgets, players, sports). For remaining overlap:
- Soft-claim: when a user views/clicks an opportunity, others see "2 people viewing"
- Pursued: when someone clicks the buy link, marked as "pursued" and deprioritized for others
- Time-windowed exclusivity and tiered access (free vs paid delay) are options but not committed

### 4. API and UI Are One Product

The React frontend is a client of the API. The API also serves external consumers (power users, spreadsheets, Discord bots).

- One API, two audiences: UI (session auth) + external (API keys)
- Rate limiting: UI gets generous limits, API keys get tiered limits
- Monetization lever: free tier = UI only, paid tier = API access

## Consequences

**Positive:**
- Solo launch is fast to build
- `user_id` on tables from day one prevents painful migration later
- Personalized results eliminate the "everyone sees the same deals" problem
- Settings persistence means the user never re-enters preferences

**Negative:**
- Multi-user features deferred (teams, social, shared watchlists)
- Need to build auth before public launch (Cognito or similar)
- API key management adds complexity for external access

## Implementation Notes

- `users` table: id, email, auth_provider_id, created_at
- `user_settings` table: user_id (FK), settings (JSONB), updated_at
- Add `user_id` column to: opportunities, inventory, watchlist, job_runs
- Auth: AWS Cognito (already on AWS, handles OAuth flows, free tier generous)
- Settings API: GET/PUT `/api/settings` (returns/updates user's JSONB blob)

## Related Decisions

- ADR-004: Demand-driven refresh (per-user refresh triggers)
- Milestone 3: eBay OAuth integration (per-user eBay tokens)
- Milestone 4.5: UI Behavior Tracking (user_events table)
