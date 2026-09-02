# ADR-0002: Backend stack — FastAPI + SQLAlchemy + Alembic + Pydantic

## Status
Accepted

## Context
The PRD's recommended stack (§12) specifies FastAPI + Python for the
backend, Pydantic for validation, PostgreSQL 16 for storage, SQLAlchemy +
Alembic for ORM/migrations, and sqlglot for later SQL AST validation. The
PRD's implementation guardrails (§25) forbid adding LangChain, LangGraph,
Redis, Celery, Kafka, Kubernetes, or a vector database without a
demonstrated requirement and approval.

## Decision
Adopt the PRD's recommended stack as-is for Milestones 0-1:
- FastAPI for the HTTP API layer.
- Pydantic (v2) / `pydantic-settings` for request/response schemas and
  environment-variable validation.
- SQLAlchemy 2.x declarative models for the Olist business tables.
- Alembic for schema migrations.
- `uv` for Python dependency and environment management (ADR-0003).

`sqlglot` (SQL AST validation for FR-8 guardrails) and any LLM/agent
tooling are explicitly deferred — Milestone 1's analytics tools call
SQLAlchemy directly with parameterized queries and never accept
free-form SQL, so AST validation has nothing to guard yet.

## Consequences
- One backend service, no microservices, matching §12's explicit
  architecture decision.
- Read/write database access is already split by role at the connection
  level (`DATABASE_URL` vs `DATABASE_URL_READONLY`) even before an agent
  exists, so FR-8's least-privilege intent is partially in place early
  (see ADR-0004).
- Adding `sqlglot` and agent-facing guardrails becomes a Milestone 2/3
  concern, not an M0/M1 one.
