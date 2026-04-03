# Agent context — TradingCards (Ragnarok Gaming)

Use this file to orient quickly. The repo is large; follow the links instead of inferring from folder names alone.

## What this is

Data-driven **trading card arbitrage** platform: SCP-first BIN pipeline + eBay-first auction pipeline, PostgreSQL, FastAPI (`:8000`), React/Vite (`:3000`). Domain target: **ragnarokgamez.com**. RDS is the usual production DB; local Postgres stays in sync via `migrate.py`.

## Read first (human + agent)

| Priority | File | Why |
|----------|------|-----|
| 1 | [STATUS.md](./STATUS.md) | Current reality: what works, what’s broken, session changelog |
| 2 | [docs/README.md](./docs/README.md) | Index to all architecture and ADRs |
| 3 | [.amazonq/rules/memory-bank/](./.amazonq/rules/memory-bank/) | `product.md`, `structure.md`, `tech.md`, `guidelines.md` — dense product + layout |
| 4 | [PIPELINE-OPS.md](./PIPELINE-OPS.md) | Commands, flags, GitHub Actions, troubleshooting |

Deep dives: [docs/architecture/system-architecture.md](./docs/architecture/system-architecture.md), [database-design.md](./docs/architecture/database-design.md), [diagrams/data-flow.md](./docs/architecture/diagrams/data-flow.md), [docs/setup/installation.md](./docs/setup/installation.md).

## Where code lives

| Area | Path |
|------|------|
| API app + route registration | `backend/api/main.py`, `backend/api/routes/` |
| Business planner (goals, plans, capital) | `backend/services/business_planner.py`, `backend/api/routes/business.py` |
| Auth (in progress; check git) | `backend/api/routes/auth.py`, `backend/utils/auth.py`, `backend/models/migration_018_auth_multi_tenant.sql`, `aws/cloudformation/cognito-auth.yaml` |
| Scrapers / eBay / SCP | `backend/scrapers/`, `backend/utils/token_manager.py` |
| DB schema + migrations | `backend/models/schema.sql`, `backend/models/migration_*.sql`, ORM in `backend/models/__init__.py` |
| Config | `backend/config/settings.py`, `config/targets.yaml` |
| Frontend | `frontend/src/` — API client `frontend/src/api/client.js`; pages in `frontend/src/pages/` |
| Pipelines (repo root) | `find_opportunities.py`, `find_auction_opportunities.py`, `worm_130point.py`, `daily_report.py`, `migrate.py` |
| GitHub Actions summary (CLI) | `scripts/summarize_github_actions.py` — recent run conclusions + failed steps (`gh auth login` or `GITHUB_TOKEN`); see `PIPELINE-OPS.md` |
| Auction funnel audit (RDS) | `scripts/audit_auction_pipeline.py` — `opportunities` auction counts + `job_runs` funnel JSON + `error_log`; see `PIPELINE-OPS.md` |
| Full data pipeline | `backend/run_pipeline_full.py` |
| Tests | `tests/unit`, `tests/integration`, `tests/qa` |
| CI | `.github/workflows/` (BIN, auction, daily report, QA) |
| AWS IaC | `aws/cloudformation/` (RDS, eBay compliance, Cognito auth, **frontend SPA**), `aws/README.md` |

## Conventions

- **PostgreSQL (local):** use `sudo -u postgres psql -d trading_cards` (peer auth). See `.amazonq/rules/database-access.md`.
- **Migrations:** add SQL under `backend/models/`, then `python3 migrate.py --both` to align local + RDS.
- **Opportunity flow:** BIN pipeline may subprocess the auction pipeline; QA runs after and does not block ingestion.

## ADRs (decisions)

- **ADR-004** — Demand-driven refresh (no clock-based data crons; pipeline scheduling via Actions is separate).
- **ADR-005** — User model, personalization, per-user opportunity scoping (planned evolution).
- **ADR-006** — Business Operating System / planner (implemented per STATUS/ROADMAP).

Full list: [docs/architecture/decisions/](./docs/architecture/decisions/).

## When editing docs

Prefer updating **existing** `STATUS.md` / `README.md` / roadmap files rather than spawning dated duplicates. See `.amazonq/rules/documentation-updates.md`.

### Architecture and diagrams (agent + human)

On **meaningful** changes (new behavior, schema/API, pipelines, CI, infra, auth, data flow), keep docs accurate **without being asked**: patch the smallest set of existing files — `STATUS.md`, `docs/architecture/*` (including `diagrams/data-flow.md` when flows change), `PIPELINE-OPS.md`, `README.md` / `docs/ROADMAP.md` / ADRs as appropriate, memory-bank when product or layout drifts, and this file if the map is wrong.

Before **creating** any new doc: one quick check — *does an existing file already own this topic?* Default to extending it. New docs only when the topic is clearly separate and long-lived.

Keep updates and chat summaries **streamlined**: say what changed; skip process narration unless it avoids confusion.

Cursor encodes the same expectations in `.cursor/rules/docs-and-architecture.mdc` (always on).
