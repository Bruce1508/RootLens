# RootLens

A local-first AI business analyst that investigates *why* a business metric
changed — not just that it changed. See [`RootLens_PRD.md`](RootLens_PRD.md)
for the full product requirements document.

**Status:** Milestones 0–6 complete — ingestion, a bounded investigation
loop backed by a local Ollama model, evidence-backed and citation-verified
reports, a 35-scenario incident benchmark with hidden ground truth, SQL
AST guardrails around the agent's one escape-valve tool, and a read-only
database role enforced for every analytics query the engine makes. See
[`docs/architecture/overview.md`](docs/architecture/overview.md) for how
it fits together, and [`docs/performance.md`](docs/performance.md) for
real, locally-measured latency numbers.

## Screenshots

| Dashboard | Investigation | Evaluation |
|---|---|---|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Investigation](docs/screenshots/investigation.png) | ![Evaluation](docs/screenshots/evaluation.png) |

## Prerequisites

- Docker + Docker Compose
- [`uv`](https://docs.astral.sh/uv/) (Python dependency management)
- Node.js 20+
- [Ollama](https://ollama.com), running locally with a model pulled (e.g.
  `ollama pull qwen3:8b`) — required for investigations and the
  evaluation runner; the dashboard alone doesn't need it
- A Kaggle account, only if you want the full dataset instead of the
  committed fixtures (see `data/README.md`)

## Quickstart

```bash
make setup      # copies .env.example -> .env, installs backend + frontend deps
make up         # starts postgres, api, web via Docker Compose
make migrate    # applies Alembic migrations
make ingest-fixtures   # loads the small golden fixture dataset (no Kaggle account needed)
make demo       # creates one real investigation and prints its URL
```

Then visit http://localhost:3000 for the dashboard, or
http://localhost:8000/api/health for the backend health check.

To use the full Olist dataset instead of fixtures (needed for the
incident benchmark — see below), follow `data/README.md`, then run
`make ingest SOURCE=data/raw`.

## Running the incident benchmark

The 35 scenarios (cancellation spikes, order-volume declines,
seller/category declines, and unanswerable questions) are grounded in the
real dataset's volume, not the small fixtures:

```bash
make ingest SOURCE=data/raw   # the real dataset must be loaded first
make eval-seed                # loads the code-defined scenarios + hidden ground truth
make eval-run                 # runs the held-out split, scores it, writes docs/evaluation/results/
```

Results are visible at http://localhost:3000/evaluations once a run
completes. This is a real local benchmark, not a fixed demo — its
measured accuracy will vary with the model and hardware you run it on;
see `docs/performance.md` for what was actually observed here.

## Commands

| Command | What it does |
|---|---|
| `make setup` | Install backend (`uv sync`) and frontend (`npm install`) dependencies |
| `make up` / `make down` | Start / stop the Docker Compose stack |
| `make migrate` | Apply Alembic migrations |
| `make ingest-fixtures` | Load the committed golden fixture dataset |
| `make ingest SOURCE=data/raw` | Load the full Olist dataset (requires manual download) |
| `make db-reset` | Dev-only: truncate and reload fixtures |
| `make demo` | Create one real investigation and print its URL |
| `make eval-seed` / `make eval-run` / `make eval` | Seed and run the incident benchmark |
| `make test` | Run backend (pytest) and frontend (Vitest) tests |
| `make test-e2e` | Run frontend end-to-end tests (Playwright, mocked API) |
| `make lint` / `make format` / `make typecheck` | Quality gates for both apps |

## Repository layout

```
apps/web/    Next.js dashboard, investigation workspace, evaluation UI
apps/api/    FastAPI backend — models, migrations, ingestion, analytics,
             investigation engine, evaluation runner
data/        Dataset docs, gitignored raw data, committed test fixtures
db/init/     Postgres role bootstrap (runs once, on first container start)
docs/        Architecture notes, ADRs, performance notes, screenshots
scripts/     demo.sh — the Milestone 6 demo entrypoint
```

## Architecture decisions

See [`docs/decisions/`](docs/decisions/) for the reasoning behind key
choices: monorepo layout, backend stack, Python tooling, database role
strategy, the metric/prompt-catalog format, and the hidden evaluation
schema.

## Known limitations

Recorded here deliberately, not left implicit:

- **The investigation loop is a bounded script, not a fully adaptive
  agent loop.** Three fixed analytics calls feed one decomposition
  decision; the LLM only gets a genuinely open-ended choice (the ad hoc
  `run_safe_sql` step) when the standard path leaves a hypothesis
  inconclusive. This was a deliberate scope choice (PRD §6: "deterministic
  business logic where possible"), not an oversight.
- **Local LLM latency is highly variable**, not proportional to query
  complexity — the same investigation took ~28s in one run and hit the
  120s per-call timeout in another. See `docs/performance.md`.
- **A benchmark scenario targeting a low-volume dimension can be swamped
  by real background variance.** One held-out scenario (a small state)
  showed the *opposite* of its expected direction, because the injected
  incident was small relative to natural month-to-month noise in the
  other 90%+ of the dataset. This is a real, measured limitation of
  scoring against an aggregated top-level metric, not a bug — surfaced
  during Milestone 5, not smoothed over.
- **`rootlens_app` (the Postgres bootstrap role) can still read the
  hidden `eval` schema** despite the schema-level hiding (ADR-0007) —
  it's effectively a superuser. The guardrail is that no application code
  path the investigation engine can reach ever queries it, not a
  database-level wall against every possible role.
- **Evaluation runs are not parallelized** — 35 scenarios run
  sequentially, each provisioning and tearing down its own schema. Not a
  problem at this scale; would need revisiting at materially larger
  scenario counts.

## A note on measured vs. planned results

Any accuracy, latency, or benchmark numbers in this README or
`docs/performance.md` are only ever reported after being actually
measured (the evaluation runner, or direct local timing). Nothing here is
a target dressed up as an achieved result.
