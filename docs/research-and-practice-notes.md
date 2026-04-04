# Research ↔ practice ↔ Ragnarok

**Purpose:** Turn **academic work**, **experienced flippers’ teachings** (blogs, YouTube, podcasts, forums), and **our own runs** into **testable hypotheses**—then align **data capture**, **pipeline behavior**, and **UI** with what we learn.

This file is meant to **grow**. Add links, one-line takeaways, and “how we’d falsify it in our DB/logs.”

### North star (same materials, systematized edge)

Grail flippers and volume arbers look different in the headlines, but they operate on the **same substrate**: listings, comps, grades, narrative, liquidity, and **moments when price ≠ your model of fair value**. The goal for Ragnarok is not to copy one persona—it is to **build the machine that**:

1. **Senses** — Ingest market + catalog + community signal (within **ToS, ethics, and attribution**—*appropriate* exploitation, not spray-and-pray scraping or spam).
2. **Understands** — Encode hypotheses (papers + practitioners + **your** logs) into **data we store** and **metrics we can query**.
3. **Prepares** — Surfaces *actionable* rows (opportunities, watchlists, capital checks) so you are **ready** when the window is short.
4. **Learns** — Closes the loop: outcomes and audits update **what we crawl, weight, and show** next.

That is **not** a single ship date; it is **successive layers** on the algorithms, processes, and tooling you already run (`find_opportunities`, auctions, worm, Business, audits). **Everyone’s experience at our fingertips** becomes leverage only when distilled into **hypotheses we measure**—this doc is the placeholder for that discipline.

---

## 0. If you feel lost — what we’re testing *first* (and what to look at)

**H1–H5 below are a menu, not homework.** You are not “behind” if none are active. Pick **one** concrete question at a time.

### Default experiment (until you pick something else): **funnel + identity sanity**

| Piece | Where | What to look for |
|--------|--------|------------------|
| **Auction funnel health** | `python3 scripts/audit_auction_pipeline.py --compare` (after a real auction run) | `opportunities_found`, `qualified`, `step2_skip_reasons`, `step3_*` — **deltas run-to-run**. Big swings with **no** code deploy → market; swings **right after** deploy → regression. |
| **BIN volume / QA** | `find_opportunities` logs, `job_runs`, optional `tests/qa/qa_opportunities.py` if you run it | Count of opps, `flagged_suspicious`, any QA rules firing. |
| **Same-card check (manual, 10 min)** | UI Opportunities: open **5 rows** (mix BIN + auction) | For each: does **eBay title/image** match the **SCP card identity** we stored? Jot **hit rate** (e.g. 4/5). That *is* data—it grounds **H2** (grade/tier mismatch) and **H4** (missing/wrong attributes) without new code. |
| **Liquidity reality check** | Card detail → player stats (when API returns data) | If **30d sales** is 0 or empty often, practitioner “liquidity matters” is telling you **charts will be empty** until the **card data pipeline** fills `sales`. |

**One-line log (optional):** Add a dated sentence under [§5](#5-open-experiments-backlog-prioritize-12) or a scratch file: `YYYY-MM-DD: audit compare …; 5-spot-check X/5 matched listing.`

### When you’re ready for a “named” hypothesis

- **H2 (grading / tier)** — Start the **grading alignment study** backlog item: spreadsheet of 20 opps with columns `title_grade_guess` vs `scp_column_used`.
- **H3 (planner vs reality)** — Run **hold-time** SQL once you have enough **inventory_sales** rows.
- **H5 (auctions)** — Only after you **log** whether you won/lost snipes (today that’s mostly **manual**; “hypothesis” waits on **outcome tracking**).

**Rule of thumb:** If you’re not looking at **audit output + a tiny manual sample** weekly, the academic rows are just reference—you’re not “testing” them yet. That’s fine; **this section is the on-ramp.**

---

## 1. Hypothesis loop (how to use this doc)

1. **Claim** — From a paper, a respected practitioner, or a Reddit thread with a coherent thesis.
2. **Operational definition** — What would we measure? (e.g. median days to sell at X% of SCP, % of “wins” that were raw vs graded, auction snipe fill rate.)
3. **What Ragnarok does today** — Pipelines, tables, API fields (honest “yes / partial / no”).
4. **Experiment** — Change one thing: new column, new `job_runs` counter, worm target list, Business assumption, UI label—not ten at once.
5. **Outcome** — After N runs or N manual reviews, keep, revert, or refine.

**Practitioner content** is not “less scientific”—it’s **high-context** and **time-stamped**. Cross-check against **sold data** (130point worm, `sales`, eBay sold where we have it) when a guru says “always” or “never.”

---

## 2. Academic sources (starter set) → Ragnarok mapping

| Source (topic) | Core idea | What we do in practice / code | Gap or experiment |
|----------------|-----------|------------------------------|-------------------|
| **NBA owners vs collectors** (*Atlantic Economic Journal* — valuation of players in salary vs card markets) | Card demand weights **individual performance** differently than team payroll contracts. | We price off **SCP + comps** keyed to **player + card identity**; not tied to salary data. | **H1:** Stars with “contract year” or trade rumors show **extra card volatility** beyond SCP refresh. **Test:** correlate optional **MLB news / call-up flags** (if we add them) with `sales` velocity or opportunity count. |
| **Third-party grading & demand** (*Atlantic Economic Journal* — NBA cards, grade premia) | **Grade is a huge price shifter**; raw vs PSA 10 are different goods. | `opportunities` / cards carry **SCP ungraded + grade 9 + PSA 10** where populated; inventory supports graded raw flags. UI shows some tier info. | **H2:** Mismatches (listing implies raw, SCP line is effectively **another tier**) drive bad buys. **Test:** sample flagged opps; tag **listing grade signals** from title (PSA, BGS, “raw”) vs **which SCP column** we used; store in QA or a review log. |
| **Platform pricing at conventions** (*Journal of Industrial Economics*) | Two-sided **venue** pricing (dealers vs attendees). | We are **eBay-first** digital; no convention module. | **Weak near-term fit.** If we ever model **fee + liquidity** across channels, reuse as analogy for **COMC vs eBay** take-home. |
| **Discrimination in card markets** (e.g. *Social Science Journal*, SSRN NBA card work) | Demographics may correlate with **price gaps** (often contested). | We do **not** model buyer/seller demographics. | **Only revisit** if we run **ethical, explicit** research design; not a default product feature. |
| **Collectibles as investments** (SSRN surveys; art/stamps long-horizon work) | **Costs, illiquidity, taste risk** eat nominal “alpha”; utility of holding matters. | **Business planner** (capital, targets, reinvest %) encodes some of this; pipelines optimize **spot edge** not portfolio variance. | **H3:** Track **realized** hold time from inventory → sale (we have inventory/sales tables). **Test:** compare **planner assumed** turnover vs **actual** `inventory_sales` / listing age. |
| **Hedonic pricing** (wine, toys, etc.) | Price = f(observed **attributes**): vintage, condition, scarcity. | **Player, year, set, #, parallel**, SCP tiers, sold comps — hedonic in spirit. | **H4:** Missing **attributes in listing text** (e.g. insert name) correlate with **false positives**. **Test:** mine `step2_skip_reasons` / manual review tags vs title token presence (analytics, not necessarily new hard filters). |
| **Auction markets for collectibles** (SSRN — theory + experiments) | **Non-pro bidders**, joy of winning → noisy prices; discipline and **timing** matter. | **Auction pipeline** + **scheduled bids** UI; snipe math in modal. | **H5:** “Good” auction opps **underperform** live if end-time clustering or thin bidding. **Test:** segment `opportunities` by **hours to end**, bid count; compare **realized** outcome if we log wins/losses post-hoc. |

---

## 3. Practitioner teachings (template — fill names & links)

Successful flippers repeat a few **themes**. Map each theme to our knobs when you add a specific author/video.

| Theme (generic) | Typical teaching | Ragnarok touchpoint | Data / UI to improve |
|-----------------|------------------|---------------------|------------------------|
| **Verify before you math** | If the **card in the photo** isn’t the comp, ROI is fiction. | Title + aspects + SCP row; **no image CV**. | Richer **listing text** in DB/API; **review checklist** in UI; optional future image hash / manual tag. |
| **Liquidity > sticker ROI** | High ROI on a card that **never sells** is a trap. | `sales`, velocity in **player stats**; volume filters in finder. | Surface **“sales in 30d”** or **worm comp count** on **Opportunity** cards more prominently when non-zero. |
| **Grade path** | Raw → sub → slab economics; **pop report** awareness. | SCP tier columns; `grading_population` exists in schema. | Wire **pop / grade scarcity** into **Card** modal or opportunities when card_id links exist. |
| **Seasonality / news** | Call-ups, playoffs, injuries move **marginal demand**. | Trending pipeline, MLB-adjacent data in roadmap. | Tight **watchlist ↔ worm ↔ BIN** on **spike players** (you already liked this direction). |
| **Fees and shipping** | Net after **all-in cost**. | We bake fees into profit calcs; shipping from eBay. | **Sensitivity** slider in UI (“if ship is $5 not $0”) — product idea. |

**Add rows** with `Source | URL | Date read | Takeaway | Hypothesis | Test in Ragnarok`.

### 3.1 Headline flippers vs what Ragnarok optimizes today

Press and YouTube often feature **extreme outcomes** on **iconic, illiquid, seven-figure** cards. That is a **different strategy layer** from **systematic eBay listings vs SCP/comps** inside typical **budget and min-profit** bands.

| Figure / story (public narrative) | What the story emphasizes | Strategy bucket | Overlap with current Ragnarok pipelines |
|-----------------------------------|---------------------------|-----------------|----------------------------------------|
| **Dave Oancea (“Vegas Dave”)** — e.g. Mike Trout **2009 Bowman Chrome Superfractor** sale cited in **multi-million** range | Massive **mark-to-market** gain on a **1/1**-style grail; timing, buyer pool, auction dynamics | **Concentrated risk**, trophy asset, often **long hold** + event sale | **Low.** We do not scan for 1/1 superfractors as a product class; identity + liquidity are different orders of magnitude. |
| **Kevin O’Leary** — reported **eight-figure** dual-auto / Jordan–Kobe tier pieces | **Capital allocation** into **museum-grade** collateral; media + network effects | **Ultra-HNW** deal flow, not “BIN under SCP” | **None** in automation; **analogy** only for “fee + who clears the trade.” |
| **Jesse Deveau / FreshPullz** (e.g. **~$2M revenue in ~13 months** in pandemic-era reporting) — **sealed boxes** + singles | **Sealed wax** velocity, boom-cycle demand, operational churn | **Inventory retail / box flipping** | **Partial.** Our stack is **singles**-centric (SCP card rows); **sealed product** would need **different SKUs, comps, and fraud rules**. |
| **Marshall Fogel** — **1952 Topps Mantle** / high-grade vintage icons | **Buy best copy, hold, sell into peak auction** | **Trophy collecting + auction consignment** | **Low** for daily opp finder; **relevant** to any future **“grail watch”** or auction-house data feeds. |

**Takeaway:** Those names are useful for **mindset** (conviction, liquidity events, grade/pop on icons) but **not a scorecard** for whether your **$10–$200 BIN arb** is “wrong.” Same hobby, **different game theory**: variance per trade, capital per position, and information sources barely overlap.

**If we ever want “whale-adjacent” hypotheses:** e.g. track **opportunities where SCP × implied rarity** exceeds a threshold, or **auction estimate** fields—**new module**, not a tweak to `min_profit` alone.

---

## 4. “What we’re doing” — code anchors (for honest comparison)

| Area | Primary locations |
|------|-------------------|
| BIN + scoring, flags | `find_opportunities.py`, `backend/api/routes/opportunities.py`, `tests/qa/` |
| Auction funnel | `find_auction_opportunities.py`, `scripts/audit_auction_pipeline.py`, `backend/utils/listing_card_identity.py` |
| Sold comps cache | `worm_130point.py`, `backend/scrapers/oneThirtyPoint_scraper.py`, `sold_comps` / related tables |
| SCP / Selenium | `backend/scrapers/sportscardspro_scraper.py`, `scp_cache`, `market_rates` |
| Capital & goals | `backend/services/business_planner.py`, `backend/api/routes/business.py` |
| Frontend truth surface | `frontend/src/pages/Opportunities.jsx`, `CardDetailModal.jsx` |

When a hypothesis fails, it’s often **here**—not because “strategy is wrong” but because **identity**, **tier**, or **stale comp** slipped through.

---

## 5. Open experiments backlog (prioritize 1–2)

**Suggested first “real” study after §0 spot-checks:** grading alignment (below).

- [ ] **Grading alignment study** — For N random stored opps: listing title grade tokens vs SCP column used; spreadsheet or `qa_flags` extension.
- [ ] **Velocity on opportunity list** — Show `recent_sales_30d` / comp count on BIN row when API has player stats (reduce liquidity traps without new gates).
- [ ] **Watchlist-driven worm** — Nightly worm `--player` list from trending top-K + manual watchlist table (if/when consolidated).
- [ ] **Hold-time truth** — SQL or small report: inventory purchase → sale duration vs Business planner assumptions.
- [ ] **Nova Act second pass on SCP misses** — Queue auctions/BIN rows where Step 3 had **no SCP match** (or step2 text skips with good photos): **`nova_act_listing_card_extract.py`** → normalized identity → retry **`find_scp_match_*`**; cap batch size and run off GitHub default runners if eBay friction is high.
- [x] **CDN + Nova multimodal → DB SCP** (first cut) — **`scripts/vision_retry_scp_from_images.py`**: `no_scp_vision_queue_sample` → download i.ebayimg URLs → Nova vision JSON → **`find_scp_match_in_db`**. Tune **`NOVA_VISION_MODEL`**, prompts, and parallel matching as needed.

---

## 6. Further reading (add DOIs / stable URLs as you go)

- Springer: *Are NBA Players Equally Valued by Team Owners and Trading Card Collectors?* (Atlantic Economic Journal).
- Springer: *Third-Party Grading as a Useful Measure of Demand: Evidence from NBA Cards* (Atlantic Economic Journal).
- Wiley: *Platform Pricing at Sports Card Conventions* (Journal of Industrial Economics).
- SSRN: collectibles auction / investment survey papers (search: “collectibles auction market efficiency”).

---

**Maintainers:** When a hypothesis **ships** or **dies**, add one line to [STATUS.md](../STATUS.md) or this file’s backlog so the loop stays visible.
