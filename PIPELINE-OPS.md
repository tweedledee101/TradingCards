# Pipeline Operations Guide

## One Command To Rule Them All

```bash
cd /home/tweedledee101/TradingCards
/usr/bin/python3 -m backend.run_pipeline_full --fresh --sport Baseball --top 40
```

## Tests (unit + PostgreSQL integration)

- **Integration tests** (`tests/integration/`, marker `integration`) connect to **`DATABASE_URL`** — typically **RDS** (`backend/.env`). They need **outbound network** (DNS + port **5432**). If you see `could not translate host name` or connection timeouts, the failure is usually **no network path** (corporate firewall, offline laptop, or a **sandboxed** tool run), not “AWS is unreachable” by default.
- **Local / WSL:** `source .venv/bin/activate` then either `set -a && . backend/.env && set +a` before `pytest`, or rely on `tests/integration/conftest.py` (loads `DATABASE_URL` from `backend/.env` when the env var is unset).
- **Full suite:** `./run_tests.sh all` or `./run_tests.sh integration` sources `backend/.env` when present.
- **`ModuleNotFoundError: No module named '_sqlite3'`** when running `pytest`: the **`pytest-cov`** plugin loads **`coverage`**, which needs the stdlib **`sqlite3`** extension. This repo’s **`pytest.ini`** disables **`pytest_cov` by default** so normal runs work on Pythons built without SQLite (common with **`/usr/local`** installs). Use **`./run_tests.sh coverage`** or **`pytest -p pytest_cov --cov=...`** only on an interpreter that has **`_sqlite3`** (e.g. Ubuntu **`apt install python3.12 python3.12-venv`**, or rebuild from source after **`libsqlite3-dev`**). **`tests/qa/`** in-memory SQLite uses **`pysqlite3-binary`** when **`import sqlite3`** fails; it is listed in **`backend/requirements.txt`** — run **`pip install -r backend/requirements.txt`** after pull.

GitHub Actions workflows run with network and repo secrets; local parity requires the same.

## Player discovery observability (eBay Browse)

When discovery returns **0 players**, the run is not “silent”: **`backend/discover_players.py`** prints a **`DISCOVER_SUMMARY`** JSON line (stdout) and writes **`error_log`** rows when all seeds are zero or when Browse returns HTTP/API errors.

- **Logs:** search workflow output for **`DISCOVER_SUMMARY`** (per-seed `total`, `http_status`, `ebay_errors`, samples).
- **Database:** `error_log` rows use categories such as **`discover_all_seeds_zero`**, **`ebay_browse_discover_http`**, **`ebay_browse_discover_api_errors`**, **`ebay_browse_discover_exception`**, **`discover_run_degraded`**.

```sql
SELECT created_at, category, message, context
FROM error_log
WHERE category LIKE 'discover%' OR category LIKE 'ebay_browse_discover%'
ORDER BY created_at DESC
LIMIT 50;
```

## What The Pipeline Does (In Order)

| Step | What | API Calls (40 players) | Time |
|------|------|------------------------|------|
| 1. Discover | Search 45 seed players, rank by eBay volume | 45 eBay | ~30s |
| 2. Import Sales | Fetch sold listings (7 queries/player) | 280 eBay | ~15min |
| 3. Active Listings | Fetch current listings (7 queries/player) | 280 eBay | ~15min |
| 4. Trends | Calculate price trends from sales data | 0 | ~5s |
| 5. SCP Rates | Scrape SportsCardsPro (graduated search + set validation) | 0 eBay | 2-8 hrs |

**Total eBay API calls: ~605/day (of 5,000 limit)**

### Set-Specific Searches (Step 2 & 3)

Each player gets 7 eBay queries instead of 1:
1. `{player} card` (generic)
2. `{player} Topps Chrome`
3. `{player} Bowman Chrome`
4. `{player} Topps Heritage`
5. `{player} Stadium Club`
6. `{player} Topps Finest`
7. `{player} Topps Inception`

Results are deduped by ebay_item_id across queries. This surfaces high-value parallels ($10-$100+) that get buried in generic searches (eBay returns max 200 per query).

Sets are configured in `backend/config/sets.py` (also has Basketball/Football sets).

## Pipeline Flags

```bash
--fresh              # Wipe all data first
--sport Baseball     # Sport filter (default: Baseball)
--top 40             # Number of top players (default: 20)
--skip-scp           # Skip slow SCP step
--skip-discovery     # Reuse existing players in DB
--scp-timeout 7200   # SCP timeout in seconds (default: 1800)
--days 7             # Discovery lookback days (default: 7)
```

## Running Auction Finder (eBay-First)

Searches eBay for auctions ending soon, validates against SCP.

### Basic Usage
```bash
# Default: 48h window, $10 min profit, $200 max budget, baseball
python3 find_auction_opportunities.py

# Tighter window, higher profit threshold
python3 find_auction_opportunities.py --hours 24 --min-profit 15

# Specific years only
python3 find_auction_opportunities.py --years 2025,2026

# Dry run (no DB storage)
python3 find_auction_opportunities.py --dry-run
```

**HTTP 429 on Browse `item_summary/search`:** eBay is rate-limiting (daily cap or burst). Wait (often **hours** or until the next **UTC/Pacific** day), check usage in [eBay Developers](https://developer.ebay.com/) → your keyset → **Analytics**. The scraper **retries 429** using `Retry-After` and waits **1s between queries**; if every call still 429s, only time or a higher Browse limit fixes it.

### Auction Finder Flags
```bash
--hours 48           # Auctions ending within X hours (default: 48)
--min-profit 10      # Min profit after bid + shipping + fees (default: $10)
--max-budget 200     # Max bid + shipping (default: $200)
--years 2023,2024,2025,2026  # Years to search (default: all four)
--sport baseball     # Sport (default: baseball)
--dry-run            # Show results without storing in DB
```

### Audit auction funnel (data, not guesses)

After any `auction_finder` run, `job_runs.results_summary` stores JSON including **`auctions_searched`**, **`qualified`**, **`step2_skip_reasons`** (why listings dropped before SCP), **`step3_*`** counters (no pricing, bin sanity, low volume, below min profit), and **`opportunities_found`**.

**Step 3 pricing funnel:** **`step3_no_pricing`** counts listings with **no price after all sources**. **`step3_no_pricing_after_primary`** = entered fallback (no DB/SCP price). **`step3_no_pricing_after_sold_comps`** = still no price after 130point (so eBay BIN comps were tried or skipped). Compare the three to see whether the gap is **SCP**, **sold comps**, or **eBay comps**.

```bash
export DATABASE_URL='postgresql://...'   # RDS or local
python3 scripts/audit_auction_pipeline.py
# Re-measure vs previous run (newest vs second-newest job with JSON summary):
python3 scripts/audit_auction_pipeline.py --compare
```

**Stale ended auction rows** (audit prints `ended_still_stored`):

```bash
python3 scripts/cleanup_stale_auction_opportunities.py --dry-run
python3 scripts/cleanup_stale_auction_opportunities.py
```

Interpretation:

- **`qualified` ≪ `auctions_searched`** → Step 2 (card #, player, year, junk, budget) is the bottleneck; fix identity extraction / queries before SCP.
- **`step3_below_min_profit` dominates** → economic threshold or bid+ship too high vs comps; experiment `--min-profit` / `--max-budget` in **dry-run** and compare counts.
- **`step3_no_pricing` dominates** → use **`after_primary`** vs **`after_sold_comps`** vs final: primary SCP miss vs thin 130point vs weak eBay BIN comp set.

### Auction improvement hypotheses (test in order)

| Hypothesis | How to test | If true, lever |
|------------|-------------|----------------|
| H1: Most raw auctions die in Step 2 (`no_card_number`, `no_player`) | Run audit script; read `step2_skip_reasons` on latest run | Description/`shortDescription` `#` parse; more `get_full_item_details` coverage; broader aspects |
| H2: Many qualify but fail `step3_no_pricing` | `step3_no_pricing` large vs `qualified` | SCP cache fill rate, Selenium health, `sold_comps` worm volume, parallel matching fixes |
| H3: Pricing works but `step3_below_min_profit` dominates | Counters in `results_summary` | Soften `--min-profit` for a “scout” tier in UI; or raise `--max-budget` for high-end flips |
| H4: UI shows 3 because most rows **ended** | `ended_still_stored` vs `active_ui` in audit | Shorter `--hours` refresh cadence or filter/cleanup ended rows; run pipeline more often |
| H5: Query set misses liquid segments | `auctions_searched` high, `qualified` flat | Pipeline adds **`get_set_queries`** for top 15 DB players (see `HIGH_VALUE_SETS`); tune player cap or sets in `backend/config/sets.py` |

**SCP Selenium slow loads:** Firefox may log `Navigation timed out after … ms`; the scraper catches that and still parses partial HTML when possible. Raise **`SCP_PAGE_LOAD_TIMEOUT`** in `backend/.env` (default **60**s, max **180**) if timeouts are frequent.

**Services in play today (auctions):** eBay **Browse API** (`item_summary/search` ending soon, `item/{id}` details, BIN comp search), **MLB Stats API** (player names), **SportsCardsPro** (Selenium when DB/cache miss), **`sold_comps` / 130point worm**, **PostgreSQL** (`opportunities`, `job_runs`, `error_log`, `scp_cache`, `market_rates`).

**Can leverage more (experiments):** extra Browse queries (same API, watch daily cap), second sport flag, duplicate **set-specific** auction queries (proven in BIN pipeline’s 7-queries-per-player pattern), Trading API only if Browse lacks a field (extra app/credentials).

### What The Auction Finder Does

1. Searches eBay using **value queries + per-player queries** (top 40 DB players: auto/refractor + **set-specific** queries for the top 15 via `backend/config/sets.py`)
2. Paginates up to 1000 results per query (5 pages x 200)
3. Filters to eBay category 261328 (Trading Card Singles)
4. Deduplicates across all queries by eBay item ID
5. Quality filter: card number required (title -> aspects -> full item details)
6. Player identification: MLB Stats API roster (2,269 players) + period/accent normalization + eBay aspects fallback (Player/Athlete/Player Name)
7. SCP validation: database lookup first (4,400 market rates), SCP cache (24h TTL), Selenium fallback
8. Multi-pass SCP matching: Pass 1 exact parallel, Pass 2A strict text, Pass 2B fuzzy word-overlap (50%+), Pass 3 signal match (RC/Auto/Relic/print_run)
9. BIN sanity check: hybrid listing BIN < 50% of SCP = reject (seller disagrees)
10. Profit check: SCP * 0.87 - (current bid + shipping) >= $10
11. Fallback pricing: 130point sold comps (DB cache) -> eBay active BIN comps (1 API call)
12. Diagnostic logging: first 30 no_scp cards show variants found, pass attempts, failure reason
13. Stores opportunities with listing_type='auction', shipping, bid_count, end_time

---

## Nova Act — listing photo vs expected card (dev)

Proof script uses the **Nova Act Python SDK** (`act_get` + browser screenshots), not the Nova **chat** HTTP API used in `scripts/dev/test_nova_act_real_data.py`.

```bash
python3 scripts/dev/nova_act_listing_visual_probe.py --dry-run
export NOVA_ACT_API_KEY="..."   # https://nova.amazon.com/act
# Nova-act needs Python 3.10+ (Ubuntu default python3 is often 3.8/3.9 — use 3.12):
python3.12 -m pip install --user nova-act && python3.12 -m playwright install chrome
python3 scripts/dev/nova_act_listing_visual_probe.py \
  --listing-url "https://www.ebay.com/itm/..." \
  --expected "2022 Bowman Chrome Elly De La Cruz 1st"
```

More context: `acquisition/facebook_marketplace/README.md`.

Batch / benchmark cases (JSON + optional confidence thresholds):

```bash
python scripts/dev/run_nova_act_probe_cases.py --dry-run
# Edit scripts/dev/nova_act_probe_cases.json (enabled + real URLs), then:
python3.12 scripts/dev/run_nova_act_probe_cases.py --headless
```

**See Nova Act move a real browser (local, no eBay):**

```bash
python3.12 scripts/dev/nova_act_smoke_gym.py
```

Opens headed Chrome against Amazon’s public gym page — confirms SDK + API key + Playwright.

**WSL2 / odd window managers:** If you see `Page.captureScreenshot: Cannot take screenshot with 0 width`, the browser viewport was effectively 0×0 (minimized window, Wayland quirks). The dev scripts pass **`screen_width=1280`, `screen_height=720`** to `NovaAct`; maximize the Chrome window or use **`--headless`** if headed mode still fails.

**Python env:** `pip install -r backend/requirements.txt` pins **FastAPI** stack but uses **`pydantic>=2.10.6`** so **nova-act** can share the same user site-packages without a version clash. If you still see resolver warnings for **mcp** / **sse-starlette**, use a **dedicated venv** for Nova Act–only tools.

**Collectors Edge AI — full photo valuation (Playwright dev probe, not production):**

Uses https://collectorsedgeai.com **Photo** tab: upload image → click through CTAs → save **screenshot + HTML + JSON** (parsed low/median/high, confidence, recommendation when regex matches) under `scripts/dev/_collectors_edge_artifacts/` (gitignored), or **`$TMPDIR/tradingcards_collectors_edge`** if that folder is not writable (fix ownership with `sudo chown -R "$USER" ~/TradingCards` on WSL if needed). Success URL is **`/result`** or **`/cards/...`**. Stdout includes **`=== CE_RESULT_JSON ===`** … **`=== END CE_RESULT_JSON ===`** for quick copy/paste. The JSON object adds **`ce_extracted`** (pricing band, comps narrative, card signals, trend hints) and **`ce_pipeline_analysis`** (hard facts, verification lines vs `opportunities` identity + `scp_price`, suggested QA flags) when pipeline fields are present (`--from-db`). With **`--merge-qa-to-db`** (only valid with **`--from-db`**), each successful run merges **`suggested_qa_flags`** into **`opportunities.qa_flags`** using the same **`rule` / `severity` / `reason`** object shape as **`qa_opportunities.py`** (prior **`ce_*`** entries from CE are replaced; pipeline QA rules are kept). **`qa_status`** is escalated to **`flagged`** when CE adds non-critical flags, or **`critical`** + **`flagged=true`** when CE reports **`ce_player_mismatch_risk`**. Respect site terms; login may be required for some flows.

```bash
# Use `python -m pip` / `python -m playwright` so installs match the interpreter you run the script with.
python -m pip install -r scripts/dev/extra-requirements-collectors-edge.txt
python -m playwright install chromium
python scripts/dev/collectors_edge_photo_run.py \
  --image-url "https://i.ebayimg.com/..." \
  --keep-open 20
# No shell URL variable: first DB opportunity with an image (needs backend/.env + backend/requirements.txt):
python scripts/dev/collectors_edge_photo_run.py --from-db --db-skip 0 --headless --settle-ms 8000
# Watch several listings in one browser (headed): pause between CE results, leave window open at the end:
python scripts/dev/collectors_edge_photo_run.py --from-db --db-limit 3 --settle-ms 8000 --pause-between-cards 15 --keep-open 25 --slow-mo-ms 120
```
If you see “Cannot load Playwright” but pip succeeded, you’re on a **different** `python` than the venv’s (try `which python` and `python3.12` explicitly).

**Image URLs from your DB (no manual eBay copy-paste):** `opportunities.image_url` and `listing_image_urls` — print recent rows for probes:

```bash
cd ~/TradingCards && source .venv/bin/activate
python scripts/dev/print_opportunity_image_urls.py --limit 5
URL=$(python scripts/dev/print_opportunity_image_urls.py --limit 1 | head -1)
# Newest row is always the same card? Skip it: `--skip 1` (then 2, 3, …).
URL=$(python scripts/dev/print_opportunity_image_urls.py --limit 1 --skip 1 | head -1)
python scripts/dev/collectors_edge_photo_run.py --image-url "$URL" --keep-open 25
# Equivalent: --from-db --db-skip 1
# Explicit opportunity rows (order preserved), e.g. weak-SCP cohort samples:
python scripts/dev/collectors_edge_photo_run.py --from-db --opportunity-ids 2687,2685 --headless --settle-ms 8000 --keep-open 0
# Persist CE QA hints on the opportunity row (see merge behavior above):
python scripts/dev/collectors_edge_photo_run.py --from-db --opportunity-ids 2687 --headless --merge-qa-to-db
```

**CE artifact → SCP row in PostgreSQL:** `scripts/vision_retry_scp_from_images.py` uses **Amazon Nova + `cards`/`market_rates` only** — it does **not** call Collectors Edge. If the **listing text or Nova year/#** disagrees with your catalog but the **photo** is clear, run **`collectors_edge_photo_run.py`** on the same CDN URL, save the JSON, then:

```bash
# Pass the real path printed as `JSON: ...` after a CE run, or:
# --latest-ce-artifact: newest valid collectors_edge_*.json (skips empty/corrupt files); if none,
# follows ce_explore_*.json → artifact_json. You may also pass a ce_explore_*.json path directly.
python3 scripts/scp_lookup_from_ce_json.py --latest-ce-artifact
python3 scripts/scp_lookup_from_ce_json.py scripts/dev/_collectors_edge_artifacts/<name>.json
# When CE headline year ≠ opportunity row (e.g. 2019 vs 2020), match catalog to listing year:
python3 scripts/scp_lookup_from_ce_json.py artifact.json --prefer-db-year
python3 scripts/scp_lookup_from_ce_json.py /full/path/to/artifact.json --player "Mike Trout" --year 2011 --number US175
```
(Do not use literal `path/to/…` or a non-existent `ce.json` from docs — the script will error with a hint.)

That runs **`find_scp_match_for_vision`** using best-effort parsing from **`ce_extracted`** (`backend/utils/ce_scp_identity.py`). If nothing prices for the requested year but the same **#** exists under another **`cards.card_year`**, the matcher may **drop the year filter** and report **`db_match_mode`** `*_year_relaxed` (verify before trading). **MISS** lines from this script describe **catalog gaps**, not Nova. You still **manually** confirm eBay image ≈ CE result ≈ SCP product art before trusting comps.

**Collectors Edge — cohort exploration (polite sampling, not load testing):** `scripts/dev/collectors_edge_explore.py` picks recent rows **with listing images** per **cohort** (`baseline`, `weak_scp_url`, `scp_or_qa_gap`, `auction`, `qa_attention`, `flagged`, `bin`, `non_scp_price_source`). **`scp_or_qa_gap`** = missing **`scp_url`** **or** **`flagged`** **or** QA **`flagged`/`critical`** (not “everyone is `qa_pending`”). Default is **dry-run** (prints ids + row summaries). **`--execute`** runs `collectors_edge_photo_run.py` once per cohort. By default, **the same `opportunity_id` is not reused** across cohorts in one batch (later cohorts skip ids already sampled earlier); use **`--allow-duplicate-ids-across-cohorts`** to override. **`--merge-qa-to-db`** forwards to the photo script. **Sequential (default):** **`--cooldown-seconds`** between subprocesses (default 90s). **Parallel:** **`--max-parallel N`** runs up to **N Chromium subprocesses** at once (RAM-heavy; respect CE — use **`--launch-stagger-seconds`** e.g. 8–15 to spread starts). When **`--max-parallel` > 1**, cooldown is skipped. Writes **`ce_explore_<utc>.json`** under `_collectors_edge_artifacts/` with exit codes and artifact summaries. Use **`--list-cohorts`** for keys.

```bash
python scripts/dev/collectors_edge_explore.py --list-cohorts
python scripts/dev/collectors_edge_explore.py --dry-run --cohorts baseline,weak_scp_url,scp_or_qa_gap --per-cohort 2
python scripts/dev/collectors_edge_explore.py --execute --cooldown-seconds 90 --cohorts weak_scp_url,scp_or_qa_gap --per-cohort 1
python scripts/dev/collectors_edge_explore.py --execute --max-parallel 2 --launch-stagger-seconds 10 --cooldown-seconds 0
```

**Vision extract from an eBay listing (main + gallery thumbnails) for SCP retry:**

```bash
python3.12 scripts/dev/nova_act_listing_card_extract.py \
  --listing-url "https://www.ebay.com/itm/..."
```

Outputs JSON (`player_name`, `card_number`, `set_product_line`, `parallel_insert`, slab fields, etc.). Intended follow-up: map into existing SCP lookup (`find_scp_match_*`) for listings that failed text-only matching.

### Nova Act in GitHub Actions

- **Chromium in CI:** Yes. `ubuntu-latest` runners work with **headless** Playwright/Chromium. Nova Act’s loop uses screenshots internally; you do not need a display server for headless runs.
- **This repo:** [`.github/workflows/nova-act-smoke.yml`](.github/workflows/nova-act-smoke.yml) runs **`nova_act_smoke_gym.py --headless`** on **workflow_dispatch** only (gym URL, not eBay). Add repository secret **`NOVA_ACT_API_KEY`**.
- **eBay inside Actions:** Risky for default pipelines: datacenter IPs, consent walls, bot friction, and **cost per run** (Nova Act steps). Prefer **manual / scheduled** jobs, **`workflow_dispatch`**, **self-hosted** runner, or **AWS-managed browser** ([Bedrock AgentCore Browser](https://aws.amazon.com/blogs/machine-learning/introducing-amazon-bedrock-agentcore-browser-tool/) — see Nova Act docs) for production-scale listing automation.
- **Workaround pattern:** Keep **auction/BIN pipelines** text+API-based on GitHub; run **vision only after** a pipeline completes, using **`job_runs.results_summary.vision_post_pipeline_queue_sample`** (bounded samples — excluded rows + tertiary checks). Vision must **not** gate ingest.

**Browse API images vs www Cloudflare:** Item **CDN image URLs** from the **Buy Browse API** (`image`, `thumbnailImages`, `additionalImages`) are usually **HTTP-fetchable directly** for multimodal models (no `ebay.com` browser). **`opportunities.listing_image_urls`** stores gallery URLs on stored rows. Completed runs record **`vision_post_pipeline_queue_sample`** in **`job_runs.results_summary`**: **BIN** job — price-floor rejects + **flagged** suspicious BIN (30–50% of SCP) still written to **`opportunities`**; **auction** job — **Step 2 metadata skips** (`no_year` / `no_card_number` / `no_player`, bounded per reason, **only if HTTP image URLs are already on the row** from Browse search and/or the same GET `/item` call Step 2 already made for missing #/player/year — **no extra Browse calls for vision**) + no-pricing-after-fallback rows + **BIN ≪ SCP** sanity rejects. Summary also stores **`step2_skip_vision_queue_sample`** (same Step 2 rows only, for audits). Legacy auction-only key **`no_scp_vision_queue_sample`** remains for older summaries; **`vision_retry_scp_from_images.py`** prefers the unified key when present. Migration **`024`** added **`listing_image_urls`** on opportunities (`migrate.py --both` if you are behind).

**Vision → DB SCP retry (CDN only, post-pipeline):**

```bash
pip install openai   # also in backend/requirements.txt
python3 scripts/vision_retry_scp_from_images.py --latest-auction-job --limit 5
python3 scripts/vision_retry_scp_from_images.py --latest-bin-job --limit 5
# No recent job_runs sample yet — use rows already in `opportunities` (CDN images):
python3 scripts/vision_retry_scp_from_images.py --from-recent-opportunities 5 --dry-run
python3 scripts/vision_retry_scp_from_images.py --from-recent-opportunities 5 --listing-type buy_it_now --dry-run
# Or: python3 scripts/vision_retry_scp_from_images.py --json /path/to/queue.json --dry-run
```

Uses **`NOVA_API_KEY`** + **`NOVA_VISION_MODEL`** (default `nova-2-lite-v1`) against **`api.nova.amazon.com`**. Downloads images with **`backend/services/vision_card_extract.py`**, then **`find_scp_match_for_vision`** (Base↔RC-style parallel fallback + multi-variant heuristic; ingest still uses stricter **`find_scp_match_in_db`**). **On HIT (default):** inserts a **new** **`opportunities`** row when profit ≥ **`--min-profit`** (default 10), confidence ≥ **`--min-confidence`** (default `medium`), **`buy_price`** is on the queue row, and **`ebay_item_id`** is not already in **`opportunities`**. Rows are **`flagged=True`** with **`qa_flags`** `vision_retry_persist`. **`--no-persist`** = print HIT/MISS only. **Step 2–only** queue rows often lack **`buy_price`** → HIT may print **`DB_SKIP … skip_no_buy_price`**. **Auction** no-pricing / BIN-sanity samples now include **`buy_price`** + **`shipping`** (current bid) so persist can run. Review hint when vision **player** ≠ **`pipeline_card`** still prints. **MISS** lines append a **catalog hint** (`vision_scp_miss_hint`); empty **auction** queue prints **`job_run.id`** + **`results_summary`** keys when the latest job has no sample.

**If `import openai` fails but `pip` says satisfied:** the venv is almost certainly **mixed** (e.g. `.venv/lib/python3.12/site-packages` exists while `.venv/bin/python` is **3.8**, or the opposite). **`pip install`** and **`python3`** must target the **same** interpreter. **`openai` 2.x** does not install cleanly on **Python 3.8** (`jiter` wheel gap). **Fix:** `deactivate; rm -rf .venv; python3.12 -m venv .venv; source .venv/bin/activate; python3 -m pip install -r backend/requirements.txt` then `python3 -c "import openai"`.

---

## Running 130point Data Worm (Background)

Crawls 130point.com for eBay sold data. Zero eBay API calls. Builds `sold_comps` cache.

### Basic Usage
```bash
# Default: 100 cards
python3 worm_130point.py

# Longer run (background)
nohup python3 worm_130point.py --limit 1000 > /tmp/worm.log 2>&1 &

# Focus on one player
python3 worm_130point.py --player "Juan Soto"
```

### Worm Flags
```bash
--limit 100          # Max cards to crawl (default: 100)
--player "Name"      # Focus on a specific player
```

### What The Worm Does
1. Queries DB for cards lacking recent sold comps (48h TTL)
2. Prioritizes cards with SCP market rates (cross-validation value)
3. Then cards without SCP rates (discovery value)
4. Hits 130point backend API (plain HTTP POST, no Selenium)
5. Parses sold prices, dates, listing types from HTML response
6. Stores in `sold_comps` table
7. Rate: ~8 queries/min (under 130point's 10/min limit)

### Rate Limits
- 130point: 10 requests/minute, 429 = blocked 1 hour
- We enforce 7s between calls (safe margin)
- Capacity: ~14,000 queries/day

---

## Running Opportunity Finder (SCP-First / BIN)

### Basic Usage
```bash
# All 40 players, default filters (BIN + Auctions)
python3 find_opportunities.py --max-budget 200 --min-profit 5 --min-roi 20

# Specific players
python3 find_opportunities.py --max-budget 200 --min-profit 5 --players "Bobby Witt Jr,Mike Trout"

# Adjust SCP price range
python3 find_opportunities.py --max-budget 500 --min-scp-price 50 --max-scp-price 500

# Higher budget scan
python3 find_opportunities.py --max-budget 1000 --min-profit 20 --min-roi 15 --top-players 40
```

### Opportunity Finder Flags
```bash
--max-budget 200     # Max buy price (default: $200)
--min-profit 5       # Min profit after fees (default: $5)
--min-roi 20         # Min ROI % (default: 20)
--min-scp-price 20   # Min SCP price to consider (default: $20)
--max-scp-price 1000 # Max SCP price (default: $1000)
--players "A,B"      # Comma-separated player names (overrides --top-players)
--top-players 40     # Number of hot players by volume (default: 40)
```

### What The Opportunity Finder Does

1. Gets player list (from DB volume ranking or --players flag)
2. Scrapes SCP for each player's full catalog (Selenium/Firefox)
3. Filters by SCP price range and volume (rejects "rare", "1 sale/year", "2 sales/year")
4. Searches eBay for each variation (BIN + Auctions)
5. Validates: player + year + card# + parallel in title
6. Filters: junk listings, factory sets, reprints, wrong sets
7. BIN price floor: below 30% of SCP = hard reject (different product)
8. BIN suspicious flag: 30-50% of SCP = passes but flagged for review
9. Auctions: no price floor, no flagging (low bids are normal)
10. Calculates profit: SCP - buy price - 13% fees
11. Stores all opportunities in `opportunities` table with `listing_type`
12. Prints summary with [BIN] and [AUCTION] tags

### Output Format
```
[eBay 409/1074] Juan Soto 2025 Topps Update Mystical #MYS-14 [Green]
  SCP: $34.99
  Query: Juan Soto 2025 Topps Update Mystical #MYS-14 Green /99
  2 opportunities found!
    [BIN] $24.99 -> $34.99 = $6.75 profit (27% ROI)
    [AUCTION] $15.00 -> $34.99 = $18.04 profit (120% ROI)

RESULTS: 113 opportunities found (85 BIN, 28 Auction)
```

### Querying Results via API
```bash
# All opportunities
curl http://localhost:8000/api/opportunities

# BIN only
curl "http://localhost:8000/api/opportunities?listing_type=buy_it_now"

# Auctions only
curl http://localhost:8000/api/auctions

# With filters
curl "http://localhost:8000/api/opportunities?min_profit=20&min_roi=50&hide_flagged=true"

# Stats
curl http://localhost:8000/api/opportunities-stats
```

## Running on GitHub Actions (Off-Laptop)

Both pipelines can run on GitHub Actions. Requires RDS database.

### Setup
1. RDS is deployed: `cardpulse-db.ckvp9bhavaww.us-east-1.rds.amazonaws.com:5432` (legacy name, domain is ragnarokgamez.com)
2. Schema + migrations applied (001-023, tracked via `schema_migrations`)
3. GitHub secrets configured: `DATABASE_URL`, `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`
4. Trigger: Actions tab -> choose workflow -> Run workflow

### Scheduled Runs (Cron)
- **BIN Pipeline**: 2AM + 2PM ET daily (`0 6,18 * * *` UTC)
- **Auction Pipeline**: 5AM + 5PM ET daily (`0 9,21 * * *` UTC)
- **Card Data Pipeline** (sales / Trending): daily `0 11 * * *` UTC (~6–7 AM ET), `--skip-scp` on schedule
- **Daily Report**: 7PM ET daily (`0 23 * * *` UTC)
- **QA Pipeline**: on push/PR to main (CI)

**Card Data Pipeline** (`card-data-pipeline.yml`): **daily cron** `0 11 * * *` UTC (~6–7 AM ET) with **`--skip-scp`**. Still supports **Run workflow** manually.

All workflows also support manual `workflow_dispatch` triggers from the Actions UI.

### SPA “Market Movers” / Trending (`GET /api/trending`)

Backend: `backend/api/routes/trending.py`. A card appears only if **all** of the following hold:

| Rule | Detail |
|------|--------|
| Auth | JWT required (`require_auth`). |
| Data | At least one row in **`sales`** joined to **`cards`**. |
| Recency | `sales.sale_date >= now() - 30 days` (rolling window). |
| Price floor | Default query param `min_price=5.0`: **average** sale price in that window must be **≥ $5** (cards cheaper than that are dropped). |
| Limit | Up to `limit` groups (default 100; UI requests 200), ordered by sale count. |

**What does *not* feed Trending:** **`find_opportunities.py`** and the scheduled **Opportunity Pipeline** write **`opportunities`** (and related flow); they do **not** populate **`sales`** for this endpoint. **`sales`** are imported by **`python3 -m backend.run_pipeline_full`** (sold listings step — eBay Browse API, see table at top of this doc). On GitHub, that is the **Card Data Pipeline** workflow only. If RDS has old **`sales.sale_date`** values (all older than 30 days), Trending correctly returns **zero rows** even when **Opportunities** is full.

**Operational fix:** Merge the workflow with **daily cron**, or **Run workflow** once on **Card Data Pipeline** for immediate `sales`. Local: `python3 -m backend.run_pipeline_full --sport Baseball --top 20 --skip-scp`.

### Available Workflows
- **Opportunity Pipeline** (`.github/workflows/pipeline.yml`) -- BIN pipeline (`find_opportunities.py`); **scheduled**
- **Auction Pipeline** (`.github/workflows/auction-pipeline.yml`) -- Auction-first pipeline; **scheduled**
- **Card Data Pipeline** (`.github/workflows/card-data-pipeline.yml`) -- `backend.run_pipeline_full` (imports **`sales`**, active listings, trends); **daily cron + manual**
- **Daily Report** (`.github/workflows/daily-report.yml`) -- Operations report
- **QA Pipeline** (`.github/workflows/qa.yml`) -- 167 tests (unit + integration + QA + frontend build)

### Workflow Inputs
- `players`: comma-separated (default: top 40 by volume)
- `max_budget`: default 200
- `min_profit`: default 5
- `min_roi`: default 20
- `min_scp_price`: default 20
- `max_scp_price`: default 1000

### Inspect recent Actions runs (no UI scraping)

Read-only summary of conclusions + failed job steps via the GitHub API:

```bash
cd /path/to/TradingCards
# Option A: GitHub CLI (after: gh auth login)
python3 scripts/summarize_github_actions.py

# Option B: PAT with repo + Actions read
export GITHUB_TOKEN=ghp_...   # or fine-grained: Actions: Read
python3 scripts/summarize_github_actions.py --limit 20

# Only opportunity + auction workflows
python3 scripts/summarize_github_actions.py --workflow pipeline.yml auction-pipeline.yml
```

Default workflows scanned: `pipeline.yml`, `auction-pipeline.yml`, `card-data-pipeline.yml`, `daily-report.yml`. Failures list each job step that ended `failure` so you can open the run URL and expand the right step.

## Common Scenarios

### Resume After Interruption (DNS failure, etc.)
```bash
/usr/bin/python3 -m backend.run_pipeline_full --skip-discovery --sport Baseball --top 40
```
Skips discovery, deduplicates by ebay_item_id so already-imported players are fast.

### Daily Refresh (add new data, keep existing)
```bash
/usr/bin/python3 -m backend.run_pipeline_full --sport Baseball --top 40
```

### Quick Refresh (skip SCP, ~30 min)
```bash
/usr/bin/python3 -m backend.run_pipeline_full --sport Baseball --top 40 --skip-scp
```

### Full Reset (wipe everything, start clean)
```bash
/usr/bin/python3 -m backend.run_pipeline_full --fresh --sport Baseball --top 40
```

## Job Status

```bash
# Check all job statuses via API
curl http://localhost:8000/api/status

# Check specific job
curl http://localhost:8000/api/status/opportunity_finder

# Check via database
sudo -u postgres psql -d trading_cards -c "SELECT job_name, status, started_at, completed_at, items_processed, items_total FROM job_runs ORDER BY started_at DESC LIMIT 10;"
```

## Running Individual Steps

```bash
# 1. Discovery only
/usr/bin/python3 -m backend.discover_players --sport Baseball --limit 40

# 2. Import sold listings only
/usr/bin/python3 -m backend.scrapers.ebay_scraper

# 3. Active listings only
/usr/bin/python3 -m backend.collect_active_listings

# 4. Trends only
/usr/bin/python3 -m backend.calc_trends

# 5. SCP rates only
/usr/bin/python3 -m backend.collect_market_rates --skip-existing
```

## Starting Services

```bash
# PostgreSQL (after WSL restart)
sudo service postgresql start

# API server (port 8000)
cd /home/tweedledee101/TradingCards
nohup /usr/bin/python3 -m backend.api.run > /tmp/api.log 2>&1 &

# Frontend (port 3000)
cd /home/tweedledee101/TradingCards/frontend
nohup npm run dev > /tmp/frontend.log 2>&1 &
```

## Troubleshooting

### DNS failure in WSL (api.ebay.com won't resolve)
- Restart WSL: close all terminals, run `wsl --shutdown` from PowerShell, reopen
- Then restart services (PostgreSQL, API, frontend)
- Resume pipeline with `--skip-discovery`

### eBay API returns 0 results or errors
- Check daily limit: 5,000 calls/day resets at midnight Pacific
- Token expires every 2 hours (auto-refreshes)
- If 401 errors persist: check backend/.env credentials

### SCP scraper fails
- Firefox must run as user `tweedledee101` (not root)
- Auto-detects binary: `/usr/lib/firefox/firefox`, `/usr/bin/firefox-esr`, `/usr/bin/firefox`
- geckodriver at `/usr/local/bin/geckodriver` (v0.36.0)
- Page load timeout (30s) is EXPECTED - data still loads

### Database locked / queries hang
- Kill any running collection scripts first
- `sudo service postgresql restart`

### API server won't start
- `lsof -i :8000` to check, `kill $(pgrep -f 'backend.api.run')` to clear
- Check log: `cat /tmp/api.log`

## Data Flow

### Opportunity Pipeline (PRIMARY)
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
API --> Ragnarok Gaming UI
```

All jobs tracked via `job_runs` table. Check status:
```bash
curl http://localhost:8000/api/status
```

## Database Quick Reference

```bash
# Check counts
sudo -u postgres psql -d trading_cards -c "SELECT
  (SELECT COUNT(*) FROM cards) as cards,
  (SELECT COUNT(*) FROM sales) as sales,
  (SELECT COUNT(*) FROM active_listings) as active,
  (SELECT COUNT(*) FROM market_rates) as rates,
  (SELECT COUNT(*) FROM opportunities) as opportunities,
  (SELECT COUNT(DISTINCT player_name) FROM cards) as players;"

# Check opportunities by type
sudo -u postgres psql -d trading_cards -c "SELECT listing_type, COUNT(*), ROUND(AVG(profit)::numeric, 2) as avg_profit FROM opportunities GROUP BY listing_type;"

# Check flagged opportunities
sudo -u postgres psql -d trading_cards -c "SELECT COUNT(*) as flagged FROM opportunities WHERE flagged = true;"
```

## Running Daily Operations Report

Generates a comprehensive health check covering pipeline status, data freshness, data quality, and action items.

```bash
# Run locally
python3 daily_report.py

# Output goes to stdout + /tmp/daily-report.json
```

The report covers:
- **Pipeline health**: last run times, success/failure status from `job_runs` table
- **Database health**: row counts for all key tables
- **Data freshness**: latest timestamps, stale SCP cache entries, expired auctions
- **Data quality**: null SCP prices, negative profits, duplicate eBay IDs
- **QA flags**: summary of flagged opportunities by rule
- **Opportunity summary**: counts and avg profit by listing type
- **Trends**: 7-day opportunity history
- **Action items**: prioritized as critical/warning/info

Runs automatically at 7PM ET via GitHub Actions (`daily-report.yml`). JSON artifact uploaded for 7 days.

---

## Migrations Applied

| Migration | What |
|-----------|------|
| 001 | Base schema (cards, sales, active_listings, etc.) |
| 002 | PSA grading population |
| 003 | Variant columns + price benchmarks |
| 004 | Accuracy tracking + image_url |
| 005 | Sell-through metrics |
| 006 | Job runs (job tracking) |
| 007 | Error log (observability) |
| 008 | Retention cleanup function |
| 009 | Opportunities table |
| 009b | SCP URL, grade_9, psa_10, image_url on opportunities |
| 010 | listing_type on opportunities (BIN vs auction) |
| 011 | Auction fields (shipping, bid_count, end_time, scp_volume) |
| 012 | QA fields (qa_status, qa_flags, qa_reviewed_at) |
| 013 | SCP cache table (scp_cache with JSONB variants, 24h TTL) |
| 014 | Sold comps table (130point eBay sold data cache) |
| 015 | Price source tracking (scp, sold_comps, ebay_comps) |
| 016 | Scheduled bids table (snipe queue) |
| 017 | Business planner tables (business_goals, daily_snapshots, daily_plans, capital_transactions) |
| 018-023 | Additional schema refinements (see `backend/models/` for details) |

**Migration tracking**: `schema_migrations` table on both local + RDS. 24 migrations applied to both.

```bash
# Check migration status
python3 migrate.py --status --both

# Apply pending migrations to both databases
python3 migrate.py --both

# Apply to one target only
python3 migrate.py --local
python3 migrate.py --rds
```

**Rule**: When you add a new migration file to `backend/models/`, run `python3 migrate.py --both` to keep local and RDS in sync.
