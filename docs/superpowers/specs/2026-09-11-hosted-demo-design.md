# Hosted read-only demo — design

**Date:** 2026-09-11
**Status:** Approved, not yet implemented
**Scope:** `apps/web`, plus one new capture script under `scripts/`

## Problem

RootLens is complete and CI-green, but there is nowhere to send someone who
wants to see it. The investigation loop calls a local Ollama model, and no free
hosting tier runs a local LLM, so the running app cannot simply be deployed.

## Audience and constraints

The demo targets recruiters and hiring managers arriving from the portfolio
card. That fixes three constraints:

- **The visit is 60–90 seconds.** Proof must be on screen before any scrolling.
  A free-tier backend that cold-starts for 30–60s is worse than no demo, because
  the visit ends before the page wakes.
- **$0 and zero maintenance.** No server, no database, no API keys, no
  rate-limiting, nothing that rots or can be abused.
- **Read-only.** The visitor lands on a finished investigation and can browse
  the other two. They do not run their own.

Non-goals: live investigations, a question box, a hosted LLM, any always-on
infrastructure. These are not deferred features to design around — they are
excluded.

## Approach

Snapshot-and-serve. Real investigations are run locally, every API response the
UI touches is captured to disk, and the built site resolves requests from those
files instead of the network.

The frontend already funnels all nine API functions through one 20-line helper,
`fetchJson` in `apps/web/lib/api-client.ts:139`. That is the only seam the demo
needs.

### Approaches rejected

- **Point `NEXT_PUBLIC_API_BASE_URL` at static JSON files.** Does not work. Every
  GET carries query parameters (`/api/metrics/summary?current_start=…`) and two
  endpoints are POSTs, so request shapes do not map onto file paths.
- **A separate `/demo` route group** that imports fixtures and passes props to the
  existing components. Leaves `api-client.ts` untouched, but duplicates the
  page-level composition of three routes. The demo and the real pages then drift
  apart silently, which is the failure mode that makes a demo misrepresent the
  product without anyone noticing.
- **Monkeypatching `globalThis.fetch` in demo builds.** Nothing typed changes,
  but failures are invisible and "did the patch apply?" becomes a permanent
  debugging step. No payoff over the chosen approach.

## Components

### 1. Fixture resolver — `apps/web/lib/demo-data.ts` (new)

Maps a request signature to a baked JSON file listed in
`public/demo/manifest.json`. No knowledge of React or of any endpoint's meaning.

**Key format.** `METHOD /path?k=v&k2=v2`, with parameter keys sorted
lexicographically, so callers passing the same parameters in a different order
hit the same fixture. Example:
`GET /api/metrics/summary?comparison_end=…&comparison_start=…&current_end=…&current_start=…`.

**Fixtures are fetched, not bundled.** They live under `public/demo/` and the
resolver requests them by same-origin relative URL (`/demo/<file>.json`). The
alternative — importing them as modules — would inline every evidence row into
the JS bundle and slow the first paint, which is the one thing this audience
cannot afford. A same-origin static JSON request costs single-digit
milliseconds and is cacheable.

The manifest itself is the only fixture bundled with the app, so the resolver
can answer "is this request part of the demo?" without a round trip.

### 2. One branch in `fetchJson` — `apps/web/lib/api-client.ts` (modified)

When `process.env.NEXT_PUBLIC_DEMO_MODE` is set, `fetchJson` delegates to the
resolver instead of building a URL against `API_BASE_URL`. Everything else in
the file — all nine endpoint functions, every exported type — is unchanged.

The resolver still performs a `fetch`, but against a same-origin static file
rather than the API, so the built site has no backend dependency.

The flag is read at build time, so a normal build produces the same bundle it
does today and the demo path is not reachable in it.

### 3. Capture script — `scripts/capture_demo.py` (new)

Runs against a live local stack (Postgres on 5433, Ollama `qwen3:8b`):

1. Creates three investigations over the Olist dataset.
2. Polls each to a terminal status.
3. GETs every endpoint the UI touches for those investigations, plus the
   evaluations list and one evaluation detail.
4. Writes each response to `apps/web/public/demo/` and emits `manifest.json`.

Output is committed. The script is **not** wired into CI: it needs a local model,
and a CI job that cannot run is worse than no job.

Fixtures come from real runs. Hand-authoring the JSON would be faster and would
quietly turn the demo into a mockup — the SQL, rows, and citations on screen must
be what RootLens actually produced.

### 4. Static export route split — `apps/web/app/**` (modified)

All four pages are `"use client"`. Under `output: "export"`, the two dynamic
routes must export `generateStaticParams`, and a client component cannot export
it. Each therefore splits in two:

| Route | Today | After |
| --- | --- | --- |
| `/investigations/[id]` | `page.tsx`, 348 lines, client | server `page.tsx` (params + `generateStaticParams`) + `investigation-view.tsx` (client, the current body) |
| `/evaluations/[id]` | `page.tsx`, 171 lines, client | server `page.tsx` + `evaluation-view.tsx` (client) |

`generateStaticParams` reads the ids from the demo manifest.

This is the largest piece of the work. It is also a structure the app wants
independently of the demo, so it is not throwaway.

### 5. Read-only affordances — `apps/web/app/page.tsx` (modified)

In demo mode the investigate button and date pickers are disabled with a short
inline reason. They are not left live to fail against a backend that is not
there.

A banner names the capture date and states that investigations are pre-run
because the loop needs a local LLM. This follows the project's existing
`publish-honest-metrics` principle: say what the number or the artifact actually
is, rather than letting a visitor infer something more flattering.

### 6. `next.config.ts` (modified)

Sets `output: "export"` only when `NEXT_PUBLIC_DEMO_MODE` is set.

## Data flow

```
capture_demo.py ──> public/demo/*.json + manifest.json   (build-time, manual)
                                  │
browser ──> page ──> api-client fn ──> fetchJson ──> demo-data resolver ──> JSON
                                          │
                                          └─ (normal build) ──> fetch ──> FastAPI
```

## Error handling

A resolver miss — a request the capture script never recorded — throws during
build and in dev, and renders a plain "not part of this demo" message in the
built site.

It must never render an empty panel. An empty panel reads as a product bug in
RootLens itself, which is the opposite of what the demo exists to show.

## Testing

- **Resolver unit tests** in the existing `apps/web/lib/__tests__/api-client.test.ts`:
  hit, miss, and parameter-order independence.
- **One Playwright spec** (`apps/web/e2e/` is already configured) run against the
  *built static export*, asserting that the landing investigation renders and that
  clicking a citation opens the evidence drawer. This is the test that catches
  demo-versus-real drift, because it exercises the same components the live app
  uses.
- Existing suites must stay green: 141 backend tests at ≥91% (the CI gate), 22
  frontend tests.

## Deployment

Vercel, as its own project separate from the portfolio. Static output, free tier,
no cold start. The portfolio's RootLens card links to it.

## Build order

1. Resolver + unit tests (no UI involved, testable in isolation).
2. `fetchJson` branch.
3. Capture script; produce real fixtures.
4. Route split for the two dynamic routes.
5. Demo affordances and banner.
6. Playwright spec against the built export.
7. Deploy; link from the portfolio card.

Step 4 is the long pole. Steps 1–3 are independently verifiable before any page
is touched.
