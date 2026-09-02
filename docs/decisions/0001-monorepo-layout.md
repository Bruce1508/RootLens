# ADR-0001: Monorepo layout with apps/web and apps/api

## Status
Accepted

## Context
RootLens needs a Next.js frontend and a FastAPI backend that evolve together
during the MVP. The PRD (§12, §24) calls for one backend service (no
microservices) and clear boundaries between UI, API, investigation domain,
model providers, analytics tools, and persistence.

## Decision
Use a single repository with `apps/web` (Next.js/TypeScript) and `apps/api`
(FastAPI/Python) as sibling directories, plus top-level `data/`, `db/`,
`docs/`, and `scripts/` directories per the PRD's suggested repository
expectations (§24). No package-manager-level workspace tooling (Turborepo,
Nx, uv workspaces) is introduced for the MVP — each app manages its own
dependencies independently, coordinated only through `docker-compose.yml`
and the root `Makefile`.

## Consequences
- Simple to reason about: two independent apps, one Postgres database.
- No cross-app shared package/build tooling to configure or maintain.
- If a shared TypeScript types package or shared Python package becomes
  necessary post-MVP, workspace tooling can be introduced then, not before.
