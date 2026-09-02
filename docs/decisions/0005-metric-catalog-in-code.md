# ADR-0005: Semantic metric catalog lives in versioned Python code

## Status
Accepted

## Context
The PRD (§10, FR-2) requires that metric definitions be "version-controlled"
and never live only in prompt text. Options considered: a database table
(`metric_definitions`, listed as an application table in §14), YAML config
files, or plain Python modules.

## Decision
For Milestones 0-1, the semantic catalog is plain, versioned Python code
under `apps/api/app/metrics/definitions/` (e.g. `product_revenue_v1.py`),
registered in `apps/api/app/metrics/catalog.py`. No database table and no
YAML parsing layer is introduced yet.

A DB-backed `metric_definitions` table is deferred until Milestone 3, when
investigations need to persist *which* metric version produced a given
report (`metric_definition_version` in the investigation state, §13.1) —
that is the first point a runtime record of "which version was used"
is actually needed.

## Consequences
- Metric formulas are unit-testable in isolation, independent of the
  database (satisfies the PRD principle "deterministic business logic
  belongs in tested tools, not prompts").
- Still fully version-controlled via git history on the Python module.
- Milestone 3 will need a migration to add `metric_definitions` once
  investigations reference a specific version — tracked as a known,
  intentional gap, not an oversight.
