# Ragnarok Gaming — Strategy & Gameplan

**Written:** 2026-07-17. This supersedes the $120k/year target in `business_goals` (already updated in the DB to a $3,600/year Phase 1 target — see below for why).

## The one-sentence diagnosis

You have one real, working edge (finding and flipping specific high-value singles on eBay) buried under six months of parallel, unfinished effort (marketplace build-out, multi-marketplace scrapers, card scanning automation, box breaks, live streaming) that never individually got enough attention to prove out or die. The fix isn't more tools — it's sequencing: one phase at a time, each with a number that tells you whether to continue or stop, instead of everything running at once with no clear signal.

**No new purchases of any kind — no box breaks, no eBay buys, no Whatnot buys — until Phase 1 below is proven.** Every dollar available goes toward turning existing inventory into cash and proving the core loop, not acquiring more inventory.

---

## Phase 1 (now → 4 weeks): Prove the core loop, on what already exists

**Goal:** prove that high-value single-card arbitrage is actually profitable for you, in reality, not in pipeline math.

**Good news buried in today's numbers:** turning off Promoted Listings (already done) likely already fixed most of the margin problem. Recomputing your five historical "top flips" at the real ~15% FVF-only rate instead of the 27.5% blended rate: James Wood auto (~+$34), Griffin Sapphire (~+$6), Arenado auto (~+$7), Trout RC (~+$2) all turn profitable; only the Yamamoto lot stays negative (~-$7). **4 of 5 already work now that Promoted is off.** That's the real signal to build on — not a new tool, a decision you already made.

**Actions:**
1. Do nothing to inventory except sell what's already listed. The 10 core eBay listings ($658.96 total ask) are the whole game this month.
2. For the 4 listings with real watcher interest but no sale (Kurtz $225/10 watchers, McGonigle $215/6, Morillo $35/8, Betts $14/8): Best Offer is now on. If no offers come in within 2 weeks, drop price 10-15% rather than waiting indefinitely — a watcher who hasn't bought at the current price after weeks isn't going to convert by inertia.
3. Track every sale: price, real fees (~15%), shipping cost, net profit. That's it — one line per sale.

**Exit criteria (check on 2026-08-14):**
- **≥3 of the 10 core items sold at real net profit** → Phase 1 passed, move to Phase 2.
- **Fewer than 3 sold, or sold at a loss** → the core strategy doesn't work at this scale/price point yet. Stop and reassess before doing anything else — don't advance to Phase 2 on hope.

**Time budget:** 2-3 hours/week, one sitting. Checking offers, adjusting one or two prices, logging sales. Not 20 hours. The plan has to survive an inconsistent week, not require a perfect one.

---

## Phase 2 (only after Phase 1 passes): Clear the backlog

**The 213 pulled eBay listings + the several hundred never-catalogued cards from this year's box breaks.**

1. **Sort by real price, not guesswork.** For each card, read the card number off it and run the SCP exact-number lookup (proven reliable earlier today — no sports knowledge needed, no AI vision required). ≥$10 → goes into the Core tier, tracked individually in the Ragnarok `Inventory` table (currently empty — start using it for real). <$10 → Bulk tier, never tracked individually again.
2. **Bulk tier → Whatnot lots, not individual eBay listings.** Split into 3-4 themed lots (Chrome/Refractor, Rookies, Inserts), floor ~$25-40/lot. This is where "sell each for $2+, don't care how" actually gets satisfied — not by chasing $2 on 200 individual listings, but by lots that average well above that.
3. **Run ONE test Whatnot show before committing to a cadence.** Your account has zero show history — that's the real finding from today, not "wrong time of day." One show, tracked: peak viewers, sales, revenue. That number tells you whether to invest more time in streaming or treat Whatnot purely as an occasional bulk-clearance tool.

**Exit criteria:** backlog converted to cash (however much that turns out to be) within 6-8 weeks of starting Phase 2. This phase has no profit bar — it's cleanup, and any positive number is a win over cards sitting in a box doing nothing.

---

## Phase 3 (only after Phase 1 & 2 are both working): Decide on automation spend

Card-scanning automation (Nova failed testing, GPT-4o blocked on billing, Claude vision showed promise on 4 cards but unvalidated at scale) is a real cost decision — not free, not proven at volume. Don't spend money here until there's a proven, cash-positive operation big enough that the time saved is worth the per-card API cost. Until then: manual entry through the SCP number lookup is slower but free and already proven to work.

## Phase 4 (not now): Expansion

Basketball/football, the marketplace/Stripe build, comc-scraper, lot-vision — all genuinely exist as half-finished work in git branches. All stay parked. Nothing here until Phases 1-2 prove the baseball-singles business works standalone. You said it yourself: get good at baseball first.

---

## Answering the specific list you asked about

- **Process:** sequential phases with pass/fail numbers, not parallel effort on everything.
- **Business planning:** goal is $3,600/yr for Phase 1 (not $120k) — small enough to actually be true, revisited upward only after hit for 2-3 consecutive months.
- **Infrastructure:** frozen. No new dev until Phase 1 passes.
- **Better/fewer/more cards:** fewer, better-vetted. No more box breaks. When buying resumes, it's only through the proven single-card pipeline, never blind boxes.
- **Platforms:** eBay = Core tier, primary. Whatnot = Bulk tier + one test show, nothing more yet. CollX = drop it.
- **Inventory management:** two-tier (Core individually tracked, Bulk never individually tracked). No cross-platform auto-sync — you don't have API/login access to build it, and it's not worth building manually yet at this scale.
- **Marketing/livestream:** not applicable until there's a show history to even improve on. One test show is the marketing experiment.

## The single most important rule

If a phase's exit criteria isn't met, that's information, not failure to push through. Stop, look at the number, decide fresh — don't keep grinding on a phase that isn't working because quitting feels bad. The last six months of parallel effort happened because nothing ever got a clean stop/go signal. This document exists so every phase has one.
