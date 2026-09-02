# RootLens

A local-first AI business analyst that investigates *why* a business metric
changed — not just that it changed. See [`RootLens_PRD.md`](RootLens_PRD.md)
for the full product requirements document.

**Status:** Milestones 0-1 (repository foundation, data ingestion,
deterministic analytics). No LLM/agent integration exists yet — that starts
at Milestone 2. See [`docs/architecture/overview.md`](docs/architecture/overview.md).

## Prerequisites

- Docker + Docker Compose
- [`uv`](https://docs.astral.sh/uv/) (Python dependency management)
- Node.js 20+
- A Kaggle account (to download the Olist dataset — see `data/README.md`)

## Quickstart

```bash
make setup      # copies .env.example -> .env, installs backend + frontend deps
make up         # starts postgres, api, web via Docker Compose
make migrate    # applies Alembic migrations
make ingest-fixtures   # loads the small golden fixture dataset (no Kaggle account needed)
```

Then visit http://localhost:3000 for the dashboard, or
http://localhost:8000/api/health for the backend health check.

To use the full Olist dataset instead of fixtures, follow
`data/README.md`, then run `make ingest SOURCE=data/raw`.

## Commands

| Command | What it does |
|---|---|
| `make setup` | Install backend (`uv sync`) and frontend (`npm install`) dependencies |
| `make up` / `make down` | Start / stop the Docker Compose stack |
| `make migrate` | Apply Alembic migrations |
| `make ingest-fixtures` | Load the committed golden fixture dataset |
| `make ingest SOURCE=data/raw` | Load the full Olist dataset (requires manual download) |
| `make db-reset` | Dev-only: truncate and reload fixtures |
| `make test` | Run backend (pytest) and frontend (Vitest) tests |
| `make lint` / `make format` / `make typecheck` | Quality gates for both apps |

## Repository layout

```
apps/web/    Next.js dashboard
apps/api/    FastAPI backend — models, migrations, ingestion, analytics tools
data/        Dataset docs, gitignored raw data, committed test fixtures
db/init/     Postgres role bootstrap (runs once, on first container start)
docs/        Architecture notes and ADRs
scripts/     One-off setup scripts
```

## Architecture decisions

See [`docs/decisions/`](docs/decisions/) for the reasoning behind key
choices: monorepo layout, backend stack, Python tooling, database role
strategy, and the metric catalog format.

## A note on measured vs. planned results

Any accuracy, latency, or benchmark numbers in this README are only ever
reported after the evaluation runner (Milestone 5) actually measures them.
Nothing here is a target dressed up as an achieved result.
