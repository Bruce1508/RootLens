# ADR-0003: Python dependency management with uv

## Status
Accepted

## Context
The developer machine has an ambient interpreter mismatch: `python3`
resolves to 3.13.7 but `pip` reports site-packages under Python 3.14.
Relying on ambient `pip`/`venv` state risks silently drifting per-machine
environments. `uv` (0.10.11) is already installed locally; `poetry` is not.

## Decision
Use `uv` for all Python environment and dependency management in
`apps/api`: `uv init`/`uv add` for `pyproject.toml` + `uv.lock`, `uv sync`
to materialize `.venv`, and `uv run <cmd>` for every Python invocation
(pytest, alembic, uvicorn, the ingestion CLI). Pin the interpreter with
`uv python pin` so `uv run` never depends on whatever `python3` happens to
resolve to on a given machine.

## Consequences
- One lockfile (`uv.lock`), reproducible installs across machines.
- All documented commands go through `uv run ...` — never bare `python`
  or `pip`.
- No Poetry, no manual `venv activate` steps in documentation.
