# ADR-0006: Prompt/version registry lives in versioned Python code

## Status
Accepted

## Context
The PRD (§25.11) requires that prompts, tool schemas, and metric
definitions be kept versioned. Milestone 2 introduces the first prompt
(`decomposition_planner`, used by the `LLMProvider` to request a
structured `DecompositionPlan` from the local model). Options considered:
a database table (`prompt_registry`), YAML config files, or plain Python
modules — the same three options weighed for the metric catalog in
ADR-0005.

## Decision
The prompt registry mirrors ADR-0005's structure exactly: plain,
versioned Python code under `apps/api/app/prompts/definitions/` (e.g.
`decomposition_planner_v1.py`), registered in
`apps/api/app/prompts/catalog.py`. No database table and no YAML parsing
layer is introduced yet.

A DB-backed `prompt_registry` table is deferred until Milestone 3, when
investigations need to persist *which* prompt version produced a given
plan or report — the same trigger condition ADR-0005 defined for metric
definitions, and it has not yet occurred for prompts either.

## Consequences
- Prompt templates are unit-testable in isolation, independent of the
  database, consistent with the metric-catalog pattern.
- Still fully version-controlled via git history on the Python module.
- Milestone 3 will need a migration to add `prompt_registry` once
  investigations reference a specific prompt version — tracked as a
  known, intentional gap, not an oversight, mirroring the same gap
  already tracked for `metric_definitions` in ADR-0005.
