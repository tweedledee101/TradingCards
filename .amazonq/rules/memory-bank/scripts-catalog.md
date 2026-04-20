# Trading Card Platform - Scripts Catalog

## Diagnostic / Status Scripts (use these BEFORE creating new files)

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/check_dev_status.py` | Quick DB snapshot: row counts, opportunity breakdown by type, latest opp timestamp for PROD + DEV | `/usr/bin/python3 scripts/check_dev_status.py` |
| `scripts/check_recent_jobs.py` | Last 8 `job_runs` rows (name, status, started, items) for PROD + DEV | `/usr/bin/python3 scripts/check_recent_jobs.py` |
| `scripts/check_job_details.py` | Last 4 `job_runs` with parsed `parameters` + `results_summary` for PROD + DEV | `/usr/bin/python3 scripts/check_job_details.py` |
| `scripts/audit_auction_pipeline.py` | Full auction funnel: active/ended rows, job_runs funnel counters (step2/step3 breakdown), error_log | `/usr/bin/python3 scripts/audit_auction_pipeline.py [--compare]` |
| `scripts/diagnose_auction_query_efficiency.py` | Rank auction Browse queries by new unique listings per API call from `step1_query_stats` | `/usr/bin/python3 scripts/diagnose_auction_query_efficiency.py [--job-id N]` |
| `scripts/diagnose_bin_ebay_variation_stats.py` | BIN per-variation eBay stats: which queries pull inventory vs dead ends | `/usr/bin/python3 scripts/diagnose_bin_ebay_variation_stats.py [--job-id N]` |
| `scripts/inspect_scp_cache.py` | Sample SCP cache entries, player counts, variant structure (targets DEV DB) | `/usr/bin/python3 scripts/inspect_scp_cache.py` |
| `scripts/liquid_funnel.py` | Check how many liquid SCP variants were actually searched on eBay | `/usr/bin/python3 scripts/liquid_funnel.py` |
| `scripts/summarize_github_actions.py` | Recent GitHub Actions conclusions + failed steps (uses `gh auth token`) | `/usr/bin/python3 scripts/summarize_github_actions.py [--limit 20] [--workflow pipeline.yml auction-pipeline.yml]` |
| `scripts/funnel_analysis.sql` | Raw SQL funnel queries for manual psql investigation | `sudo -u postgres psql -d trading_cards -f scripts/funnel_analysis.sql` |

## Pipeline Operations Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/audit_pipeline_skips.py` | Sample false junk/skip patterns from pipeline listing skips | `/usr/bin/python3 scripts/audit_pipeline_skips.py --limit 200` |
| `scripts/cleanup_stale_auction_opportunities.py` | Remove ended auction rows from opportunities table | `/usr/bin/python3 scripts/cleanup_stale_auction_opportunities.py [--dry-run]` |
| `scripts/verify_bin_opportunities.py` | Post-ingest BIN verification (130point vs SCP) | `/usr/bin/python3 scripts/verify_bin_opportunities.py --limit 300 --only-pending` |
| `scripts/verify_opportunities_ce.py` | Verify top opportunities via Collectors Edge API | `/usr/bin/python3 scripts/verify_opportunities_ce.py --limit 50` |
| `scripts/write_bin_player_shards.py` | Split player list into N shard files for parallel BIN CI | `/usr/bin/python3 scripts/write_bin_player_shards.py --shards 8 --out-dir bin_shards/` |
| `scripts/query_scp_cache_players.py` | List players with SCP cache entries (for pipeline player selection) | `/usr/bin/python3 scripts/query_scp_cache_players.py` |

## Dev / Comparison Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/run_find_opportunities_dev.py` | Run BIN pipeline against DEV database | `/usr/bin/python3 scripts/run_find_opportunities_dev.py --top-players 20` |
| `scripts/compare_dev_prod_api.py` | Diff JSON responses between prod and dev API | `/usr/bin/python3 scripts/compare_dev_prod_api.py` |
| `scripts/copy_scp_cache_to_dev.py` | Copy SCP cache from prod to dev DB | `/usr/bin/python3 scripts/copy_scp_cache_to_dev.py` |
| `scripts/copy_prod_reference_to_dev.py` | Copy reference data from prod to dev | `/usr/bin/python3 scripts/copy_prod_reference_to_dev.py` |
| `scripts/clear_dev_opportunities.py` | Wipe dev opportunities for clean re-run | `/usr/bin/python3 scripts/clear_dev_opportunities.py` |
| `scripts/psql_dev.py` | Run psql against dev DB URL (derived from DATABASE_URL) | `/usr/bin/python3 scripts/psql_dev.py -c '\d cards'` |
| `scripts/start_dev_api.sh` | Start dev API server | `bash scripts/start_dev_api.sh` |
| `scripts/test_prod_api.sh` | Quick prod API smoke test | `bash scripts/test_prod_api.sh` |
| `scripts/test_sales_ranking_dev.py` | Test sales-based player ranking on dev | `/usr/bin/python3 scripts/test_sales_ranking_dev.py` |

## Vision / CE Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/vision_retry_scp_from_images.py` | Nova multimodal + SCP DB match for pipeline misses | `/usr/bin/python3 scripts/vision_retry_scp_from_images.py --latest-auction-job --limit 5` |
| `scripts/scp_lookup_from_ce_json.py` | Map CE artifact JSON to SCP catalog match | `/usr/bin/python3 scripts/scp_lookup_from_ce_json.py --latest-ce-artifact` |
| `scripts/ce_verify_skips.py` | CE verification on pipeline skip samples | `/usr/bin/python3 scripts/ce_verify_skips.py` |
| `scripts/dev/collectors_edge_photo_run.py` | Playwright CE photo flow (upload image, get valuation) | `python scripts/dev/collectors_edge_photo_run.py --from-db` |
| `scripts/dev/collectors_edge_explore.py` | Cohort-based CE sampling across opportunity types | `python scripts/dev/collectors_edge_explore.py --list-cohorts` |
| `scripts/dev/print_opportunity_image_urls.py` | Print image URLs from DB opportunities for probes | `python scripts/dev/print_opportunity_image_urls.py --limit 5` |
| `scripts/dev/ebay_browse_ping.py` | Check eBay Browse API quota + connectivity | `/usr/bin/python3 scripts/dev/ebay_browse_ping.py` |

## Dev Test Scripts (scripts/dev/)

| Script | Purpose |
|--------|---------|
| `test_130point_live.py` | Live 130point scraper test |
| `test_api.py` | API endpoint smoke tests |
| `test_budget_opportunities.py` | Budget filter logic tests |
| `test_discovery.py` | Player discovery tests |
| `test_ebay_connection.py` | eBay API connectivity test |
| `test_ebay_fields.py` | eBay response field inspection |
| `test_find_listing.py` | Single listing lookup test |
| `test_opportunities.py` | Opportunity logic tests |
| `test_scp_matching.py` | SCP matching logic tests |
| `test_scp_page.py` / `test_scp_page2.py` | SCP scraper page tests |
| `test_scp_url.py` | SCP URL construction tests |
| `test_set_extract.py` / `test_set_extraction.py` | Set name extraction tests |
| `test_variant_system.py` | Variant parsing tests |

## Important Notes

- **Python interpreter**: Use `/usr/bin/python3` (system Python 3.8.10 with all deps). The default `python3` in login shell may resolve to linuxbrew's Python which lacks `psycopg2`.
- **Environment**: Scripts load `backend/.env` themselves (most via dotenv or manual parsing). No need to `source` first for most scripts.
- **Database target**: Most diagnostic scripts hit PROD (`DATABASE_URL`) by default. Some also check DEV. `inspect_scp_cache.py` targets DEV specifically.
