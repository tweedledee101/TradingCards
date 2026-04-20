# Experiments

Scratch scripts, hypothesis tests, and one-off investigations. These are NOT production code -- they're the lab notebooks of the project. Kept for reference and reproducibility.

**Do not import from these files.** They may have hardcoded paths, missing deps, or stale logic.

## Categories

### accuracy/
Pipeline accuracy experiments: false positive analysis, filter tuning, hypothesis testing (H1-H5), SCP matching validation. Key findings from these experiments drove the 87.7% accuracy overhaul in Session 85.

### volume/
Volume and coverage experiments: liquid card analysis, SCP volume scraping, player discovery, API budget optimization, growth projections. The liquid-first auction pipeline came from insights in these scripts.

### search/
Multi-platform search experiments: ddgs/primp TLS impersonation, eBay Browse alternatives, Google Shopping, DuckDuckGo. Research from Session 83 on replacing Browse API with free web search.

### validation/
Post-run validation scripts: morning checks, auction audits, SCP price verification, parallel skip analysis. Many of these evolved into the formal diagnostic scripts in `scripts/`.

### misc/
Everything else: one-off data pulls, URL generators, HTML link builders, dead pipeline variants that were superseded.

## When to create experiments

- Testing a hypothesis about pipeline behavior
- Exploring a new data source or API
- One-off data analysis that doesn't belong in the pipeline
- Prototyping a feature before building it properly

## When to promote to production

If an experiment proves valuable, extract the logic into the proper location:
- Pipeline logic -> `backend/services/`
- Scraper -> `backend/scrapers/`
- Diagnostic -> `scripts/diagnostics/`
- CLI tool -> `scripts/ops/`
