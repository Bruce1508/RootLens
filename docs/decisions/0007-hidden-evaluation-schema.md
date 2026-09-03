# ADR-0007: Hidden ground truth lives in a Postgres schema, not a separate database

## Status
Accepted

## Context
FR-13 requires ground truth for incident-benchmark scenarios to be "stored
outside the agent-accessible schema," and §14's data model names two hidden
tables, `eval_scenarios` and `eval_ground_truth`, calling for "the agent
database role" to have "no privileges" on them. The PRD's own wording is
schema-scoped ("hidden evaluation schema," singular), not a separate
database or cluster.

## Decision
Add a Postgres schema named `eval` (migration `e042344d6d54`) holding
`eval.eval_scenarios` and `eval.eval_ground_truth`
(`app/models/evaluation.py`). No new database role is created:
ADR-0004's `rootlens_readonly` was granted `SELECT` only via `ALTER DEFAULT
PRIVILEGES IN SCHEMA public`, so it automatically has zero privileges on
`eval` — confirmed by hand:
`psql` as `rootlens_readonly` against `eval.eval_scenarios` returns
`permission denied for schema eval`.

`EvaluationRun` and `EvaluationCaseResult` (the benchmark's *reported*
results, not its answer key) stay in `public` — they're meant to be
inspectable, per PRD §28 ("verify benchmark measurements").

## Consequences
- Zero new grant/role-management code — the hiding falls out of ADR-0004's
  existing default-privilege scoping for free.
- `rootlens_app` (the Postgres bootstrap user configured via `POSTGRES_USER`)
  is effectively a superuser and can still read `eval.*` regardless of
  schema. This is an acknowledged, pre-existing limit of the guardrail
  posture — ADR-0004 already calls `rootlens_readonly` "a coarse guardrail,
  not the full guardrail set" for the same reason. Closing it would require
  running the investigation engine itself under a role with no bypass,
  which is Milestone 6 scope (SQL AST guardrails / read-only role
  enforcement for the agent), not M5's.
- The evaluation runner (`app/evaluation/runner.py`) and the evaluation
  reporting API (`app/api/routes/evaluations.py`) both read `eval.*`
  deliberately, using the write/app session — they are the one legitimate,
  trusted path allowed to see the answer key, analogous to how
  `app.investigations.service.create_investigation` already uses the write
  session rather than a role split.
