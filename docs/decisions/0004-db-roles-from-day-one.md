# ADR-0004: Create app and read-only database roles from Milestone 0

## Status
Accepted

## Context
FR-8 requires that "PostgreSQL connection must use a read-only role for
agent execution," but the agent does not exist until Milestone 2/3. The
naive approach is to defer role creation until the agent is built.

## Decision
Create two Postgres roles at first container boot, via
`db/init/001_create_roles.sql` (mounted into
`/docker-entrypoint-initdb.d/`):

- `rootlens_app` — owns the schema; used by Alembic migrations and the
  ingestion CLI (write access).
- `rootlens_readonly` — `GRANT SELECT` only on the business tables; used
  by every FastAPI query endpoint and analytics tool starting in
  Milestone 1, not just once the agent exists.

`apps/api` reads two connection strings from `.env`
(`DATABASE_URL`, `DATABASE_URL_READONLY`) so read paths and write paths
are separated at the connection level from the first working version of
the backend.

## Consequences
- FR-8's least-privilege posture is in place two milestones early, for
  the cost of one SQL file and one extra env var.
- No SQL AST validation is added yet (see ADR-0002) — the readonly role
  is a coarse guardrail, not the full FR-8 guardrail set, which still
  belongs to Milestone 2/3 when the agent gains tool access.
