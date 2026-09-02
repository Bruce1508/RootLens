# RootLens architecture overview (Milestones 0-1)

This document covers only what exists after Milestones 0-1. See
`RootLens_PRD.md` §12-14 for the full target architecture (agent loop,
evidence store, evaluation runner — Milestones 2-6, not built yet).

## Services

```
apps/web   Next.js dashboard (KPI cards, period selectors)
apps/api   FastAPI backend (deterministic analytics endpoints only — no LLM)
postgres   PostgreSQL 16, source-aligned Olist business tables
```

## Database roles (ADR-0004)

- `rootlens_app` — owns the schema. Used by Alembic migrations and the
  ingestion CLI.
- `rootlens_readonly` — `SELECT`-only. Used by every FastAPI query
  endpoint and analytics tool.

## Request flow (Milestone 1)

```
Browser -> apps/web -> GET /api/metrics/summary -> apps/api
                                                       |
                                                       v
                                     app.analytics.compare_periods
                                     (parameterized SQL, rootlens_readonly)
                                                       |
                                                       v
                                                  PostgreSQL
```

No agent, no LLM, no SSE, no evidence store yet — every response is a
deterministic function of the request parameters and the database
contents, per the Milestone 1 exit criteria ("no LLM is required").

## What's intentionally absent

Per the PRD's non-goals (§4.3) and Milestone boundaries (§21), the
following do not exist in this codebase yet: `LLMProvider`/Ollama
integration, the investigation state machine, hypothesis persistence,
the evidence store, SSE trace streaming, incident injection, and the
evaluation runner. Introducing any of these before their milestone is a
scope violation, not progress.
