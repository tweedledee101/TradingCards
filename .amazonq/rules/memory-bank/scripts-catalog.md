# Trading Card Platform - Scripts Catalog

## Directory Structure

```
scripts/
├── diagnostics/     # Read-only status checks and funnel analysis
├── ops/             # Pipeline operations (verify, cleanup, shard)
└── dev/             # Dev tools, CE/vision, test scripts
```

## Diagnostics (scripts/diagnostics/) -- use BEFORE creating new files

| Script | Purpose | Usage |
|--------|---------|-------|
| `check_dev_status.py` | Quick DB snapshot: row counts, opportunity breakdown by type, latest opp timestamp for PROD + DEV | `/usr/bin/python3 scripts/diagnostics/check_dev_status.py` |
| `check_recent_jobs.py` | Last 8 `job_runs` rows (name, status, started, items) for PROD + DEV | `/usr/bin/python3 scripts/diagnostics/check_recent_jobs.py` |
| `check_job_details.py` | Last 4 `job_runs` with parsed `parameters` + `results_summary` for PROD + DEV | `/usr/bin/python3 scripts/diagnostics/check_job_details.py` |
| `audit_auction_pipeline.py` | Full auction funnel: active/ended rows, job_runs funnel counters (step2/step3 breakdown), error_log | `/usr/bin/python3 scripts/diagnostics/audit_auction_pipeline.py [--compare]` |
| `diagnose_auction_query_efficiency.py` | Rank auction Browse queries by new unique listings per API call from `step1_query_stats` | `/usr/bin/python3 scripts/diagnostics/diagnose_auction_query_efficiency.py [--job-id N]` |
| `diagnose_bin_ebay_variation_stats.py` | BIN per-variation eBay stats: which queries pull inventory vs dead ends | `/usr/bin/python3 scripts/diagnostics/diagnose_bin_ebay_variation_stats.py [--job-id N]` |
| `inspect_scp_cache.py` | Sample SCP cache entries, player counts, variant structure (targets DEV DB) | `/usr/bin/python3 scripts/diagnostics/inspect_scp_cache.py` |
| `liquid_funnel.py` | Check how many liquid SCP variants were actually searched on eBay | `/usr/bin/python3 scripts/diagnostics/liquid_funnel.py` |
| `summarize_github_actions.py` | Recent GitHub Actions conclusions + failed steps (uses `gh auth token`) | `/usr/bin/python3 scripts/diagnostics/summarize_github_actions.py [--limit 20]` |
| `preflight_auction.py` | Pre-flight check: DB, SCP cache, eBay API, CE import, MLB API | `/usr/bin/python3 scripts/diagnostics/preflight_auction.py` |
| `funnel_analysis.sql` | Raw SQL funnel queries for manual psql investigation | `sudo -u postgres psql -d trading_cards -f scripts/diagnostics/funnel_analysis.sql` |

## Pipeline Operations (scripts/ops/)

| Script | Purpose | Usage |
|--------|---------|-------|
| `audit_pipeline_skips.py` | Sample false junk/skip patterns from pipeline listing skips | `/usr/bin/python3 scripts/ops/audit_pipeline_skips.py --limit 200` |
| `cleanup_stale_auction_opportunities.py` | Remove ended auction rows from opportunities table | `/usr/bin/python3 scripts/ops/cleanup_stale_auction_opportunities.py [--dry-run]` |
| `verify_bin_opportunities.py` | Post-ingest BIN verification (130point vs SCP) | `/usr/bin/python3 scripts/ops/verify_bin_opportunities.py --limit 300 --only-pending` |
| `verify_opportunities_ce.py` | Verify top opportunities via Collectors Edge API | `/usr/bin/python3 scripts/ops/verify_opportunities_ce.py --limit 50` |
| `write_bin_player_shards.py` | Split player list into N shard files for parallel BIN CI | `/usr/bin/python3 scripts/ops/write_bin_player_shards.py --shards 8 --out-dir bin_shards/` |
| `query_scp_cache_players.py` | List players with SCP cache entries (for pipeline player selection) | `/usr/bin/python3 scripts/ops/query_scp_cache_players.py` |

## Dev Tools (scripts/dev/)

| Script | Purpose | Usage |
|--------|---------|-------|
| `run_find_opportunities_dev.py` | Run BIN pipeline against DEV database | `/usr/bin/python3 scripts/dev/run_find_opportunities_dev.py --top-players 20` |
| `compare_dev_prod_api.py` | Diff JSON responses between prod and dev API | `/usr/bin/python3 scripts/dev/compare_dev_prod_api.py` |
| `copy_scp_cache_to_dev.py` | Copy SCP cache from prod to dev DB | `/usr/bin/python3 scripts/dev/copy_scp_cache_to_dev.py` |
| `copy_prod_reference_to_dev.py` | Copy reference data from prod to dev | `/usr/bin/python3 scripts/dev/copy_prod_reference_to_dev.py` |
| `clear_dev_opportunities.py` | Wipe dev opportunities for clean re-run | `/usr/bin/python3 scripts/dev/clear_dev_opportunities.py` |
| `psql_dev.py` | Run psql against dev DB URL | `/usr/bin/python3 scripts/dev/psql_dev.py -c '\d cards'` |
| `ebay_browse_ping.py` | Check eBay Browse API quota + connectivity | `/usr/bin/python3 scripts/dev/ebay_browse_ping.py` |
| `vision_retry_scp_from_images.py` | Nova multimodal + SCP DB match for pipeline misses | `/usr/bin/python3 scripts/dev/vision_retry_scp_from_images.py --latest-auction-job --limit 5` |
| `scp_lookup_from_ce_json.py` | Map CE artifact JSON to SCP catalog match | `/usr/bin/python3 scripts/dev/scp_lookup_from_ce_json.py --latest-ce-artifact` |
| `collectors_edge_photo_run.py` | Playwright CE photo flow (upload image, get valuation) | `python scripts/dev/collectors_edge_photo_run.py --from-db` |
| `collectors_edge_explore.py` | Cohort-based CE sampling across opportunity types | `python scripts/dev/collectors_edge_explore.py --list-cohorts` |

## Important Notes

- **Python interpreter**: Use `/usr/bin/python3` (system Python 3.8.10 with all deps). The default `python3` in login shell may resolve to linuxbrew's Python which lacks `psycopg2`.
- **Environment**: Scripts load `backend/.env` themselves (most via dotenv or manual parsing). No need to `source` first.
- **Database target**: Most diagnostic scripts hit PROD (`DATABASE_URL`) by default. Some also check DEV.
- **Experiments**: Scratch scripts and one-off investigations live in `experiments/` (not tracked in CI). See `experiments/README.md`.
