# Dev environment + pipeline cutover (same platform, different flow)

**Intent:** Keep **ragnarokgamez.com** stack (SPA, Lambda API, Cognito, RDS, worms, CE tooling). Change **only the order and sources** of pipeline steps so **eBay Browse is used for tight card/listing queries**, not player discovery or wide auction nets. Add a **dev front door** to experiment without trashing production rows or burning prod-only assumptions.

---

## 1. Canonical card list (you don’t have to pick one forever)

**Default recommendation for implementation:** **hybrid**

| Source | Role |
|--------|------|
| **Ranked player names** | From **`sold_comps` / `sales`** (130point worm + card pipeline) — **not** Browse seed totals. |
| **Card identities + SCP book + volume text** | **SCP player catalog** per ranked player (what BIN already does well). |
| **`cards` / `market_rates`** | Accelerate when identity already exists; **fill gaps** when SCP crawl is skipped for a player. |

**Title variants on eBay:** start with **2–4 strings per variation** (strict + loose). **Raise** variant count only when **opportunity yield** or **recall** is low in dev metrics — not a fixed global number.

### Implemented dev-oriented pipeline flags (code)

- **`--player-rank-source sales`**: top players = **`GROUP BY` player on `sales`** (joined to `cards`) in **`--sales-rank-days`** (default **7**), ordered by **count** — no Browse for that step. Use **`--top-players`** to raise above 100 when needed.
- **`--dev-strict-listings`**: tighter **text** match (all parallel tokens; majority of long set-name tokens in title).
- **`--dev-reconcile-scp-comps`**: before eBay, **`backend/services/scp_sold_comps_reconcile.py`** adjusts each variation’s reference **`price`** using **`sold_comps`** median (with optional **parallel** filter on comps). Stored row: **`price_source=reconciled`**, **`verification_detail.pre_ebay_reconciliation`**, **`scp_price_raw`** when blended.
- **`--dev-vision-queue-pass`** / **`--dev-vision-queue-max`**: fills **`vision_post_pipeline_queue_sample`** with **`dev_identity_listing_queue`** entries (images + title) for **post-pipeline** multimodal / CE — **does not block ingest** (same contract as existing flagged-BIN vision sampling).

---

## 2. Dev replica: `dev.ragnarokgamez.com`

### 2.1 Same code, different hostnames

- **`https://dev.ragnarokgamez.com`** — **implemented in repo:** `aws/cloudformation/frontend-spa-dev.yaml` + `./aws/deploy-frontend-dev.sh`. Build: **`cd frontend && npm run build:dev`** (`frontend/.env.dev` sets **`VITE_API_URL`**; default **`https://dev-api.ragnarokgamez.com`**). Sync to the **dev** bucket from stack outputs; invalidate **dev** CloudFront.
- **`https://dev-api.ragnarokgamez.com`** — **in repo:** `aws/cloudformation/api-lambda-http-dev.yaml` + **`./aws/deploy-api-lambda-dev.sh`** (Lambda env **`DATABASE_URL`** = **`DATABASE_URL_DEV`**). **Same routes** as prod. Cognito: callback **`https://dev.ragnarokgamez.com/auth/callback`**.

### 2.2 Database: same RDS vs “dev tables”

**Recommended:** **second database on the same RDS instance**, e.g. `trading_cards_dev`, **same migrations**. With **`DATABASE_URL`** pointed at that instance, **`python3 migrate.py --dev`** derives **`…/trading_cards_dev`**, **`CREATE DATABASE`** if your role allows, then migrates. Optional explicit **`DATABASE_URL_DEV`** in `backend/.env`.

```bash
python3 migrate.py --dev
python3 migrate.py --all-db    # local + prod DATABASE_URL + dev (when all three are used)
```

| Approach | Pros | Cons |
|----------|------|------|
| **Separate DB** (`trading_cards_dev`) | Clean ORM, no `environment` column on every row, easy wipe | Second DB to create/backup |
| **`environment` column** on `opportunities`, `job_runs`, … | One DB | Every query must filter; easy to leak dev rows into prod UI |
| **Duplicate tables** `dev_opportunities` | — | ORM/migrations pain |

**Shared read-only data** (optional): you can keep **`sold_comps`**, **`cards`**, **`sales`** in **prod DB** and have dev pipeline **read** prod for comps while **writing** opportunities to **dev DB** — only if you accept cross-DB or replicate comps into dev. Simpler v1: **clone or run worms against dev** so dev is self-contained.

### 2.3 Cognito

- **Same user pool**, **second app client** for dev callback URLs (`https://dev.ragnarokgamez.com/auth/callback`), **or** separate test pool — either works; second app client is usually enough.

### 2.4 eBay keys

- **Same app id** → dev + prod runs **share** Browse quota → bad for your stated pain. **Better:** separate eBay **sandbox** or **second production keyset** for dev Actions if policy allows.

---

## 3. Migration path: pipeline behavior (order of work)

**Principle:** each step is **shippable**, **measurable**, and **reversible** with a flag.

| Phase | Change | Success signal |
|-------|--------|----------------|
| **0** | Dev infra live (dev UI + dev API + `trading_cards_dev`) | Sign-in, health, empty opportunities |
| **1** | **Player rank from `sold_comps`/`sales`**, Browse discovery behind flag or fallback only | **Browse calls/run** down; player list non-empty |
| **2** | **Auction Step 1:** card-driven queries only (reuse BIN-style variation list or shared builder) | Auction **Browse calls** down; opportunities **quality** ≥ baseline |
| **3** | **Adaptive title variants** per card (cap + metrics) | Recall up without quota explosion |
| **4** | **Optional:** CE/vision gate before “final” opportunity row (stricter than today) | `verification_status` / QA disagreement rate improves |
| **5** | **Prod cutover:** flip flags, run shadow period | Dev vs prod KPIs match or beat |

**Last things to change:** DNS defaults for **end users** (point everyone at new flow only when KPIs hold) and **removal** of old auction query matrix after burn-in.

---

## 4. Effectiveness testing (no spoon-fed rows)

Run **both** flows on a schedule **into dev** (or run old prod + new dev in parallel):

| Metric | Where |
|--------|--------|
| Browse **GET** count / run | `job_runs.results_summary`, logs |
| Rows written | `opportunities` count / day |
| Economics | median **`profit`**, **`roi`** |
| Trust | **`verification_status`**, **`qa_flags`**, post-ingest verification scripts |
| Capital narrative | **`inventory`** + **`days_held`** on sales |

**Bar:** new flow **≥** old on trust + economics, **strictly better** on Browse usage, before prod is default.

---

## 5. What this doc does **not** decide yet

- Exact **subdomain** strings (dev-api vs api-dev) — pick with ACM cert SANs.
- Whether **sold_comps** stays prod-read-only for dev or is **copied** — ops choice.
- **eBay** second keyset approval — your developer account constraints.

Edit this file as decisions land; link from **`aws/README.md`** and **`PIPELINE-OPS.md`** when stacks exist.
