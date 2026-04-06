# Testing strategy — correctness vs outcomes

ADR-003 defines **pytest layers** (unit, integration). This doc adds the **product layer**: tests and checks that ask whether the system is **achieving the goal** (find real, buyable mispricings with **trustworthy** identity and comps), not only whether functions return without error.

## Operating principle: measure, don’t debate

Effectiveness of **any** stage (queries, matchers, filters, UI) should be **decidable from data** on a normal day — not re-argued from first principles.

- **Pipeline health** is read from **`job_runs.results_summary`** and the diagnose/audit scripts (Layer B). If auction **`auctions_searched`** is tiny vs **`ebay_total_hint`** on product-line queries, that is **our** retrieval/slice problem, not “eBay has no cards.”
- **Trust** is read from **verification outcomes** (Layer C): identity and comps must **converge** across sources. A persistent mismatch after the defined validation chain is a **defect** (process or code), not an acceptable gray area.

**North star:** Rows on Ragnarok should be **trustable without second-guessing**. Until then, every surfaced row should carry an honest **verification state** (`verified` / `pending` / `conflict`) so “unreliable” is visible in data, not only in your head.

### Daily / per-run expectations (examples — tune thresholds over time)

| Signal | Where | Expectation (directional) |
|--------|--------|---------------------------|
| Auction raw retrieval | `auctions_searched`, `step1_query_stats`, `ebay_total_hint` | Enough unique listings that **low opportunity count** is explained by **economics/identity**, not by “we only pulled 50 items.” |
| Auction funnel | `qualified`, `step2_skip_reasons`, `step3_*` | Know **which stage** dominates; if Step 2 parse skips dominate, invest in **parsing/aspects**, not min-profit. |
| BIN retrieval | `ebay_listings_fetched_total`, `ebay_variation_stats` | Variations with **zero** `listings_fetched` vs **high** fetch + zero `passed_profit_roi` tell different stories (query vs filters). |
| Identity | CE + SCP + eBay image (manual or automated) | After **Collectors Edge** validation, **eBay vs SCP** should still disagree rarely; if they do, **open a concrete fix** (matcher, set/parallel, or QA rule). |
| Sold reality | `sold_comps` / 130point vs SCP | Systematic divergence → pricing or wrong-row risk; track as **outcome** metric. |

These are **product SLOs** in spirit: adjust numbers as the business learns, but **keep** the habit of “today’s run vs expectation.”

## Layer A — Correctness (existing)

- **Unit:** parsing, matching helpers, scraper response shapes (mocked).
- **Integration:** DB, API routes, migrations against a real database.
- **QA markers:** regressions for bugs found manually (`pytest -m qa`).

Run: `pytest tests/unit`, `pytest tests/integration`, see [PIPELINE-OPS.md](../../PIPELINE-OPS.md).

## Layer B — Pipeline / coverage health (automatable smoke)

These do not prove profit; they prove we are **not blind** or **not stuck at zero**.

| Check | What it answers |
|--------|------------------|
| `job_runs.results_summary` (BIN + auction) | Funnel counts: searched → qualified → opportunities; Step 2/3 reasons |
| `scripts/audit_auction_pipeline.py` | Active vs ended auction rows; latest funnel JSON |
| `scripts/diagnose_auction_query_efficiency.py` | Which Browse `q` strings add deduped listings vs burn quota (`step1_query_stats`) |
| `scripts/diagnose_bin_ebay_variation_stats.py` | Per SCP variation: `listings_fetched` vs `passed_profit_roi` (`ebay_variation_stats` on `opportunity_finder`) |

**Rule of thumb:** if Layer B collapses (e.g. `qualified` → 0, or every query `new_after_dedupe` ≈ 0), fix **retrieval / queries / parsing** before debating min-profit.

## Layer C — Outcome / trust (goal-aligned)

**Goal:** What appears on **RagnarokGamez** should be **the same physical card** as the eBay listing, tied to the **correct** SCP row, with **comps** that survive cross-checks. With **eBay imagery**, **SCP product art**, **Collectors Edge**, and **130point / `sold_comps`**, persistent inaccuracy is **not** hand-waved — it maps to a **specific** broken step (match, parse, parallel, or pricing source).

**Intended verification chain (conceptual order):**

1. **Visual / listing** — eBay gallery (and title/aspects) represent what is for sale.
2. **SCP row** — Catalog identity + `scp_url` product image should match that listing.
3. **Collectors Edge** — Independent read from photo (`collectors_edge_photo_run`, `ce_extracted`, `ce_pipeline_analysis`).
4. **130point / sold comps** — Sold reality for the **same** SKU (player/year/#/parallel as resolved); contradicts SCP or CE → investigate before trusting “profit.”

If **CE agrees with the listing** but **SCP match disagrees**, the bug is **our SCP match or catalog choice**, not “the market is wrong.” If **all sources disagree**, the row must not ship as **verified** until resolved.

Today much of this is **partly manual**; the product move is to **automate gates**, **store verification state on the opportunity**, and **measure disagreement rates** per run.

Layer C metrics should include:

1. **Identity precision** — Rate of agreement across eBay image, SCP art, and CE structured fields; track over time.
2. **Economic calibration** — `sold_comps` / SCP / pipeline profit for the same resolved identity; flag systematic bias.
3. **Coverage vs missed** — Reference sets (hot SKUs, manual spot checks) vs what the pipeline emitted.

### Pytest marker

```ini
# pytest.ini
outcome: Goal-aligned / funnel / trust metrics (may need DB or fixtures)
```

Use **`@pytest.mark.outcome`** for tests that encode **thresholds** (e.g. “parser accepts ≥ X% of titles from fixture set”) or **regression baselines** for funnel JSON shapes. Many Layer C checks will remain **scripts + dashboards** until metrics stabilize.

## When something “fails” Layer C

Question **everything** in scope: process, data flow, exclusion rules, scraper filters, error handling, UI copy. Layer C failures are **product** failures, not just test failures.

## Related docs

- [ADR-003](../architecture/decisions/ADR-003-testing-strategy.md) — original testing decision
- [KNOWN-ISSUES.md](../KNOWN-ISSUES.md) — false positives / mismatch patterns
- [PIPELINE-OPS.md](../../PIPELINE-OPS.md) — operational audits
