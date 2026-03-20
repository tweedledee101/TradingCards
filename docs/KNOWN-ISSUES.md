# Known Issues

Documented problems found during pipeline runs. Grouped by category so patterns inform priorities.

**How to use this file**: When you spot a bad result, add it under the right category (or create a new one). Update the frequency and add the example. Over time, the categories with the most entries and highest impact tell us what to fix first.

---

## Categories

| Category | Count | Impact | Status |
|----------|-------|--------|--------|
| [Reprint / Replica Match](#reprint--replica-match) | 5 | High -- inflates profit by 10-100x | Partially Fixed (REPRINT_PATTERNS) |
| [Wrong Variation Match](#wrong-variation-match) | 4 | High -- completely wrong card | Partially Fixed (KNOWN_SETS) |
| [Suspiciously Low Buy Price](#suspiciously-low-buy-price) | 1 | Medium -- likely misidentified listing | Fixed (MIN_PRICE_RATIO 0.30) |
| [Grade Mismatch](#grade-mismatch) | 2 | High -- compares wrong price tier | Open |
| [Variant Sub-Type Mismatch](#variant-sub-type-mismatch) | 1 | High -- different card entirely | Open |
| [Stale SCP Price](#stale-scp-price) | 4 | High -- historical price, not current | Open |
| [Team Set / Multi-Card](#team-set--multi-card) | 1 | High -- listing is not a single card | Open |
| [Misclassified SCP Sales](#misclassified-scp-sales) | 1 | High -- SCP data itself is wrong | Open |

---

## Reprint / Replica Match

**Problem**: eBay query matches reprints, stickers, Project 2020 cards, and Shoebox Treasures that reference the original card number in their title. SCP price is for the real card, so profit calculation is wildly inflated.

**Impact**: High. Creates false positives with 2,000-6,000% ROI that look incredible but are worthless. Pollutes the opportunity list and erodes trust in results.

**Detection signals**:
- Title contains "Replica", "Sticker", "Project 2020", "Project 70", "Shoebox Treasures", "Reprint"
- Buy price is under $15 for a card SCP prices at $200+
- Multiple listings at the same low price point (mass-produced reprints)

### Examples (from 2026-03-20 full scan)

| # | Card | SCP Price | Buy Price | eBay Title | URL |
|---|------|-----------|-----------|------------|-----|
| 14 | Mike Trout 2011 Topps Update #US175 Base | $255.89 | $3.95 | "2011 Topps Update Mike Trout Rookie Card RC #US175 \| Die-Cut RepIica Sticker" | [ebay](https://www.ebay.com/itm/358349883969) |
| 15 | Mike Trout 2011 Topps Update #US175 Base | $255.89 | $3.95 | "Mike Trout, 2011 Topps Update Rookie Card RC #US175 \| Die-Cut RepIica Sticker" | [ebay](https://www.ebay.com/itm/358312822510) |
| 16 | Mike Trout 2011 Topps Update #US175 Base | $255.89 | $5.15 | "2025 SHOEBOX TREASURES '2011 TOPPS UPDATE #US175' #22 MIKE TROUT" | [ebay](https://www.ebay.com/itm/287033229220) |
| 17 | Mike Trout 2011 Topps Update #US175 Base | $255.89 | $8.38 | "MIKE TROUT TOPPS PROJECT 2020 #35 2011 Update #US175 RC Andrew Thiele" | [ebay](https://www.ebay.com/itm/256686848700) |
| 18 | Mike Trout 2011 Topps Update #US175 Base | $255.89 | $11.96 | "TOPPS PROJECT 2020 #399 MIKE TROUT by Artist KING SALADEEN" | [ebay](https://www.ebay.com/itm/266860710811) |

**Frequency**: 5 of 30 visible results (17%). Likely much higher across all 618 opportunities.

---

## Wrong Variation Match

**Problem**: eBay query includes a variation name (e.g., "SSP") or short card number (e.g., "#1") that matches unrelated listings. The returned card is a completely different product -- different set, different parallel, different year -- but shares a keyword.

**Impact**: High. The opportunity is for a card that doesn't exist at that price. User would buy the wrong card entirely.

**Detection signals**:
- eBay title contains set names not in the SCP variation (e.g., "Gold Label" when SCP says "Topps")
- eBay title contains parallel names not in the SCP variation (e.g., "Red Foil /25" when SCP says "SSP")
- Short card numbers (#1, #5) matching broadly across titles
- "Bat Down" vs "Bat Pointing Up" -- opposite variation names

### Examples (from 2026-03-20 full scan)

| # | Card | SCP Price | Buy Price | eBay Title | Problem | URL |
|---|------|-----------|-----------|------------|---------|-----|
| 10 | Mike Trout 2020 Topps #1 SSP | $583.73 | $79.99 | "2020 Topps Gold Label #1 Mike Trout Class 3 RED FOIL /25 SSP" | Gold Label Red Foil, not base Topps SSP | [ebay](https://www.ebay.com/itm/257018495214) |
| 11 | Mike Trout 2020 Topps #1 SSP | $583.73 | $86.99 | "MIKE TROUT 2020 Topps Gallery /99 GREEN PARALLEL #1 SP SSP" | Gallery Green /99, not base Topps SSP | [ebay](https://www.ebay.com/itm/356377376218) |
| 12 | Mike Trout 2020 Topps #1 SSP | $583.73 | $87.34 | "MIKE TROUT 2020 Topps Gallery /99 GREEN PARALLEL #1 SP SSP" | Gallery Green /99, not base Topps SSP | [ebay](https://www.ebay.com/itm/277305943798) |
| 21 | Ronald Acuna Jr 2018 Topps #698 Bat Down | $199.99 | $49.50 | "2018 Topps *Bat Pointing Up* #698 Ronald Acuna Jr PSA 9" | "Bat Pointing Up" is the opposite variation | [ebay](https://www.ebay.com/itm/186441690291) |

**Frequency**: 4 of 30 visible results (13%). Short card numbers (#1, #5) are the worst offenders.

---

## Suspiciously Low Buy Price

**Problem**: A listing appears at a price far below what the card should cost, suggesting the listing is misidentified, a different condition than expected, or a bait listing.

**Impact**: Medium. Could be a real deal, but more likely the listing is not what it appears. Needs manual verification.

**Detection signals**:
- Buy price is less than 5% of SCP market rate
- Card is not a common base card (has a specific parallel or variation)

### Examples (from 2026-03-20 full scan)

| # | Card | SCP Price | Buy Price | ROI | eBay Title | URL |
|---|------|-----------|-----------|-----|------------|-----|
| 28 | Jasson Dominguez 2024 Topps #60 True Photo | $64.99 | $1.45 | 4369% | "2024 Topps Series 1 - Jasson Dominguez #60 True Photo (RC)" | [ebay](https://www.ebay.com/itm/167395602633) |

**Frequency**: 1 of 30 visible results (3%). Need more data to assess.

---

## Adding New Issues

When you find a bad result, add it like this:

1. Pick the right category (or create a new one)
2. Add a row to the examples table with: result number, card, SCP price, buy price, eBay title, URL
3. Update the category count in the summary table at the top
4. Update frequency estimate if the pattern is clearer

---

## Grade Mismatch

**Problem**: Pipeline compares SCP ungraded price to a graded eBay listing (or uses PSA 10 SCP price for an ungraded listing). The profit calculation is based on the wrong price tier.

**Impact**: High. Creates false positives where the "profit" is actually the grading premium, not arbitrage.

**Detection signals**:
- eBay title contains "PSA 9", "PSA 10", "BGS", "SGC" but pipeline used ungraded SCP price
- eBay listing is ungraded but pipeline used graded SCP price
- Profit seems too good for a common card

### Examples (from 2026-03-20 manual validation)

| Card | SCP Ungraded | SCP PSA 10 | Buy Price | Pipeline Used | Problem |
|------|-------------|------------|-----------|---------------|----------|
| Juan Soto Gold Stars #224 (2020 Topps Complete Set) | $1.50 | $30.00 | $9.99 (ungraded) | $28.46 (PSA 10) | Ungraded listing matched to PSA 10 price |
| Jordan Walker Father's Day Blue #344 | $220.00 | N/A | $149.95 (PSA 9) | $220.00 (ungraded) | PSA 9 listing matched to ungraded price |

---

## Variant Sub-Type Mismatch

**Problem**: Pipeline matches a sub-variant to the wrong SCP product. "Magenta Speckle Refractor" (/350) matched to "Magenta Refractor" (/399) -- different cards with different print runs and values.

**Impact**: High. Completely wrong price comparison.

### Examples (from 2026-03-20 manual validation)

| Card | SCP Product | SCP Price | eBay Listing | Actual Value |
|------|------------|-----------|--------------|-------------|
| Juan Soto 2021 Topps Chrome #150 | Magenta Refractor /399 | $4.25 | Magenta Speckle Refractors /350 at $13.99 | Pipeline showed $22.69 profit -- actually overpriced |

---

## Stale SCP Price

**Problem**: SCP price based on sales from 1-3 years ago. Market has moved significantly since then. Pipeline treats the stale price as current market value.

**Impact**: High. Creates opportunities that don't exist at current market prices.

**Detection signals**:
- SCP volume shows "rare", "1 sale per year", "2 sales per year", "3 sales per year"
- Most recent SCP sale is 6+ months old
- Price trend is clearly declining across the few sales that exist

### Examples (from 2026-03-20 manual validation)

| Card | SCP Price | Last Sale | Last Sale Price | Volume | Trend |
|------|-----------|-----------|-----------------|--------|-------|
| Jordan Walker Father's Day Blue #344 | $220.00 | Sep 2024 | $190.00 | 3/year | $470 -> $330 -> $220 -> $190 (down) |
| Jordan Walker Brick by Brick Auto #BB-16 | $62.50 | Jul 2023 | $70.00 | 3/year | Erratic, last sale 2 years ago |
| Jordan Walker Leaf Ultimate Auto #BA-JW1 | $26.50 | N/A | N/A | rare | No recent sales at all |
| Juan Soto Gold Mosaic #113 /10 | $300.00 | Jan 2022 | $300.00 | 1/year | Single sale from 3+ years ago |

---

## Team Set / Multi-Card

**Problem**: eBay listing is a team set or multi-card lot, not a single card. Pipeline matches it because the card number appears in the title.

### Examples (from 2026-03-20 scan results)

| Card | SCP Price | Buy Price | eBay Title | Problem |
|------|-----------|-----------|------------|----------|
| Nolan Ryan 1972 Topps #595 | $94.61 | $39.95 | "1972 Topps California Angels Team Set w/o #595 Nolan Ryan (27)" | Team set WITHOUT the Ryan card |

---

## Misclassified SCP Sales

**Problem**: SCP product page has sales from completely different cards misclassified under the wrong product. When a card has only 2-3 total sales, one misclassified entry corrupts the entire price.

### Examples (from 2026-03-20 manual validation)

| SCP Product | SCP Price | Misclassified Sales |
|-------------|-----------|--------------------|
| Jordan Walker [Gold] #UD-JW1 (2020 Leaf Ultimate Destinations) | $277.50 | Shows Juan Soto sales ($525, $29.99) on a Jordan Walker page |

---

Categories to watch for as we see more data:
- **Lot / Multi-Card Listings**: Single price for multiple cards, not one card
- **Wrong Player**: eBay returns a different player's card
- **Damaged / Misgraded**: Card condition doesn't match SCP assumption
- **International / Shipping Trap**: Low price but high international shipping
- **Non-PSA Grading Premium**: Arena Club, TAG, etc. worth less than PSA-based SCP prices suggest
