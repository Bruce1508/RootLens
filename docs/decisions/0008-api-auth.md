# ADR-0008: Single shared bearer token on mutating investigation routes

## Status
Accepted

## Context
Phase 4 of the 2026-11-05 upgrade plan calls for "a single API key / bearer
token on all mutating routes ... constant-time compare, configured via env.
Unconfigured key means requests are denied (fail closed)." Every
investigation run costs real LLM time (Phase 3 measured 44-51s mean
latency per run), so the create/cancel routes are the ones worth gating —
the GET routes just read already-computed state and cost nothing extra per
request.

## Decision
`app/core/auth.py::require_api_key` is a FastAPI dependency wired onto
`POST /api/investigations` and `POST /api/investigations/{id}/cancel`
only. It reads a single `API_KEY` env var via `Settings.api_key`:
- Unconfigured (`None`/empty) → every request to these routes is denied
  with 403, not let through. Fail closed, not fail open.
- Header missing or not `Bearer <token>` shaped → 401.
- Header present but wrong token → 403.
- Compared with `secrets.compare_digest`, not `==`, to avoid a timing
  side-channel on the token value.

One shared token rather than per-client keys or OAuth: there's exactly one
caller (the Vercel-hosted frontend) and no per-user concept anywhere else
in the system (Investigation rows aren't owned by a user). A full
identity/auth-provider integration would be unrequested scope for what the
plan calls "the minimum credible set."

## Consequences
- GET routes (`/api/investigations`, `/evidence/{id}`, `/events`,
  `/stream`) stay unauthenticated. Acceptable for now since they expose no
  write capability and no secret data beyond the investigation's own
  question/report; revisit if that stops being true.
- Local dev and CI must set `API_KEY` (added to `.env.example` and
  `docker-compose.yml`'s `api` service) or every POST to these two routes
  fails closed, including in tests that don't override the dependency.
- No key rotation or multi-key support — rotating means changing one env
  var and restarting the process. Fine at this scale; would need revisiting
  before a real multi-tenant deployment.
