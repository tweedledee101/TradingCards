# Documentation Index

## Project Root
- [README.md](../README.md) - Project overview, quick start, features
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Branching, PRs, when not to commit straight to main
- [STATUS.md](../STATUS.md) - Current project status and database state
- [PIPELINE-OPS.md](../PIPELINE-OPS.md) - Pipeline commands, flags, troubleshooting
- [ROADMAP.md](./ROADMAP.md) - Milestones and backlog (including future brand/content ideas)

## How Things Work
- [OPPORTUNITY-FINDER.md](./OPPORTUNITY-FINDER.md) - Product concept; **canonical pipeline intent** (operator agreement) at top; see `PIPELINE-OPS` + live API for current behavior
- [KNOWN-ISSUES.md](./KNOWN-ISSUES.md) - Documented false positive patterns and pipeline bugs
- [research-and-practice-notes.md](./research-and-practice-notes.md) - Literature + flipper teachings → hypotheses, code mapping, experiments

## Architecture
- [system-architecture.md](./architecture/system-architecture.md) - System design and component overview
- [database-design.md](./architecture/database-design.md) - Schema, ERD, table descriptions
- [data-flow.md](./architecture/diagrams/data-flow.md) - Pipeline + post-pipeline vision flow (ASCII diagrams)

## Architecture Decision Records
- [ADR-001](./architecture/decisions/ADR-001-postgresql-database.md) - Why PostgreSQL
- [ADR-002](./architecture/decisions/ADR-002-ebay-primary-source.md) - Why eBay as primary source
- [ADR-003](./architecture/decisions/ADR-003-testing-strategy.md) - Testing strategy (pytest)
- [ADR-004](./architecture/decisions/ADR-004-demand-driven-refresh.md) - Demand-driven refresh (GitHub Actions schedule is ops-level; no in-app clock SCP crons)
- [ADR-005](./architecture/decisions/ADR-005-user-model.md) - User model, personalization, opportunity scoping
- [ADR-006](./architecture/decisions/ADR-006-business-planner.md) - Business Operating System / planner
- [ADR-007](./architecture/decisions/ADR-007-public-surfaces-vs-admin-and-commerce.md) - Public storefront vs admin-only tooling; future Stripe/Plaid, breaks, calendar

## Setup
- [installation.md](./setup/installation.md) - Development environment setup

## Testing
- [testing/strategy.md](./testing/strategy.md) - Correctness vs pipeline health vs outcome/trust metrics

## Component READMEs
- [frontend/README.md](../frontend/README.md) - Frontend setup and tech stack
- [aws/README.md](../aws/README.md) - AWS infrastructure (eBay compliance Lambda)
- [acquisition/facebook_marketplace/README.md](../acquisition/facebook_marketplace/README.md) - NovaAct integration
