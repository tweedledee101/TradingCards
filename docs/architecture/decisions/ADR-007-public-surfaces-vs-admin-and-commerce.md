# ADR-007: Public Surfaces vs Admin, Storefront, and Future Commerce

**Date:** 2026-04-05  
**Status:** Accepted (directional — most items not built yet)  
**Deciders:** Product owner

## Context

RagnarokGamez serves two different audiences:

1. **Operator (single admin)** — needs the full **operations console**: opportunities, business planner, inventory, pipeline-adjacent data, and any internal research views (e.g. trending).
2. **Visitors / customers** — should see only what the operator chooses to expose: primarily a **storefront** (browse inventory / listings), marketing pages, and eventually **events** (breaks, livestreams). They must **not** receive the **arbitrage tooling**, pipeline logic, or data products that create competitive advantage.

The operator also intends **future** on-site **checkout** and payment integration (**Stripe** for card payments; **Plaid** or similar if bank-link / payout flows are needed), plus **breaks**, **livestreams**, and a **dynamic calendar** (whether customers log in to see it is TBD).

## Decision

### 1. Two product planes

| Plane | Who | What |
|--------|-----|------|
| **Admin / ops** | Single designated admin (only) | Opportunities, Business OS, internal inventory management, trending/research as needed, any API that encodes buying logic or SCP/eBay arbitrage workflows |
| **Public** | Everyone else | Landing, marketing, **storefront** (mirror of sellable inventory / eBay listings), future checkout, optional calendar/events |

**Rule:** Arbitrage and “how we find deals” stay **admin-only**. The public site is **retail + brand**, not a SaaS clone of the operator stack.

### 2. Single admin

There is **one** human operator with full access. No requirement today for multi-seat admin. (Existing user/role fields may exist for future expansion; **policy** is still “effectively one admin” until explicitly changed.)

### 3. Commerce (future)

- **Stripe:** primary path for **checkout** when the operator enables on-site purchase.
- **Plaid (or similar):** consider when **bank-linked** flows add value (payouts, ACH, reconciliation)—not interchangeable with Stripe for simple card checkout; choose per flow.
- **eBay:** may remain a **fallback or fulfillment** channel (e.g. “also on eBay”) even after checkout exists.

### 4. Events (future)

- **Breaks** and **livestreams** are first-class **content/commerce** ideas, not ops tooling.
- **Dynamic calendar:** implement when event volume justifies it; **access** (public vs logged-in customer vs admin-only draft events) is **TBD** per event type.

### 5. Implementation guidance (when built)

- **Frontend:** public routes **outside** the current all-authenticated shell; admin routes require **authenticated + admin** (Cognito group claim, env allowlist, or single `owner` user id — choose one and enforce on **API** as well as UI).
- **API:** no public endpoints that return opportunity-finder payloads, business capital detail, or pipeline secrets; storefront reads **curated** listing/inventory DTOs only.

## Consequences

- Requires an explicit **route and API audit** when storefront/checkout land: default-deny for new routes until classified public vs admin.
- Marketing landing and storefront work can proceed **without** exposing internal logic.
- ADR-005 (user model / future teams) remains valid for **data shape**; this ADR constrains **what product surfaces exist**, not the full multi-tenant future.

## Related

- [ADR-005](./ADR-005-user-model.md) — users, roles, opportunity scoping  
- [ADR-002](./ADR-002-ebay-primary-source.md) — eBay as commerce channel  
- [ROADMAP.md](../../ROADMAP.md) — Milestone 3 backlog  
