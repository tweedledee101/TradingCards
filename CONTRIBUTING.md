# Contributing — branches, PRs, risk

## Branching (default)

- **`main`** should stay **deployable**: CI green, no known broken migrations, secrets never committed.
- **New features, refactors, and risky experiments**: use a **feature branch** off current `main`:
  - Name: `feature/short-topic` or `fix/short-topic` (examples: `feature/auction-query-offsets`, `fix/scp-match-year`).
- **Merge via pull request** when the change touches pipelines, schema, auth, scrapers, or anything that could take production down. That gives a diff boundary and CI signal even if you are solo.
- **Tiny doc-only or typo fixes** can go direct to `main` if you prefer—still prefer a branch when unsure.

## GitHub (recommended)

- Turn on **branch protection** for `main`: require PR, require status checks, optional required reviewers.
- Keeps “routing around in code” from landing unreviewed on the line that runs Actions against RDS.

## Commits

- One logical change per commit when practical; message in normal sentences (what + why).
- Run **`python3 -m pytest tests/unit -q`** (or `./run_tests.sh` as you normally do) before pushing risky changes.

## Where things live

See [AGENTS.md](./AGENTS.md) for the code map; [PIPELINE-OPS.md](./PIPELINE-OPS.md) for pipeline commands.

## Testing beyond correctness

Correctness tests are necessary but not sufficient. See [docs/testing/strategy.md](./docs/testing/strategy.md) for **outcome-oriented** checks (funnel coverage, trust metrics) that tie work to Ragnarok’s actual goals.
