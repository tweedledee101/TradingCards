# Testing strategy — correctness vs outcomes

ADR-003 defines **pytest layers** (unit, integration). This doc adds the **product layer**: tests and checks that ask whether the system is **achieving the goal** (find real, buyable mispricings with **trustworthy** identity and comps), not only whether functions return without error.

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

**Rule of thumb:** if Layer B collapses (e.g. `qualified` → 0, or every query `new_after_dedupe` ≈ 0), fix **retrieval / queries / parsing** before debating min-profit.

## Layer C — Outcome / trust (goal-aligned)

**Goal:** What appears on **RagnarokGamez** as an opportunity should be **the same card** as the eBay listing, priced against the **right** SCP row (and comps), with explicit **verification** when automation is uncertain.

Today this is **partly manual** (Collectors Edge photo flow, Nova vision queue, `ce_pipeline_analysis`). Long-term, Layer C should include:

1. **Identity precision** — Sample (or full) audit: eBay image + SCP product image + CE result agree on player / year / # / parallel; track disagreement rate over time.
2. **Economic calibration** — Backtest or sample: sold prices vs SCP vs pipeline “profit” for a cohort; flag systematic bias.
3. **Coverage vs missed** — Compare pipeline output to a reference set (e.g. sold_comps hot SKUs, manual watchlist).

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
