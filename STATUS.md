# Trading Card Platform - Current Status
**Last Updated:** 2026-04-14

## HONEST SYSTEM STATE

**Target:** ~1,000 accurate opportunities (BIN + Auction). **Current:** 60 CE-verified opportunities out of 150 total. **40% accuracy rate -- CE verification now filtering out wrong matches.**

### What's Running (Prod / RDS)
- Auction pipeline: 2x/day via GitHub Actions, finding 15-32 opps/run
- BIN pipeline: FIXED -- uses SCP cache (no Selenium), 60 hardcoded players, 500 variations/shard. Awaiting first run.
- CE verification: all 150 existing opportunities verified. 60 confirmed, 90 rejected (66 price divergence, 23 year mismatch, 1 player mismatch)
- CE verification in CI: runs automatically after BIN + auction pipelines
- API: hides CE-rejected opportunities by default (`hide_ce_rejected=true`)
- SCP cache: 12,806 entries (1,352 unique players, 43K+ variants)
- sold_comps: 446+ rows (worm seeding from opportunities)
- Frontend: ragnarokgamez.com (Cognito auth, Opportunities + Business Dashboard)
- API: api.ragnarokgamez.com (FastAPI Lambda)
- Tests: 221 pass, 2 fail (auth), 11 errors (web search tests need Python 3.12)

### What's Broken (Prod / RDS)
- **BIN pipeline hasn't run with new config yet** -- pushed today, awaiting manual trigger or 2PM ET cron
- **Card data pipeline never ran on RDS** -- `cards`=1, `sales`=0, `active_listings`=0. Trending page empty.
- **market_rates: 0 rows** -- pipeline uses scp_cache only
- **147,060 error_log entries**
- **inventory, scheduled_bids: empty**

### CE Verification Results (April 14, 2026 -- all 150 opportunities)
| Status | Count | Avg Profit | Meaning |
|--------|-------|-----------|----------|
| ce_confirmed | 60 | $22.86 | Real opportunities -- card identity matches |
| ce_price_divergence | 66 | $62.36 | Wrong SCP match -- fake profit |
| ce_year_mismatch | 23 | $21.88 | Wrong year -- different card |
| ce_player_mismatch | 1 | $22.85 | Wrong player entirely |

Key insight: the highest-"profit" opportunities were the most wrong. Top 20 by profit had 95% false positive rate. Lower-profit opportunities had ~50% accuracy. CE catches exactly the wrong matches the pipeline was surfacing.

### RDS Table Counts (April 14, 2026)
| Table | Rows | Notes |
|-------|------|-------|
| cards | 1 | Card data pipeline never ran on RDS |
| sales | 0 | Same |
| active_listings | 0 | Same |
| market_rates | 0 | Pipeline uses scp_cache instead |
| scp_cache | 12,806 | 1,352 players, 43K+ variants |
| sold_comps | 446+ | Worm seeding from opportunities |
| opportunities | 150 | 60 CE-confirmed, 90 CE-rejected, BIN stale (April 6) |
| pipeline_listing_skips | 41,544 | 33,110 economics + 3,243 reprint + more |
| job_runs | 123+ | Auction completing; BIN awaiting first new run |
| error_log | 147,060 | Mostly eBay Browse HTTP errors |
| schema_migrations | 30 | All applied |

### The Core Problem
Three compounding issues preventing 1,000 accurate opportunities:
1. **Coverage too narrow**: 40 players, ~1,665 SCP variations. eBay has 1.1M+ Topps Chrome listings alone.
2. **Identity matching wrong too often**: text-only matching (title -> SCP) misidentifies cards. Grade mismatch, parallel mismatch, wrong player. 33,110 economics rejects -- many are wrong matches, not genuinely unprofitable.
3. **No visual verification in pipeline**: Collectors Edge API can identify cards from images (30s, structured JSON, no browser). Proven but not integrated into pipeline yet.

### Session 85 continued (April 14): CE Verification Complete + CI Integration
- **All 150 opportunities CE-verified**: 60 confirmed (40%), 66 price divergence, 23 year mismatch, 1 player mismatch
- **Key finding**: top 20 by profit had 95% false positive rate. Highest-"profit" opportunities were the most wrong (avg $62 fake profit on price divergence vs $23 real profit on confirmed).
- **CE verification added to CI**: `verify-ce` job runs after BIN + auction, verifies top 50 unverified by profit
- **API filter**: `hide_ce_rejected=true` default on `/opportunities` and `/auctions` -- UI only shows confirmed or pending
- **60 players in BIN pipeline** (up from 40): all with 25+ SCP cache entries
- **All 3 commits pushed to GitHub**: BIN fix, 60 players + CE script, CE in CI + API filter
- **Changed files**: `.github/workflows/pipeline.yml`, `backend/api/routes/opportunities.py`, `scripts/verify_opportunities_ce.py`, `scripts/query_scp_cache_players.py`

### Session 85 (April 13): BIN Pipeline Fix + SCP Cache Mode + sold_comps Seeding
- **Root cause of BIN failure**: eBay Browse API returning HTTP 429 on ALL 45 seed discovery calls. Analytics showed 5,000/5,000 remaining (daily quota fine) -- it's burst rate limiting, not quota exhaustion. Every seed got 429'd, discovery returned 0 players, pipeline exited.
- **Fix 1: Hardcoded player list in workflow** -- `bin-plan` job now passes 40 known Baseball players directly to `write_bin_player_shards.py --players`. Zero Browse API calls for discovery. Eliminates the 429 failure mode entirely.
- **Fix 2: BIN shards use `--use-scp-cache`** -- reads from 12,806 cached SCP entries (1,352 players, 43K+ variants) instead of Selenium. Removed Firefox/geckodriver install from BIN shard jobs. Faster CI, more reliable, same data.
- **Fix 3: `--max-ebay-variations 500` per shard** -- SCP cache returns thousands of variants per player. Without a cap, 8 shards would blow through 5,000 Browse API calls/day. 500/shard = 4,000 total, leaves room for auction pipeline.
- **Fix 4: Worm `--opportunities` SQL error** -- `ORDER BY scp_price` wasn't in `SELECT DISTINCT` list. Added `scp_price` to select. Worm now populates sold_comps from 146 existing opportunities.
- **sold_comps seeding**: 446 comps stored from first batch before 130point rate limit. Worm will continue on retry.
- **Changed files**: `.github/workflows/pipeline.yml` (BIN discovery + SCP cache + variation cap), `worm_130point.py` (SQL fix)

### Session 84 (April 13): CE API Direct + Funnel Analysis
- **CE tRPC API discovered**: `POST collectorsedgeai.com/api/trpc/cards.identifyByImage` -- base64 image in, structured JSON out (player, year, set, variant, printRun, pricing with methodology). 30s per card, no Playwright.
- **Integrated into existing tooling**: `collectors_edge_photo_run.py` tries API first, Playwright fallback. `--no-api` flag to force browser. Works with `--from-db`, `--merge-qa-to-db`, explore cohorts.
- **Full-size images fix**: `opportunity_image_urls.py` now sorts s-l1600.jpg first (was using 225px thumbnails -- CE accuracy much better with full-size).
- **Batch tested 25 cards via CE API**: 100% success rate (vs 40% with Playwright). Found pricing gaps (Cowser Auto /99: SCP $40, CE $175), wrong player matches (Chourio listing identified as Rowdy Tellez), grade mismatches.
- **Funnel analysis**: 79.7% of pipeline skips are economics. 14,500 skips where buy > 3x SCP (strong wrong-match signal). 31,141 skips on cards with SCP < $20 (wasted effort).
- **Web search (ddgs/primp)**: Works but doesn't beat Browse API volume. Not the path forward.
- **New files**: `scripts/ce_verify_skips.py`, `backend/services/web_search_discovery.py`, `tests/unit/test_web_search_discovery.py`
- **Changed files**: `backend/utils/collectors_edge_result.py` (API functions), `backend/utils/opportunity_image_urls.py` (full-size sort), `scripts/dev/collectors_edge_photo_run.py` (API-first flow)

---

## SESSION HISTORY (oldest at bottom)

Session 83: **Multi-platform listing discovery research** -- ddgs/primp tested, Browse API still better for volume. Python 3.12 confirmed at `/usr/local/bin/python3.12`.

Session 82: **`scripts/psql_dev.py`** — **`psql`** against dev URL when **`DATABASE_URL_DEV`** is unset (derived like **`migrate.py --dev`**). **`.amazonq/rules/database-access.md`**, **`PIPELINE-OPS`**.

Session 81: **`migration_028_cards_ungraded_price.sql`** — fixes missing **`cards.ungraded_price`** when **`migration_add_parallel.sql`** was recorded after constraint conflict with **`migration_003`**. **`migration_add_parallel.sql`** trimmed to column adds only.

Session 80: **`migrate.py`** applies **`backend/models/schema.sql`** when **`public.cards`** is missing, then **`migration_*.sql`** (fixes fresh **`trading_cards_dev`** failing on **`migration_001`**). Doc touch **`create_trading_cards_dev_database.md`**, **`migrate.py`** header.

Session 79: **`migrate.py --dev`** auto-**CREATE DATABASE** **`trading_cards_dev`** (same instance as **`DATABASE_URL`**) via **`backend/utils/dev_postgres.py`**; dev URL derived when **`DATABASE_URL_DEV`** unset; **`--no-create-dev-db`**. **`run_find_opportunities_dev`**, **`deploy_api_cf.py`**, **`deploy-api-lambda-dev.sh`** accept derive. Tests **`tests/unit/test_dev_postgres.py`**. Docs: **`PIPELINE-OPS`**, **`create_trading_cards_dev_database.md`**, dev architecture.

Session 78: **Dev API stack + run/compare tooling** — **`api-lambda-http-dev.yaml`**, **`deploy-api-lambda-dev.sh`**, **`deploy_api_cf.py`** (`--template`, **`--database-env-key DATABASE_URL_DEV`**). **`scripts/run_find_opportunities_dev.py`**, **`scripts/compare_dev_prod_api.py`**. **`GET /health`** + Lambda fast path: **`postgres_db_name`**. **`aws/scripts/create_trading_cards_dev_database.md`**. **`PIPELINE-OPS`**, **`aws/README.md`**, dev architecture doc.

Session 77: **dev.ragnarokgamez.com UI stack** — **`aws/cloudformation/frontend-spa-dev.yaml`**, **`aws/deploy-frontend-dev.sh`**, **`frontend`**: **`npm run build:dev`**, **`frontend/.env.dev`**. **`aws/README.md`** (dev UI checklist + Cognito). **`docs/architecture/dev-environment-and-pipeline-cutover.md`** §2.1.

Session 76: **Dev gaps — SCP/sold_comps reconcile + vision queue** — **`--dev-reconcile-scp-comps`**, **`scp_sold_comps_reconcile`**, **`sold_comp_summary_for_identity(..., parallel=...)`** (verify + reconcile + **`audit_pipeline_skips`**). **`--dev-vision-queue-pass`** / **`--dev-vision-queue-max`**. DB row **`price_source=reconciled`**, **`verification_detail`**. Tests **`test_scp_sold_comps_reconcile`**. **`PIPELINE-OPS`**, dev architecture doc.

Session 75: **Sales-count player ranking + dev strict listings** — **`--player-rank-source sales`** (``sales`` rows / player / ``--sales-rank-days``, default 7); **`fetch_hot_players_from_sales`** returns counts; default **`--top-players` 100** (local/shard writer; CI still passes 40). **`--dev-strict-listings`** + **`backend/services/dev_strict_listing.py`**. **`find_opportunities` / auction / shard script** wiring. Tests **`test_dev_strict_listing`**, **`test_discover_rank_source`** sales. **`PIPELINE-OPS`**, dev architecture doc.

Session 74: **Dev DB migrations + sold_comps player ranking** — **`migrate.py --dev`** / **`--all-db`** when **`DATABASE_URL_DEV`** is set; **`Config.DATABASE_URL_DEV`**. **`--player-rank-source sold_comps`** on **`find_opportunities.py`**, **`find_auction_opportunities.py`**, **`scripts/write_bin_player_shards.py`** (Browse-free discovery step; optional **`--no-sold-comps-fallback-browse`**). **`discover_players`**: **`fetch_hot_players_from_sold_comps`**, **`DISCOVER_SUMMARY`** **`rank_source`**. Tests **`tests/unit/test_discover_rank_source.py`**. **`PIPELINE-OPS`**, **`docs/architecture/dev-environment-and-pipeline-cutover.md`**.

Session 73: **Dev + pipeline cutover plan** — **[docs/architecture/dev-environment-and-pipeline-cutover.md](./docs/architecture/dev-environment-and-pipeline-cutover.md)** (`dev.ragnarokgamez.com` pattern, second DB on same RDS, phased Browse-light funnel, KPI bar vs current). **`docs/README.md`**, **`PIPELINE-OPS.md`** links.

Session 72: **Inventory ↔ eBay** — **`migration_027`**: **`inventory.ebay_item_id`**, **`ebay_listing_url`**, **`listing_ask_price`**, **`listed_at`**. API: **`POST /api/inventory`** + **`PATCH /api/inventory/{id}`**, bulk CSV columns, **`GET /api/inventory?status=active`**, stats count **owned+listed**, **`POST /api/inventory/sales`** returns **`days_held`**. **`PIPELINE-OPS`**, **`database-design`**. Run **`migrate.py`**.

Session 71: **Working capital rule in docs** — **[docs/OPPORTUNITY-FINDER.md](./docs/OPPORTUNITY-FINDER.md)** velocity bullet: ~2wk buy→sell + $1k capital; pipeline approximates via **`sold_comps`/`sales`** cadence until inventory flip timestamps exist.

Session 70: **Target architecture** — **[docs/OPPORTUNITY-FINDER.md](./docs/OPPORTUNITY-FINDER.md)** *Target evolution*: 130point/`sold_comps`-led player ranking (~100), velocity/sell-through, $5–$1k, CE+SCP before narrow eBay; success metrics table + gap vs current Browse-led discover. **[docs/ROADMAP.md](./docs/ROADMAP.md)** §2.0a pointer.

Session 69: **Operator map** — **[AGENTS.md](./AGENTS.md)** *Follow the money*: linear BIN path (discover → SCP → eBay → API → UI), auction caveat + “nothing buyable” = thresholds / verification / stale / pipeline shape, not API excuses.

Session 68: **Canonical opportunity intent** — **[docs/OPPORTUNITY-FINDER.md](./docs/OPPORTUNITY-FINDER.md)** *Canonical pipeline intent*: liquidity ranking → SCP $5–$1k universe → catalog-driven listing discovery → SCP + comps + CE validation; notes BIN vs auction alignment gap. **[docs/README.md](./docs/README.md)** index line updated.

**Trust / roadmap §2.0 (in progress):** **`migration_025`–`026`**: verification fields; **`opportunities.sport`** + **`pipeline_listing_skips`**; **sales-driven discovery** merges DB `sales` hot players with anchor seeds daily; **`--sport` / BIN Browse pagination ≤1000**; API + Opportunities UI **sport filter**; post-ingest **`scripts/verify_bin_opportunities.py`** (130point vs SCP) + **`scripts/audit_pipeline_skips.py`**. CE photo flow remains Playwright (`collectors_edge_photo_run`). See **[docs/testing/strategy.md](./docs/testing/strategy.md)**.

Session 67: **Discovery rate visibility** — Each Browse response during seed discovery can log **`DISCOVER_BROWSE_RATELIMIT`** (HTTP + **`X-EBAY-C-RATELIMIT-*`** + **`Retry-After`** when present); **`EBAY_DISCOVER_LOG_BROWSE_RATELIMIT=0`** to disable. **`PIPELINE-OPS`** + module docstring.

Session 66: **Auction pipeline vs RDS idle** — Long **eBay 429** sleeps left **`JobTracker`**’s single SQLAlchemy session idle; RDS closed the connection (**SSL SYSCALL EOF**), then **`tracker.update`** / **`fail`** crashed (**PendingRollbackError**). Fix: **`JobTracker`** uses a **fresh session per** `update` / `complete` / `fail` (and closes after **`start`**); **`fail`** is best-effort (logs if DB still down). **`database.create_engine`**: **`pool_pre_ping=True`**, **`pool_recycle=280`**.

Session 65: **Production API 500 on all FastAPI routes** — **`POST /inventory/bulk-import`** uses **`UploadFile`**; missing **`python-multipart`** caused **import-time RuntimeError** in Lambda, so **`/api/opportunities`** etc. never loaded (while **`/health`** still OK). Fix: **`python-multipart`** in **`backend/requirements.txt`** and **`backend/requirements-lambda.txt`** (Docker image); **redeploy** API Lambda (`./aws/deploy-api-lambda.sh`).

Session 64: **Resilient BIN CI** — **`scripts/write_bin_player_shards.py`**; **`find_opportunities.py`** **`--bin-replace-scope`** **`all`** | **`shard_players`** (shard mode requires **`--players`**). **`.github/workflows/pipeline.yml`**: **`bin-plan`** + **8-way matrix** **`opportunity-bin`** (**75m**/shard, **`max-parallel: 4`**), **`--bin-replace-scope shard_players`**; artifacts per shard; **`PIPELINE-OPS`** (orphan BIN note, keep shard count in sync).

Session 63: **BIN reliability** — DB write is **one transaction** (delete old BIN + insert) so cancel mid-run no longer risks wiping BIN then dying; **`--max-ebay-variations`** + workflow **`ebay_variation_cap`**; **PIPELINE-OPS** cancel/eBay note.

Session 62: **Opportunities data + landing** — API **`/api/auctions`**: if no **live** rows, **ended_fallback** returns recent ended auctions (UI banner). Opportunities page: GitHub **Run workflow** links, BIN empty state, filter empty state. **Landing**: Norse-hall line *Enter the hall.* **SiteFooter**: compact middot row. **`PIPELINE-OPS.md`**: subsection *From scanner run → rows on the Opportunities page*.

Session 61: **UI polish** — minimal **Landing** (mobile-first, safe-area, no long copy); **SiteFooter** (Careers/Contact/Legal placeholders, ©); **Help** page with trust/verification docs; **Opportunities** drops banner for link to Help + empty-DB explainer; **TrustBadges** component.

Session 60: **Public landing vs trending** — **`/`** → **`Landing.jsx`** (public); trending **`Home`** at **`/market`**; nav **Market**; **`CardDetail`** back link → **`/market`**; auth still **`PrivateLayout`** except landing + callback. **`docs/ROADMAP.md`** M3.1 note.

Session 59: **Discovery QA + UI sport chips + auction parity** — **`get_hot_players`** / **`hot_player_names_for_pipeline`** only pass sales-merge kwargs when DB session or positive dynamic limit; **`tests/qa/test_player_discovery`** expects **`player_name`** dict rows. **Opportunities** list + **CardDetailModal** show **`sport`**. **`find_auction_opportunities`**: **`--dynamic-seed-*`**, **`--max-discovery-candidates`**, **`--no-dynamic-seeds`**; **`.github/workflows`**: **`pipeline.yml`** + **`auction-pipeline.yml`** pass **`dynamic_seed_days`** / **`max_discovery_candidates`**. **`PIPELINE-OPS.md`**: BIN Browse pagination note.

Session 58: **Resilient opportunity CI + BIN telemetry** — **`find_opportunities.py`**: `--skip-auction-chain`; **`ebay_variation_stats`** + aggregates on **`job_runs`** (`opportunity_finder`). **`.github/workflows/pipeline.yml`**: jobs **BIN** (90m) + **Auction** (120m, `if: always()`), artifacts per job; dispatch **`run_auction`**. **`scripts/diagnose_bin_ebay_variation_stats.py`**. **`PIPELINE-OPS.md`**, **`docs/testing/strategy.md`**, **`AGENTS.md`**.

Session 57: **Product surfaces** — **[ADR-007](./docs/architecture/decisions/ADR-007-public-surfaces-vs-admin-and-commerce.md)**: single **admin** ops plane (Opportunities, Business, tooling private) vs **public** landing + storefront + future **Stripe** checkout / **Plaid**-class bank flows, **breaks**, **livestreams**, **calendar** (customer access TBD). **ROADMAP** Milestone 3 backlog.

Session 56: **Git workflow + testing intent** — **[CONTRIBUTING.md](./CONTRIBUTING.md)** (feature branches, PRs for risky changes). **[docs/testing/strategy.md](./docs/testing/strategy.md)** (correctness vs funnel health vs outcome/trust); **`pytest` marker `outcome`**. **ROADMAP 2.0** — mandatory **eBay ↔ SCP ↔ CE** identity verification path for trusted opportunities. **ADR-003** supplement link.

Session 55: **Auction Browse — wider lens + diagnostics** — **`backend/config/auction_queries.py`**: product-line queries (e.g. `{year} Topps Chrome baseball`) × latest N years + existing parallel pack; **`--no-product-line-queries`**, **`--product-line-year-cap`**, **`--sold-comp-seed-queries`** / **`--sold-comp-seed-days`** via **`auction_sold_comp_seeds`** (130point **`sold_comps`**). **`search_auctions_ending_soon`**: optional **`meta_out`** with **`ebay_total`**. **`job_runs.results_summary`**: **`step1_query_stats`**, **`value_query_meta`**. **`scripts/diagnose_auction_query_efficiency.py`**; **`audit_auction_pipeline.py`** hints. Tests **`test_auction_queries_config`**, **`test_auction_sold_comp_seeds`**. **`PIPELINE-OPS.md`**.

Session 54: **Auction ↔ BIN player parity** — **`hot_player_names_for_pipeline`** in **`backend/discover_players.py`**; **`find_opportunities.get_hot_players`** and **`find_auction_opportunities`** use it (auction: **`--top-players`**, **`--days`**, **`--players`**; BIN: **`--days`**). Auction no longer ranks players by **`Card`** row counts unless discovery returns empty. **`PIPELINE-OPS.md`**: Step 3 counter identity (**qualified** vs **opportunities**), fee/profit/BIN-sanity explanation. Tests: **`test_hot_player_names_for_pipeline_wraps_discover`**.

Session 53: **eBay discovery filter** — Dropped **past-only** `itemEndDate` on Browse search. **Baseball** uses **`category_ids=261328`** as a **query param** (not `categoryId` inside `filter`, which was yielding **total=0**). **`EbayScraper`** sends **`X-EBAY-C-MARKETPLACE-ID`** / **`ENDUSERCTX`** for **US**. Discovery **fallback** retry without `buyingOptions` if first call returns 0. **`find_opportunities`**: **exit 1** if **0 players** (error text points at **`DISCOVER_SUMMARY`** + **`error_log`** categories). **`discover_players`**: **`BROWSE_APP_QUOTA`** from Analytics **`getRateLimits`** (skippable **`EBAY_SKIP_ANALYTICS_QUOTA`**); **`X-EBAY-C-RATELIMIT-*`** on Browse responses into **`DISCOVER_SUMMARY`**; **Browse 429** **decreasing** backoff (**`EBAY_DISCOVER_429_BACKOFF`**). **`scripts/dev/ebay_browse_ping.py`**: Analytics + Browse probe. **`PIPELINE-OPS.md`**. **`itemEndDate`** filters use UTC **`.000Z`** in **`ebay_scraper`**.

Session 52: **Ship-ready tree** — Stopped tracking **`frontend/node_modules`** (~6.6k files) and **`__pycache__`** / **`*.pyc`** (use **`.gitignore`** + **`npm ci`**). Staged feature work: migration **024** **`listing_image_urls`**, vision/SCP/Collectors Edge utilities + scripts, Opportunities API/UI, test hygiene (**234** pytest), **`nova-act-smoke`** workflow. **CI** frontend job runs **`npm ci`**; local **`npm run build`** verified.

Session 51: **pytest + missing `_sqlite3`** — **`pytest.ini`** disables **`pytest_cov` by default**; **`tests/qa/conftest.py`** uses **`pysqlite3-binary`** when stdlib **`sqlite3`** is broken (SQLAlchemy **`module=`**). **`backend/requirements.txt`** pins **`pysqlite3-binary`**. **`./run_tests.sh coverage`** still needs real **`_sqlite3`**. **`PIPELINE-OPS.md`** “Tests” bullet updated.

Session 50: **Test / RDS reachability** — Confirmed **141/141** `tests/unit` + `tests/integration` against **RDS** when `DATABASE_URL` is loaded and network is allowed; earlier failures were **sandbox/no-network**, not AWS down. **`tests/integration/conftest.py`** loads `DATABASE_URL` from **`backend/.env`** if unset; **`run_tests.sh`** `all`/`integration` sources **`.env`**. **`PIPELINE-OPS.md`** “Tests” section explains DNS/network vs infra.

Session 49: **CE → SCP + auction job UX** — **`scp_lookup_from_ce_json`**: MISS prints **catalog # sample** for player, **`scp_url`/`ebay_url`** from opportunity, **psql** one-liner; fixed misleading “for year …” when **no row for that # at any year**. **`catalog_card_number_hints_for_player`**. **`vision_scp_miss_hint`** / **`find_scp_match_for_vision`** year-relaxed. **`ce_scp_identity`**, **`PIPELINE-OPS.md`**, tests.

Session 48: **Vision SCP DB match** — **`find_scp_match_for_vision`**: `#` normalization, Base→**RC**-style parallel retry, multi-variant heuristic; **`vision_scp_miss_hint`** on **MISS**; **`vision_retry_scp_from_images.py`** prints **`db_match`** on HIT and **`job_run.id` + `results_summary` keys** when auction queue empty. Unit test **`test_scp_db_match_vision.py`**. **`PIPELINE-OPS.md`**, **`data-flow.md`**.

Session 47: **`vision_retry_scp_from_images.py` → DB** — On SCP **HIT**, **insert** **`opportunities`** by default (**`--no-persist`** off). Filters: **`--min-profit`** (10), **`--min-roi`**, **`--min-confidence`** (`medium`). **Duplicate** `ebay_item_id` skipped. **`fetch_vision_queue_from_opportunities`**: **`listing_type`**, **`shipping`**. **Auction** vision queue rows: **`buy_price`/`shipping`** on no-pricing + BIN-sanity samples. Tests **`test_vision_retry_persist.py`**. **`PIPELINE-OPS.md`**.

Session 46: **Auction Step 2 → vision sample** — **`find_auction_opportunities.py`**: bounded (**25/run per** `no_year` / `no_card_number` / `no_player`) **`step2_skip_vision_queue_sample`** + merged into **`vision_post_pipeline_queue_sample`** (first segment). Uses **Browse + already-merged GET /item** gallery only (**no** vision-only API round-trips). Helper **`_merge_auction_gallery_from_item_details`**. **`PIPELINE-OPS.md`**, **`vision_retry_scp_from_images.py`** docstring, unit test **`test_vision_queue_unified_includes_step2_and_step3_rows`**.

Session 45: **Auction `scp_cache` VARCHAR(255)** — Multi-player / bad parse titles could pass a huge `player_name` into **`SCPCache`** and fail **`StringDataRightTruncation`**. **`_get_scp_variants`** now skips cache read/write when **`player_name` > 255** or **`card_number` > 50** (still runs Selenium); early exit **`return [], False`** when no card #.

Session 44: **Vision retry without job_runs** — **`backend/utils/vision_queue_from_opportunities.py`**; **`scripts/vision_retry_scp_from_images.py`** **`--from-recent-opportunities N`** (+ optional **`--listing-type`**). Argparse: one of **`--latest-auction-job` | `--latest-bin-job` | `--from-recent-opportunities` | `--json`** required. Unit tests **`test_vision_queue_from_opportunities.py`**. **`PIPELINE-OPS.md`**, **`AGENTS.md`**, **`data-flow.md`**. **Mixed .venv** (e.g. **`lib/python3.12`** vs **Python 3.8** binary): **`vision_card_extract`** ImportError explains interpreter + recreate-venv steps; **`PIPELINE-OPS`** troubleshooting; **`requirements.txt`** note on **Python 3.9+** for **`openai` 2.x**.

Session 43: **Vision post-pipeline only** — Documented policy: multimodal/Nova does **not** gate **`find_opportunities.py`** / **`find_auction_opportunities.py`** ingest. **`vision_post_pipeline_queue_sample`** on **`job_runs.results_summary`**: BIN price-floor rejects + flagged suspicious BIN; auction no-pricing + BIN≪SCP sanity rejects. **`vision_retry_scp_from_images.py`**: **`--latest-bin-job`**, **`_vision_queue_from_summary`**, disagreement hint vs **`pipeline_card`**. **`docs/architecture/diagrams/data-flow.md`**, **`PIPELINE-OPS.md`**, **`docs/architecture/database-design.md`**, **`scripts/audit_auction_pipeline.py`**, **`docs/OPPORTUNITY-FINDER.md`** (staleness note). **`find_opportunities.py`**: **`from __future__ import annotations`**.

Session 42: **CE → DB QA** — **`backend/utils/collectors_edge_qa_merge.py`**: merge **`ce_pipeline_analysis.suggested_qa_flags`** into **`opportunities.qa_flags`** (same object shape as **`qa_opportunities.py`**); **`collectors_edge_photo_run.py`** **`--merge-qa-to-db`**. **`iter_cohort_plan`** dedupes ids across cohorts by default; **`collectors_edge_explore.py`** **`--allow-duplicate-ids-across-cohorts`**, **`--merge-qa-to-db`**. **`PIPELINE-OPS.md`**.

Session 41: **CE extract + cohorts** — **`collectors_edge_result`**: drop “Analyzed … year” from **`years_mentioned`**, add **`years_in_analysis_headline`**, **±1y** product vs listing fuzzy match; **card #** candidates filter UI noise (keep insert codes like **FA-NS**). **`scp_or_qa_gap`** cohort no longer matches all `pending` QA rows. **`PIPELINE-OPS.md`**.

Session 40: **CE exploration** — **`scripts/dev/collectors_edge_explore.py`**: DB **cohorts** (`weak_scp_url`, `scp_or_qa_gap`, `qa_attention`, …), dry-run vs **`--execute`**, cooldown between runs, **`ce_explore_*.json`** report. **`--opportunity-ids`** on **`collectors_edge_photo_run.py`**. **`backend/utils/collectors_edge_cohorts.py`**, **`iter_opportunity_rows_by_ids`**. **`PIPELINE-OPS.md`**, **`AGENTS.md`**.

Session 39: **Collectors Edge JSON** — **`backend/utils/collectors_edge_result.py`**: structured **`ce_extracted`** + **`ce_pipeline_analysis`** (matching/verification vs opportunity row, CE vs SCP band, QA flag hints); **`opportunity_image_meta`** includes player/year/#/parallel/`scp_price` for cross-checks. **`PIPELINE-OPS.md`**.

Session 38: **`collectors_edge_photo_run.py`** — treats **`/result`** as success (not only `/cards/`), writes **`collectors_edge_*.json`**, prints **`CE_RESULT_JSON`** block; **`--from-db`** / **`--db-skip`** / **`--db-listing-type`**. Shared **`backend/utils/opportunity_image_urls.py`**. **`PIPELINE-OPS.md`**, **`AGENTS.md`**.

Session 37: **`scripts/dev/print_opportunity_image_urls.py`** — DB image URLs for probes. **`collectors_edge_photo_run.py`**: clicks **Identify & Value** after upload, longer waits / **180s** default timeout. **`PIPELINE-OPS.md`**, **`AGENTS.md`**.

Session 36: **Collectors Edge AI photo probe** — **`scripts/dev/collectors_edge_photo_run.py`**: Playwright **Photo** flow, CTA heuristics, **screenshot + HTML** artifacts; **`scripts/dev/extra-requirements-collectors-edge.txt`**. **`PIPELINE-OPS.md`**, **`.gitignore`** (`_collectors_edge_artifacts/`).

Session 35: **Vision SCP retry (CDN path)** — **`scripts/vision_retry_scp_from_images.py`**: Nova multimodal + **`backend/services/vision_card_extract.py`** → **`scp_db_match.find_scp_match_in_db`**; **`results_summary`** parsed whether DB returns **str or dict**. Auction **`find_scp_match_in_db`** import moved to **`backend/services/scp_db_match.py`**. **`openai`** + **`pydantic>=2.10.6`** in **`backend/requirements.txt`** (nova-act–compatible). Nova Act dev scripts: **`screen_width`/`screen_height`** to avoid WSL **0-width screenshot** failures. **eBay Browse 429:** **`search_auctions_ending_soon`** retries with **`Retry-After`** backoff; **`find_auction_opportunities.py`** sleeps **1s** between queries. Docs **`PIPELINE-OPS.md`**, **`AGENTS.md`**, **`research-and-practice-notes.md`**.

Session 34: **Browse API gallery images** — `collect_browse_item_image_urls()` (`image` + `thumbnailImages` + `additionalImages`); auction/BIN listings carry `image_urls`; `get_full_item_details` merges more; **`opportunities.listing_image_urls`** (migration **024**); API **`listing_image_urls`**; auction **`results_summary.no_scp_vision_queue_sample`**. Docs: **`database-design.md`**, **`PIPELINE-OPS.md`**.

Session 33: **Nova Act visual probe** — **`nova_act_listing_visual_probe.py`**: `ensure_live_nova_act_ready()`, `run_listing_visual_assessment()`. **`nova_act_smoke_gym.py`**: headed gym demo (see browser). **`nova_act_listing_card_extract.py`**: multi-image eBay JSON extract for SCP retry. **Cases JSON** + runner. **CI:** **`.github/workflows/nova-act-smoke.yml`** (dispatch, gym headless). **`PIPELINE-OPS.md`**: Actions + Chromium notes. Backlog: **research-and-practice-notes** Nova Act second pass on SCP misses.

Session 32: **Research ↔ practice** — New **[docs/research-and-practice-notes.md](./docs/research-and-practice-notes.md)**: maps academic + practitioner ideas to **Ragnarok pipelines/tables**, explicit **hypotheses (H1–H5)**, gaps, and a small **experiment backlog** (grading alignment, velocity on cards, watchlist-driven worm, hold-time vs planner). Linked from [docs/README.md](./docs/README.md).

Session 31: **Opportunities UX** — Live Auctions list includes **flagged** auctions (sorted after high-confidence); **Needs Review** is **BIN-only**. Mobile auction row shows **Max bid (est.)** (SCP after fees − $10 − ship). **CardDetailModal**: backdrop `pointer-events` fix for **tab taps on mobile**, visible errors for failed player-stats fetch, price-history chart if **1+** days of data, copy when **sales** pipeline empty.

Session 30: **Opportunities context + inventory CSV** — **`GET /api/opportunities/context-strip`**: business dashboard slice (YTD, on-track, listed/total from planner) + catalog-matched **ActiveListing** pulse vs latest **MarketRate** (13% SCP fee). **`POST /api/inventory/bulk-import`**: UTF-8 CSV (purchase_date, purchase_price, card identity). Frontend: Opportunities strip + expandable table; Inventory file upload. Auction Actions **`SCP_PAGE_LOAD_TIMEOUT=90`**.

Session 29: **SCP Selenium** — **`SCP_PAGE_LOAD_TIMEOUT`** in `backend/.env` / `config.settings` (default **60**s, clamped 15–180); **`SportsCardsProScraper`** uses it for `set_page_load_timeout`. Documents noisy Firefox “Navigation timed out” during long auction Step 3 runs.

Session 28: **Auction pipeline pack** — **`backend/utils/listing_card_identity.py`**: card # from **Card No. / CN: / catalog / insert / ref** plus **`#`**. **`resolve_year_from_set_hint`** when player+# spans multiple years. **Step 3**: fixed fallback so **130point** recovery is not dropped; funnel adds **`step3_no_pricing_after_primary`** and **`step3_no_pricing_after_sold_comps`**. **Queries**: top **15** players get **`get_set_queries`** (`sets.py`). **`scripts/audit_auction_pipeline.py --compare`**; **`scripts/cleanup_stale_auction_opportunities.py`**.

Session 27: **Auction card identity** — `search_auctions_ending_soon` passes **`short_description`**. `get_full_item_details` fills **`card_number`** and **`card_year`** from item text when aspects omit them. **`find_auction_opportunities.py`**: **`extract_year`** reads Year aspect, then title, then short description (1980–next year); detail fetch runs when **year** is missing too; **`infer_year_if_unique_in_catalog`** sets year when player+# maps to exactly one **`cards.card_year`**. Card **`#`** disambiguation via **`pick_card_number_with_catalog`** (player+year+sport).

Session 26: **Auction funnel observability** — `find_auction_opportunities.py` writes **`step2_skip_reasons`**, **`step3_no_pricing`**, **`step3_bin_sanity`**, **`step3_low_volume`**, **`step3_below_min_profit`**, **`detail_lookups`**, and run **`parameters`** into `job_runs.results_summary`. New **`scripts/audit_auction_pipeline.py`** prints live auction row counts vs ended-stale, parses last auction_finder runs, and summarizes `error_log`. **`PIPELINE-OPS.md`**: audit commands + **hypothesis / experiment table** for improving auction volume without abandoning ROI/liquidity goals.

Session 25: **Production SPA deploy** — `npm run build`, `aws s3 sync` to `ragnarok-spa-635601810497-us-east-1`, CloudFront invalidation `E1I0LKGWO56GR5` (`/*`). **`aws/README.md`**: “Traffic: volume vs where from” (CloudWatch/Monitoring, optional Standard logging, third-party analytics).

Session 24: **Mobile list layout** — Trending (`Home.jsx`): stacked stats row with optional **Avg** label below `sm`; heat box label order preserved on desktop. Opportunities (`Opportunities.jsx`): auction/BIN rows use a **3-column metric strip** below `sm` (Bid–SCP–Profit / Buy–SCP–Profit) so numbers line up; header row is timer+image+chevron (auctions) or BIN+image+chevron; countdown column narrowed on small screens; expanded action rows **flex-wrap**.

Session 23: **Card Data Pipeline** — added **daily schedule** (`0 11 * * *` UTC) so **`sales`** refresh for Trending; scheduled runs **always `--skip-scp`** (dispatch unchanged unless SCP unchecked). Root cause of empty Trending was **no cron + zero prior runs**.

Session 22: **`scripts/summarize_github_actions.py`** — prints recent GitHub Actions conclusions and failed steps (uses `gh auth token` or `GITHUB_TOKEN`); documented in **`PIPELINE-OPS.md`**.

Session 21: **Trending empty vs Opportunities** — `/api/trending` reads **`sales`** with **`sale_date` in the last 30 days** and **avg price ≥ $5** (`trending.py`). Scheduled **Opportunity Pipeline** does not insert **`sales`**; only **`run_pipeline_full`** (GitHub **Card Data Pipeline**, manual) does. **`PIPELINE-OPS.md`** documents the split; **Home** empty-state copy updated.

Session 20: **`ragnarok-api-lambda` stack** redeployed with fixed **`AWS::Lambda::Permission` `SourceArn` … `/*/*`** (HTTP API). Redundant manual **`apigw-httpapi-correct-*`** statement removed; resource policy is **single CFN-managed** allow — future stack updates won’t resurrect REST-style `*/*/*/*`.

Session 19: **Production API** `api.ragnarokgamez.com` observed returning **HTTP 500** (API Gateway) on `/health` and app routes — documented under WHAT'S BROKEN; Opportunities page no longer swallows API errors (shows same class of failure as Trending). **`lambda_entry.handler`** now logs a **`lambda_diag":"handler_entry"`** line on every invocation (deploy via `./aws/deploy-api-lambda.sh`) to separate “no invoke” vs “handler ran”; **`aws/README.md`** has the full DNS → API Gateway → Lambda chain and CLI isolation steps.

Session 17: **Production UI live** at https://ragnarokgamez.com (and www) via CloudFormation stack `ragnarok-frontend-spa`: S3 + CloudFront + Route53 alias, ACM cert `8dda492b-...`. Production builds target API at `https://api.ragnarokgamez.com` (`frontend/.env.production`); host the FastAPI app there when ready. QA workflow supports manual **Run workflow** (`workflow_dispatch`). README QA badge links to Actions.

Session 18: **Cognito auth gate** — SPA shows **Sign in** until Hosted UI completes; PKCE + `/auth/callback`; axios sends `Authorization: Bearer`. **API** routes (except `/health`, webhooks, eBay compliance) require **JWT** via `require_auth`. CORS limited to localhost + ragnarokgamez.com (+ www). Cognito stack updated: callback URLs include `/auth/callback`. Backend needs `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID` in `backend/.env` (see `.env.example`).

## SYSTEM STATUS: BIN FIXED (SCP CACHE MODE), AUCTION RUNNING, IDENTITY ACCURACY POOR

See top of this file for honest current state. The summary below is from earlier sessions and **overstates what is working on RDS**. The numbers (25,434 cards, 42,313 sales) reflect the **local** database, not RDS production.

### Quick Start

```bash
cd /home/tweedledee101/TradingCards

# Run opportunity finder (SCP catalog -> eBay active listings)
python3 find_opportunities.py --max-budget 200 --min-profit 10 --min-roi 20 --top-players 40

# Or specify players
python3 find_opportunities.py --max-budget 200 --min-profit 10 --players "Bobby Witt Jr,Mike Trout"

# Start services
nohup /usr/bin/python3 -m backend.api.run > /tmp/api.log 2>&1 &
cd frontend && nohup npm run dev > /tmp/frontend.log 2>&1 &

# Database migrations (keeps local + RDS in sync)
python3 migrate.py --both       # apply pending to both
python3 migrate.py --status --both  # check what's applied
```

---

## WHAT WORKS

### SCP-to-eBay Opportunity Pipeline
File: `find_opportunities.py`

Flow:
1. SCP player search returns full catalog (100 variations per player, 1 Selenium call)
2. Filter to variations within budget ($20-$1000 default)
3. Volume filter: skip cards with "rare", "1 sale per year", "2 sales per year" (dead money)
4. Build precise eBay search queries from SCP data (set name, card number, parallel, print run)
5. Search eBay active listings for each variation (BIN and auctions)
6. Strict title validation: player name + year + card number + variation keyword required
7. Junk filter: excludes "You Pick", "Complete Your Set", "Digital", "Bunt", lots, repacks
8. Factory set filter: excludes "Complete Set", "Montgomery Club", "Walmart Exclusive", "Target Exclusive" (unless SCP card itself is a factory set variant)
9. Reprint filter: excludes "Replica", "Project 2020", "Shoebox Treasures", "Sticker", "ACEO"
10. Wrong set detection: rejects listings containing known set names not in the SCP variation
11. BIN price floor: listings below 30% of SCP are hard-rejected (different product)
12. BIN suspicious flagging: listings between 30-50% of SCP pass but flagged for review
13. Auctions: included with no price floor or flagging (low current bids are normal)
14. Profit calculation: SCP price - buy price - 13% eBay fees
15. Results stored in `opportunities` table with listing_type (buy_it_now or auction)
16. Results served via API with listing_type filter support

### Pipeline Filters (in order)
```
SCP Catalog (100 variations/player)
  -> SCP price range ($20-$1000)
  -> Volume filter (reject "rare", "1 sale/year", "2 sales/year")
  -> eBay search (BIN + Auctions)
  -> Title validation (player + year + card# + parallel)
  -> Junk filter (you pick, mystery, repack, etc.)
  -> Factory set filter (complete set, montgomery, walmart/target exclusive)
  -> Reprint filter (replica, project 2020, shoebox treasures)
  -> Wrong set detection (gold label, gallery, etc. in wrong context)
  -> BIN price floor (< 30% of SCP = different product)
  -> Profit/ROI threshold
  -> BIN suspicious flagging (30-50% of SCP)
  -> Store in DB with listing_type tag
```

### Observability
- Structured logging (`backend/utils/logger.py`) -- WARN+ persists to `error_log` table
- FastAPI request middleware with timing and request_id tracking
- API endpoints: `/api/errors`, `/api/errors/summary`
- Job tracking: `job_runs` table, `/api/status` endpoint
- Data retention: self-managing via `run_retention_cleanup()` PostgreSQL function

### Database State (LOCAL -- not RDS; see top of file for RDS)
- 25,434 cards (40 players) -- LOCAL ONLY
- 42,313 sales -- LOCAL ONLY
- 44,165 active listings -- LOCAL ONLY
- 4,400 market rates -- LOCAL ONLY
- RDS has: cards=1, sales=0, active_listings=0, market_rates=0
- Primary DB: RDS (`cardpulse-db.ckvp9bhavaww.us-east-1.rds.amazonaws.com`)
- 30 migrations applied on RDS

### Auction-First Pipeline (Rewritten -- March 22)
File: `find_auction_opportunities.py`

Flips the standard pipeline: eBay auctions first, SCP validation second.
1. Search eBay for auctions ending within 48h using value-focused + player-specific queries (110 queries with pagination)
2. Category filter: eBay category 261328 (Trading Card Singles)
3. Quality filter: card number + player (period-normalized, accent-stripped, eBay aspects fallback) + not junk + within budget
4. SCP validation: DB lookup first, SCP cache (24h TTL), Selenium fallback
5. Multi-pass SCP matching: Pass 1 exact, Pass 2A strict text, Pass 2B fuzzy word-overlap, Pass 3 signals
6. BIN sanity check: hybrid listing BIN < 50% of SCP = reject
7. Profit check: SCP * 0.87 - (current bid + shipping) >= $10
8. Store in opportunities table with listing_type='auction'
9. Diagnostic logging on no_scp cards (first 30)

Latest run: 522 unique auctions found, 198 qualified after quality filter.

### Infrastructure Ready
- GitHub Actions workflows: BIN pipeline + Auction pipeline + Daily Report (workflow_dispatch + cron scheduled)
  - BIN pipeline: 2AM/2PM ET (`0 6,18 * * *` UTC)
  - Auction pipeline: 5AM/5PM ET (`0 9,21 * * *` UTC)
  - Daily report: 7PM ET (`0 23 * * *` UTC)
  - QA pipeline: on push/PR (CI)
- Firefox install: Mozilla PPA (`ppa:mozillateam/ppa`) for Ubuntu 24.04 runners
- Geckodriver: pinned v0.36.0 (avoids GitHub API rate limiting on latest-release lookup)
- RDS CloudFormation template (`aws/cloudformation/rds.yaml`) -- PostgreSQL free tier with self-contained VPC
- RDS deployed and running: `cardpulse-db.ckvp9bhavaww.us-east-1.rds.amazonaws.com:5432` (legacy name, domain is ragnarokgamez.com)
- 23 migrations tracked via `schema_migrations` table (both local + RDS)
- Migration runner: `python3 migrate.py --both` (applies pending, skips already-applied)
- Legacy migration scripts: `aws/apply-rds-migrations.sh`, `aws/migrate-to-rds.sh`
- Code pushed to GitHub (`tweedledee101/TradingCards`, main branch)
- GitHub secrets configured: `DATABASE_URL`, `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`
- Firefox binary auto-detection for local vs GitHub Actions environments
- 167 tests passing in CI (63 unit + 11 integration + 70 QA + frontend build)
- Daily operations report: pipeline health, DB health, data freshness, data quality, QA flags, trends, action items

### Other Working Systems
- Volume-based player discovery (45 seed players, ranked by eBay volume)
- Master pipeline (`run_pipeline_full.py`) -- all 5 steps
- Set-specific eBay searches (7 queries/player)
- Precise parallel extraction (80+ patterns)
- Insert set detection (20+ insert names)
- eBay API (production, auto-refreshing OAuth, 5,000 calls/day)
- SCP scraper (Firefox/Selenium) -- search and direct product page scraping
- Card images from eBay thumbnails
- PostgreSQL database with variant-aware schema (migrations 001-010)
- FastAPI REST API with 18+ endpoints
- React frontend with Ragnarok Gaming dark theme
- Opportunities page: scan timestamp, SCP verify link, 3 price tiers, eBay images, "Needs Review" section

### Players (40 total)
Ken Griffey Jr, Shohei Ohtani, Nolan Ryan, Mike Trout, Cal Ripken Jr,
Aaron Judge, Derek Jeter, Ronald Acuna Jr, Juan Soto, Bryce Harper,
Fernando Tatis Jr, Mookie Betts, Julio Rodriguez, Bobby Witt Jr,
Freddie Freeman, Elly De La Cruz, Ichiro Suzuki, Paul Skenes,
Adley Rutschman, Corbin Carroll, James Wood, Corey Seager,
Jackson Chourio, Jasson Dominguez, Gunnar Henderson, Jackson Holliday,
Trea Turner, Dylan Crews, Jackson Merrill, Roki Sasaki,
Yoshinobu Yamamoto, Junior Caminero, Marcelo Mayer, Wyatt Langford,
Evan Carter, Colton Cowser, Jordan Walker, Masyn Winn,
Spencer Strider, Jac Caglianone

---

## WHAT'S BROKEN -- HONEST ASSESSMENT

### Production API host (verified 2026-03-27; root cause fixed in template 2026-03-27)
`https://api.ragnarokgamez.com` returned **HTTP 500** with `{"message":"Internal Server Error"}` while **direct `lambda invoke` returned 200** and **CloudWatch had no invocation logs** — caused by **`AWS::Lambda::Permission` using REST-style `SourceArn` `*/*/*/*`**; **HTTP API** sends `...:api-id/$default/$default`, so **ArnLike failed** and API Gateway could not invoke Lambda. **Fix in repo:** `api-lambda-http.yaml` now uses `SourceArn` `...:api-id/*/*` instead of REST-style `...:api-id/*/*/*/*`. **Deploy:** update stack or `aws lambda add-permission` with `--source-arn "arn:aws:execute-api:REGION:ACCOUNT:API_ID/*/*"` and remove the old statement. After fix, tail `/aws/lambda/ragnarok-trading-api` while curling `/health`. **Session 20:** production stack updated; manual duplicate permission removed so **only CloudFormation** owns invoke policy.

### 1. Grade Mismatch
Pipeline compares ungraded SCP price to graded eBay listings (and vice versa). Example: Juan Soto Gold Stars #224 -- SCP ungraded is $1.50, PSA 10 is $30. Pipeline matched a $9.99 ungraded BIN against the PSA 10 price and showed $17 profit. Completely wrong.

### 2. Variant Matching Still Too Loose
"Magenta Speckle Refractor" matched to SCP "Magenta Refractor" -- different cards, different print runs (/350 vs /399). Pipeline needs to treat sub-variants as distinct parallels.

### 3. SCP Price Reliability on Low-Volume Cards
SCP prices based on 1-3 sales from 2+ years ago are historical artifacts, not current market value. Example: Jordan Walker Father's Day Blue -- SCP says $220 based on 2023-2024 sales, but the card hasn't sold in 6 months and the trend is clearly down. The pipeline treats stale SCP prices as gospel.

Worse: some low-volume SCP pages have misclassified sales (Juan Soto sales appearing on a Jordan Walker product page). When there are only 2-3 total sales, one misclassified entry corrupts the entire price.

### 4. Volume Filter Not Tight Enough
"3 sales per year" currently passes the volume filter but produces nothing but noise in practice. Every card manually validated at that volume level was a pass -- either dead money, declining trend, or no exit liquidity.

### 5. Factory Set Filter Blind Spot
Factory set filter checks eBay titles but not SCP product names. When the eBay title says "2020 Topps #224 Gold Star" (no "complete set" mention) but the SCP product is "2020 Topps Complete Set", the filter misses it.

### 6. Reprint Detection Gaps
Cal Ripken "R&N China Topps Porcelain" and "2015 Topps Cardboard Icon 5x7" are reprints that don't match current REPRINT_PATTERNS. Need to add "porcelain", "cardboard icon", "5x7" patterns.

### 7. Team Set / Multi-Card Listings
Nolan Ryan 1972 Topps -- eBay listing was "California Angels Team Set w/o #595 Nolan Ryan (27)" -- a team set WITHOUT the Ryan card. Pipeline matched it as a single card.

---

## LESSONS LEARNED (March 20 -- Manual Validation Session)

### Volume Is Everything
Every card manually validated with "3 sales per year" or less was a pass:
- Jordan Walker Father's Day Blue /50: 3 sales/year, declining from $470 to $190, no PSA 9 data
- Jordan Walker Brick by Brick Auto /50: 3 sales/year, last sale July 2023, zero recent eBay solds
- Jordan Walker Leaf Ultimate Auto: 1 sale/year, SCP page has misclassified sales
- Juan Soto Gold Mosaic /10: 1 sale ever (2022), BGS 9 not PSA, no exit

The one card that looked like a real opportunity: Juan Soto Mystical Green /99 -- "1 sale per month" volume, 3 recent comps validating the SCP price, active player, stable trend.

### Real Arbitrage Range
Real opportunities exist in the 50-85% of SCP range. Below 30% is almost certainly a different product. Between 30-50% needs manual review. The efficient market hypothesis holds for popular players on popular cards -- cheap BIN listings are cheap for a reason (factory set, wrong variant, damaged, etc.).

### Auctions Are Where Margins Live
BIN below market rate is inherently suspicious. Auctions ending below market rate is normal -- that's how auctions work. The pipeline was excluding all auctions, which was cutting off the best opportunities.

---

## What Changed (March 22 2026 -- Session 12)

### NEW: Three-Tier Pricing Waterfall
- When SCP fails to match a card, pipeline now tries two fallback sources before giving up
- Tier 1: SCP (DB lookup, SCP cache 24h TTL, Selenium fallback) -- primary, highest confidence
- Tier 2: 130point sold comps (DB cache from background worm, instant, free) -- actual eBay sold prices
- Tier 3: eBay active BIN comps (1 API call per card, median of 3+ listings) -- market asking prices
- All fallback-priced opportunities flagged for review (lower confidence than SCP)

### NEW: 130point.com Scraper (`backend/scrapers/oneThirtyPoint_scraper.py`)
- Plain HTTP POST to `https://back.130point.com/sales/` -- no Selenium needed
- Returns actual completed eBay sale prices, dates, listing types (auction vs fixed)
- Rate limit: 10 requests/minute (we enforce 7s between calls)
- Zero eBay API calls consumed

### NEW: Background Data Worm (`worm_130point.py`)
- Slowly crawls 130point.com building a local cache of eBay sold data in `sold_comps` table
- Prioritizes: cards with SCP rates first (cross-validation), then cards without (discovery)
- 48h TTL on cached data, ~8 queries/min = ~14,000/day capacity, all free
- Run: `nohup python3 worm_130point.py --limit 1000 > /tmp/worm.log 2>&1 &`

### NEW: eBay BIN Comps Fallback
- `search_active_bin_comps()` in ebay_scraper.py -- searches BIN-only listings, 1 API call
- `find_ebay_comps_fallback()` -- median of 3+ ungraded BINs, trims outliers
- Tested: Max Anderson Mojo Auto $24.49 (4 comps), Trey Sweeney Auto $15.00 (15 comps)

### NEW: Database Migration 014 -- sold_comps table
- player_name, card_year, card_set, card_number, parallel, sale_price, sale_type, sale_date
- Indexed: (lower(player_name), card_year, lower(card_number))

### KEY DISCOVERY: 130point returns actual SOLD data (not asking prices)
- eBay Browse API returns active listings (asking prices)
- 130point aggregates actual completed eBay sales (sold prices)
- More conservative and accurate: Max Anderson Mojo -- 130point $14.99 (sold) vs eBay BIN $24.49 (asking)

### KEY DISCOVERY: eBay Browse API `total` field
- Every search returns `total` count even with `limit=1` (1 API call = 1 volume reading)
- Enables cheap volume-based player discovery without fetching items

## What Changed (March 22 2026 -- Session 13)

### NEW: Cross-Validation QA Rule
- `scp_vs_sold_comps` rule in `qa_opportunities.py`: flags when SCP price diverges >50% from 130point sold median
- Requires 3+ sold comps, trims outliers, severity warning at >50%, critical at >75%
- Runs as part of standard QA pass (does not block pipeline)

### NEW: Price Source Tracking
- Migration 015: `price_source` column on opportunities table (values: scp, sold_comps, ebay_comps)
- Wired into both BIN pipeline (always 'scp') and auction pipeline (tracks three-tier fallback)
- Exposed in API responses, displayed as confidence badges in frontend

### NEW: $10 Minimum Profit Floor
- BIN pipeline default changed from $5 to $10 (matches auction pipeline)
- Both pipelines still accept `--min-profit` override

### NEW: Tabbed Card Detail Modal (`CardDetailModal.jsx`)
- Hero section: large card image, key numbers, live countdown, action buttons (always visible)
- Overview tab: player analytics (30d sales, avg sale, velocity, active listings), SCP price tiers, QA flags
- Sell-Through tab: sell-through speed bars by price bucket, capital efficiency callout ("$20.51/day return")
- Price History tab: Recharts sparkline (avg/min/max sale price, SCP reference line), daily volume bars
- Timing tab: day-of-week avg price chart (cheapest day highlighted green), hourly sales volume
- Lazy-loads tab data only when clicked

### NEW: Player Analytics API
- `/api/players/{name}/stats`: cards, sales, velocity, avg sale price, market rates, opportunities, sell-through buckets
- `/api/players/{name}/price-history`: daily avg/min/max sale prices for sparkline chart
- `/api/players/{name}/timing`: day-of-week and hour-of-day sale patterns
- Accent normalization: Acu\u00f1a matches Acuna (fixes zero-data bug for accented player names)

### NEW: Live Countdown Timers
- Every auction card shows seconds ticking: `14h 02m 37s` format
- Client-side 1-second intervals against `end_time` from DB
- `end_time` now exposed in auction API response
- Modal shows live countdown in pricing grid
- Ended auctions show "Ended" label with dimmed opacity

### NEW: Confidence Badges
- Green "SCP" badge: priced from SportsCardsPro (highest confidence)
- Blue "Sold Comps" badge: priced from 130point sold data
- Amber "Market Comps" badge: priced from eBay BIN comps (lowest confidence)
- Shown on every card in list view and in modal hero

### NEW: Scheduled Bids Infrastructure (Snipe Queue)
- Migration 016: `scheduled_bids` table (max_bid, snipe_seconds, ebay_item_id, end_time, status)
- API: POST/GET/DELETE `/api/scheduled-bids`
- Model: `ScheduledBid` in models/__init__.py
- Frontend: Snipe UI complete (Session 14)
- Placeholder for future eBay OAuth auto-bid integration

### NEW: Worm Improvements
- `--opportunities` flag: crawls cards from opportunities table first (cross-validation priority)
- 429 retry logic: 10-minute wait, up to 3 retries (was dying immediately on rate limit)

### FIX: Accent Mismatch in Player Stats
- `Ronald Acu\u00f1a Jr.` (opportunities) vs `Ronald Acuna Jr` (cards) now match
- Uses unicodedata NFD normalization + period stripping
- Affects player stats API and all player-level queries

### NEW: Frontend Features
- QA flags displayed in expanded card view (color-coded by severity)
- "Full Details" button in expanded card view opens modal
- Card thumbnails clickable to open modal
- Filter bar with Max Bid, Min Profit, Min ROI inputs

## What Changed (March 23 2026 -- Session 16)

### NEW: Business Operating System (ADR-006) -- Full Build
- Migration 017: 4 new tables -- `business_goals`, `daily_snapshots`, `daily_plans`, `capital_transactions`
- Applied to both local + RDS (24 migrations total, 23 tables)
- `backend/services/business_planner.py`: BusinessPlanner class with goal decomposition, 12-month compounding trajectory, daily target calculation, capital tracking, snapshot generation, daily plan generator, catch-up logic
- `backend/api/routes/business.py`: 6 endpoints -- dashboard, trajectory, today's plan, set goal, record capital, history
- 4 SQLAlchemy models added to `backend/models/__init__.py`
- Routes registered in `backend/api/main.py`
- Goal on RDS: id=2, $1K starting capital, 25% margin, 13% fees, 2 turns/month = $12,215 Year 1 projection

### NEW: Business Dashboard Frontend (`frontend/src/pages/BusinessDashboard.jsx`)
- Goal setup form (if no goal exists) with all parameters
- Top stats row: available capital, daily target, today's profit, YTD profit
- Week + month progress bars with color-coded fill
- Inventory summary: total cards, listed, unlisted, cost basis
- Today's action plan: buy opportunities (with eBay links, ROI, profit), list unlisted, reprice stale, research
- 12-month trajectory chart (Recharts: cumulative profit + working capital lines)
- Capital transaction form (deposit, sale, purchase, withdrawal)
- Hours override for plan regeneration
- Edit Goal Settings toggle
- Ragnarok Gaming dark theme, consistent with Opportunities page

### NEW: Business API Client Functions
- 6 functions added to `frontend/src/api/client.js`: getBusinessDashboard, getBusinessTrajectory, getBusinessPlan, setBusinessGoal, recordCapitalTransaction, getBusinessHistory

### NEW: Business Nav Link
- "Business" added to main navigation bar in `App.jsx`
- Route: `/business` -> BusinessDashboard component

## What Changed (March 23 2026 -- Session 15)

### NEW: All 167 Tests Passing in CI
- Fixed test_ebay_scraper.py: mocked token_manager, updated card_set expectations, fixed api_error and price_conversion tests
- Fixed test_trend_calculator.py: updated social score expectations to match 60% mentions + 40% normalized sentiment formula
- Fixed test_multi_platform_sourcing.py: updated to nested response structure (`options["urls"]`)
- Fixed test_ui_enhancements.py: row color function always returns '' (avg_price > avg_price * multiplier)
- Fixed test_database.py: DATABASE_URL env var, unique constraint with all 7 columns, named columns in price_trends
- 63 unit + 11 integration + 70 QA + frontend build = 167 passed, 0 failed

### NEW: Scheduled GitHub Actions Pipelines
- BIN pipeline: `0 6,18 * * *` (2AM/2PM ET) -- runs `find_opportunities.py` against RDS
- Auction pipeline: `0 9,21 * * *` (5AM/5PM ET) -- runs `find_auction_opportunities.py` against RDS
- Daily report: `0 23 * * *` (7PM ET) -- runs `daily_report.py`, uploads JSON artifact
- All workflows also support manual `workflow_dispatch` triggers

### NEW: Daily Operations Report (`daily_report.py`)
- Tier 2: Pipeline health (job_runs table), database health (table row counts), data freshness
- Tier 3: Data quality (null SCP prices, negative profits, duplicate eBay IDs), QA flags summary
- Tier 4: Opportunity summary by listing type, 7-day trends, action items (critical/warnings/info)
- Outputs to stdout and `/tmp/daily-report.json`

### NEW: ADR-006 Business Operating System
- Full scope: 3 tables (business_goals, daily_snapshots, daily_plans)
- Goal decomposition with honest compounding math ($1K at 25% margin = ~$14.5K Year 1)
- Daily plan generator, catch-up logic, capital tracker, inventory triage
- Added as Milestone 2.5 in ROADMAP.md

### FIX: Firefox Install on GitHub Actions Runners
- Ubuntu 24.04 (Noble) dropped `firefox-esr` from default repos
- Added `ppa:mozillateam/ppa` to both pipeline workflows
- Pinned geckodriver to v0.36.0 (GitHub API rate limiting returned HTML instead of JSON for latest release)

## What Changed (March 23 2026 -- Session 14)

### NEW: Snipe UI in Card Detail Modal
- "Snipe $XX.XX" button: calculates recommended max bid from SCP (SCP * 0.87 - $10 profit - shipping)
- Expands to snipe panel: big profit headline (updates live as user adjusts bid), math formula summary, bid input pre-filled with recommended price, snipe timing dropdown (3/5/10/15/30s), Queue button
- "Schedule Bid" button: manual entry for users who have their own number, separate panel with bid input + timing + live profit preview
- Panels are mutually exclusive (opening one closes the other)
- After scheduling: both buttons replaced with "Bid Queued" badge
- BIN cards show "Buy $XX.XX" green button linking directly to eBay
- Timer and bid count separated to their own context row (not competing with action buttons)
- eBay/SCP links demoted to small text links (reference, not decisions)

### NEW: My Bids Strip on Opportunities Page
- Horizontal scrollable strip at top of Opportunities page showing all scheduled bids
- Each bid card: thumbnail, player/card info, live countdown (1-second ticks), max bid, snipe timing
- Urgency indicators: normal -> amber (< 1 hour) -> red pulse (within 2x snipe window)
- Cancel button removes bid via API, View link opens eBay listing
- Strip hidden when no scheduled bids exist

### NEW: RDS as Primary Database
- `.env` DATABASE_URL switched from localhost to RDS
- All pipeline runs now write to RDS by default
- Local database kept structurally in sync for fallback

### NEW: Migration Runner (`migrate.py`)
- `schema_migrations` table tracks which migrations have been applied
- `python3 migrate.py --both`: applies pending migrations to local + RDS
- `python3 migrate.py --status --both`: shows applied vs pending
- `python3 migrate.py --local` / `--rds`: target one database
- Handles already-existing objects gracefully (records as applied, doesn't fail)
- 23 migrations tracked on both databases, both up to date

### FIX: Variable Ordering Bug in CardDetailModal
- `recSnipe` was referencing `scpPrice` and `shipping` before they were declared
- Moved recommended snipe calculation below variable declarations

## What Changed (March 22 2026 -- Session 11)

### REWRITE: Auction Search Strategy
- Replaced 101 set-specific queries ("2023 Topps Series 1", etc.) with 110 value-focused + player-specific queries
- 30 value queries: numbered parallels (/25, /50, /99...), autographs, refractors, premium products (Tier One, Tribute, Museum, etc.)
- 80 player queries: top 40 DB players x 2 ("player auto numbered" + "player refractor")
- Added pagination: up to 1000 results per query (was capped at 200)
- Result: searches like a dealer, not like a catalog

### NEW: Fuzzy Parallel Matching (Pass 2B)
- Pass 2A: strict match (all SCP parallel words in eBay title) -- unchanged
- Pass 2B: word-overlap scoring -- extracts meaningful words from both SCP parallel and eBay title, scores by overlap fraction
- Requires 50%+ overlap and at least 1 meaningful word match
- Picks best unambiguous match; refuses to guess on ties
- Fixes: "Aqua" now matches "Aqua Refractor", "Sparkle Refractor" matches "Refractor Chrome Variation"
- Noise words filtered: set names, generic terms (card, baseball, topps, etc.)

### NEW: BIN Sanity Check for Hybrid Listings
- If auction+BIN hybrid listing has BIN price < 50% of SCP price, reject the opportunity
- Seller's own BIN is a market signal -- if they'll sell for $6 and SCP says $27, SCP match is wrong
- Catches the Dylan Crews false positive: $6 BIN vs $27 SCP = 22% ratio = rejected

### FIX: Hybrid Auction+BIN Price Extraction
- eBay's `price` field on hybrids returns the BIN price, not the current bid
- Now uses `currentBidPrice` for the actual bid amount
- BIN price stored separately in `bin_price` field for sanity checking
- Pure auctions unaffected (no `currentBidPrice` field)

### FIX: Player Name Period Matching
- MLB API stores "Vladimir Guerrero Jr." with period; eBay titles use "VLADIMIR GUERRERO JR" without
- Both player names and titles now stripped of periods before matching
- Fixes all Jr./Sr. players: Vlad Jr, Tatis Jr, Witt Jr, Griffey Jr, Acuna Jr, Ripken Jr

### FIX: eBay Scraper Player Aspect Names
- `get_full_item_details()` now accepts Player, Player/Athlete, Athlete, Player Name (was only Player)
- Detail lookup fallback now checks `detail_aspects` dict (was incorrectly checking search-level `aspects`)

### NEW: SCP Match Diagnostic Logging
- First 30 no_scp cards now show: variants found, variant names+prices, Pass 1 tried value, Pass 2 search text, Pass 3 signals, eBay title
- `find_scp_match_via_selenium()` returns 3-tuple: (result, was_cached, diagnostics)
- Diagnostics dict tracks: variants_found, variant_names, pass1_tried, pass2_searched, pass3_signals, fail_reason
- Makes the SCP matching black hole visible for debugging

## What Changed (March 22 2026 -- Session 10)

### NEW: QA Validation System
- `qa_opportunities.py`: background post-pipeline validator
- Rules: extreme_roi (>500%), high_roi (>300%), price_ratio_10x, no_scp_url, card_number_mismatch, low_bid_high_scp
- Stores qa_status (pending/clean/flagged/critical), qa_flags (JSONB), qa_reviewed_at on opportunities
- Migration 012: qa_status, qa_flags, qa_reviewed_at columns
- Does NOT block pipeline -- runs after, in the background

### NEW: MLB Stats API Player Roster
- Replaced 40-player DB lookup with MLB Stats API (`statsapi.mlb.com/api/v1/sports/1/players?season=YEAR`)
- Free, no auth, ~1,400 players per year, 2,104 unique across 2023-2026
- Dramatically reduced "no_player" skip rate in auction pipeline
- Names sorted longest-first to prevent partial matches

### NEW: QA Test Suite (67 tests passing)
- `tests/qa/test_scp_matching.py`: 40 tests for SCP matching logic
- `tests/qa/test_opportunity_analyzer.py`: 19 tests for profit/fee/auction calculations
- `tests/qa/test_api_contract.py`: 8 tests for API response shape
- Fixed JSONB/SQLite incompatibility in conftest.py

### NEW: Unified Pipeline
- `find_opportunities.py` now automatically runs auction pipeline after BIN completes
- One command runs both: `python3 find_opportunities.py --max-budget 200 --min-profit 5 --min-roi 20 --top-players 40`
- BIN pipeline only clears BIN results (was wiping auctions)

### FIX: SCP Selenium Matching (Critical)
- Removed wrong-parallel fallback (was returning first result with any price)
- Added `_scp_url_has_card_number()` -- verifies card number in SCP URL before accepting
- Exact parallel match only, no fallback

### FIX: Lot Detection
- Added `is_lot()` function: detects multiple # signs, X & Y & Z patterns, "N cards" language
- Integrated into `is_junk()` filter

### NEW: Domain -- ragnarokgamez.com
- ACM certificate issued: `arn:aws:acm:us-east-1:635601810497:certificate/8dda492b-b16f-45bf-965e-9268abaabe78`
- Covers ragnarokgamez.com + *.ragnarokgamez.com
- All docs updated from cardpulse.jgaffiliated.com to ragnarokgamez.com
- Logger namespace changed from cardpulse to ragnarok
- AWS resource names (RDS endpoint, stack names) unchanged (deployed infrastructure)

### NEW: Roadmap Additions
- Milestone 4.5: UI Behavior Tracking (user_events table, feedback loop with QA flags)
- Milestone 9: Predict the Spike (standard leading indicators + nuanced signals: social media, artist features, local communities, call-ups, breaker schedules, cross-sport correlation)
- ADR-005 planned: User model, personalization, opportunity scoping

## What Changed (March 21 2026 -- Session 9)

### NEW: Auction-First Pipeline (`find_auction_opportunities.py`)
- Searches eBay for auctions ending soon by year + set name (not generic "baseball card")
- 101 search queries across 4 years x 24+ sets (Topps Chrome, Bowman Chrome, etc.)
- eBay category 261328 filter (Trading Card Singles only)
- Player name extraction: DB match (40 players) -> eBay item aspects fallback
- Card number extraction: title -> aspects -> full item details (3-pass)
- Quality signals: serialed (/XX), auto, rookie, non-base parallel
- SCP validation: database first (4,400 market rates), Selenium fallback
- Profit formula: SCP * 0.87 - (bid + shipping) >= $10
- Resilient Selenium: if Firefox fails, continues with DB-only matches
- Progress output during quality filtering (every 50 auctions, every 25 detail lookups)
- Stores: shipping, bid_count, end_time, scp_volume in opportunities table
- GitHub Actions workflow: `.github/workflows/auction-pipeline.yml`

### NEW: Database Migration 011
- Added columns to opportunities: shipping, bid_count, end_time, scp_volume

### FIX: SportsCardsPro Scraper Firefox Binary
- Auto-detects Firefox binary path (was hardcoded to `/usr/bin/firefox`)
- Now checks `/usr/lib/firefox/firefox`, `/usr/bin/firefox-esr`, `/usr/bin/firefox`

### FIX: API Auction Dict
- `_auction_to_dict()` now uses stored shipping, bid_count, end_time from DB
- Calculates hours_left dynamically from end_time
- Includes scp_volume in response

---

## What Changed (March 20 2026 -- Sessions 7-8)

### NEW: Auction Support
- Removed hard auction filter -- auctions now flow through the pipeline
- Auctions skip price floor check (low current bids are normal)
- Auctions are never flagged as "suspicious price"
- Every opportunity tagged with `listing_type` (buy_it_now or auction)
- Console output shows [BIN] or [AUCTION] tags
- Summary shows breakdown: "113 opportunities found (85 BIN, 28 Auction)"
- Database: `listing_type` column added (migration_010)
- API: `?listing_type=auction` filter, `/api/auctions` endpoint now functional

### NEW: Pipeline Quality Filters (Session 7)
- Auction filtering: discovered pipeline was treating auction bids as BIN prices, fixed
- Factory set filter: 12 patterns (complete set, montgomery club, walmart/target exclusive, etc.)
- Price floor: BIN below 30% of SCP hard-rejected (MIN_PRICE_RATIO = 0.30)
- Suspicious flagging: BIN between 30-50% of SCP flagged for "Needs Review"
- Volume capture: parses SCP volume text ("1 sale per day", "rare", etc.)
- Volume filter: skips "rare", "1 sale per year", "2 sales per year"

### NEW: GitHub Actions + RDS Infrastructure (Session 7)
- `.github/workflows/pipeline.yml`: workflow_dispatch with configurable inputs
- `aws/cloudformation/rds.yaml`: RDS PostgreSQL free tier template
- `aws/migrate-to-rds.sh`: local-to-RDS migration script

### Previous Sessions
- Session 6 (March 19-20): SCP-to-eBay pipeline built and validated
- Session 5 (March 19): SCP card-number-first matching rewrite
- Session 4 (March 19): Graduated SCP search + set validation, insert set detection
- Session 3 (March 18): Parallel precision, volume expansion to 40 players, Ragnarok Gaming UI
- Session 2 (March 18): Card images, Leaf sub-sets, SCP sanity check, buy links
- Session 1 (March 18): Pipeline, discovery, OpportunityAnalyzer core

---

## Known Issues / Next Steps (Priority Order)

### 1. TIGHTEN VOLUME FILTER
Reject "3 sales per year" -- every card at that level was a pass during manual validation. Minimum viable volume is "1 sale per month".

### 2. ADD MINIMUM PROFIT THRESHOLD
$6 profit on an $18 card isn't worth the research time. Need a minimum dollar amount ($15-20).

### 3. FIX GRADE MISMATCH
Pipeline must compare ungraded-to-ungraded, graded-to-graded. Currently uses SCP ungraded price for all listings regardless of grade.

### 4. FIX VARIANT MATCHING
"Magenta Speckle" != "Magenta". Sub-variants need to be treated as distinct parallels.

### 5. EXPAND REPRINT PATTERNS
Add: "porcelain", "cardboard icon", "5x7", "team set", "set w/o", "set without".

### 6. WORKER SEPARATION (Milestone 1)
Data gathering (SCP scraping, eBay API calls) must run in a separate process from the core app. See ADR-004.

### 7. DEMAND-DRIVEN REFRESH (Milestone 2)
No crons. Data refreshes only when needed. See ADR-004.

### 8. CROSS-VALIDATE SCP PRICES
130point sold comps now available for cross-validation. Next: auto-flag when SCP and 130point median diverge by >50%.

### 9. Redesign Remaining Pages
Inventory, Watchlist, CardDetail still have old white theme.

### 10. AWS DEPLOYMENT (Milestone 3)
Core app on ECS, worker on ECS task, database on RDS, frontend on CloudFront + S3.

### 11. EBAY ACCOUNT INTEGRATION (Milestone 3)
OAuth login, auto-import purchases, auto-track sales.

### 12. APPLY FOR EBAY COMPATIBLE APPLICATION STATUS
Upgrade from 5,000 to 50,000-200,000+ API calls/day.

### 13. Basketball/Football Support (Milestone 6)

See `docs/ROADMAP.md` for full feature roadmap with milestones.

---

## Architecture

### Opportunity Pipeline
```
HOT PLAYERS (from eBay sales volume or manual list)
    |
    v
[SCP Selenium] -- 1 search per player --> full catalog (100 variations + prices + volume)
    |
    v
FILTER -- $20-$1000 SCP price range
       -- Volume filter (reject rare, 1/year, 2/year)
    |
    v
[eBay Browse API] -- 1 search per variation --> active listings (BIN + Auctions)
    |
    v
VALIDATE -- player name + year + card# + variation keyword in title
         -- exclude junk, factory sets, reprints, wrong sets
         -- BIN price floor (30% of SCP)
    |
    v
CALCULATE -- SCP price - buy price - 13% fees = profit
    |
    v
STORE -- opportunities table (listing_type: buy_it_now or auction)
    |
    v
API --> Ragnarok Gaming UI (BIN + Auction tabs, Needs Review section)
```

## Key Files

| File | Purpose |
|------|---------|
| `find_opportunities.py` | SCP-to-eBay BIN opportunity pipeline |
| `find_auction_opportunities.py` | eBay-first auction opportunity pipeline (3-tier pricing) |
| `worm_130point.py` | Background 130point sold data crawler |
| `backend/scrapers/oneThirtyPoint_scraper.py` | 130point.com eBay sold data scraper |
| `backend/models/__init__.py` | SQLAlchemy models (Opportunity with listing_type) |
| `backend/api/routes/opportunities.py` | Opportunities + Auctions API endpoints |
| `frontend/src/pages/Opportunities.jsx` | Opportunities page (Ragnarok Gaming theme) |
| `backend/run_pipeline_full.py` | Master data pipeline (7 queries/player) |
| `backend/scrapers/ebay_scraper.py` | eBay import + parallel extraction |
| `backend/utils/logger.py` | Structured logging (WARN+ to DB) |
| `backend/utils/job_tracker.py` | Job tracking (job_runs table) |
| `backend/utils/retention.py` | Self-managing data retention |
| `daily_report.py` | Daily operations report (Tiers 2-4) |
| `backend/services/business_planner.py` | Business Operating System engine (ADR-006) |
| `backend/api/routes/business.py` | Business planner API endpoints (6 routes) |
| `frontend/src/pages/BusinessDashboard.jsx` | Business dashboard page (goal, plan, trajectory) |
| `.github/workflows/pipeline.yml` | GitHub Actions BIN pipeline (cron + manual) |
| `.github/workflows/auction-pipeline.yml` | GitHub Actions auction pipeline (cron + manual) |
| `.github/workflows/daily-report.yml` | GitHub Actions daily report (cron + manual) |
| `.github/workflows/qa.yml` | GitHub Actions QA/CI pipeline (push + PR) |
| `aws/cloudformation/rds.yaml` | RDS PostgreSQL CloudFormation template |
| `PIPELINE-OPS.md` | Operations guide |

## Services

```bash
sudo service postgresql start

# API: http://localhost:8000 (Swagger: /docs)
cd /home/tweedledee101/TradingCards
nohup /usr/bin/python3 -m backend.api.run > /tmp/api.log 2>&1 &

# Frontend: http://localhost:3000
cd /home/tweedledee101/TradingCards/frontend
nohup npm run dev > /tmp/frontend.log 2>&1 &
```
