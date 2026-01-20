# Acquisition Pipeline Plan

## Goal
Build an acquisition workflow that finds and evaluates trading card deals, guides purchases based on available cash, and records acquisitions in the local database before handing off to the sales phase.

## Workflow Overview
1. **Source Discovery (Marketplaces)**
   - Scan Facebook Marketplace, eBay, and other marketplaces for listings related to trading cards (football, basketball, hockey, baseball, etc.).
   - Collect listing data (title, price, seller info, photos, location, shipping, listing URL).

2. **Screening & Categorization**
   - Scan listings for card details (player, year, brand, grading, condition).
   - Group listings into strategy categories:
     - Single-card sale
     - Lot sale
     - Bundle package
     - Other (misc or mixed)

3. **Buy Strategy & Budget Gate**
   - Evaluate potential ROI and fit to strategy.
   - Filter by available cash-on-hand (only what is approved for spending).
   - Rank targets by expected value, urgency, and seller responsiveness.

4. **Seller Outreach & Negotiation**
   - Reach out directly to sellers.
   - Track negotiation status, counteroffers, and agreed terms.

5. **Acquisition Logging (Local DB)**
   - Once a deal is agreed, write all acquisition details into the local database.
   - Track purchase price, fees, shipping, and seller details.

6. **Physical Receipt & Handoff**
   - When cards are received, mark as acquired in the database.
   - Move item into the sales-cycle pipeline.

## Dependencies To Build Next
1. **Marketplace Intake**
   - Listing schema (normalized fields)
   - Importers/scrapers or manual capture process

2. **Classification & Scoring**
   - Rules for category assignment
   - ROI estimation and buy/hold strategy rubric

3. **Budget Module**
   - Cash-on-hand tracker
   - Reserved vs. available funds

4. **Outreach Tracker**
   - Seller contact status
   - Message templates and communication history

5. **Database Integration**
   - Acquisition table(s)
   - Lifecycle status fields

## Open Questions
- Which marketplaces should be prioritized beyond Facebook Marketplace and eBay?
- What is the minimum data required to qualify a listing for evaluation?
- Do we need separate strategies for graded vs. ungraded cards?
- How should we handle lots with incomplete metadata?
