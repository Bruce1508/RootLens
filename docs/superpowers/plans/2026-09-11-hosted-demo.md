# Hosted Read-Only Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy a $0, zero-maintenance, read-only demo of RootLens by capturing real
investigation runs to disk and serving them through a static export, so a recruiter
landing from the portfolio card sees a real, finished investigation with working
citations in under 5 seconds.

**Architecture:** All frontend API calls already funnel through one function,
`fetchJson` in `apps/web/lib/api-client.ts`. In demo builds
(`NEXT_PUBLIC_DEMO_MODE=1`), that function delegates to a new fixture resolver
that fetches baked JSON from `public/demo/` instead of the network. A Python
capture script populates those fixtures from a real local run. The two dynamic
routes (`/investigations/[id]`, `/evaluations/[id]`) split into a thin server
`page.tsx` (for `generateStaticParams`) plus the existing client component,
because `output: "export"` requires static params and a `"use client"` page
cannot export them.

**Tech Stack:** Next.js 15 (App Router, static export), TypeScript, Vitest,
Playwright, Python 3 stdlib (capture script), Vercel (hosting).

**Spec:** `docs/superpowers/specs/2026-09-11-hosted-demo-design.md`

## Global Constraints

- **$0 hosting, zero ongoing maintenance.** Static export only — no server, no
  database, no API keys in the deployed demo.
- **Read-only.** The investigate button and date pickers are disabled in demo
  mode, not left live against a backend that doesn't exist.
- **Fixtures come from real local runs, never hand-authored JSON.** The SQL,
  rows, and citations shown must be what RootLens actually produced.
- **A visible banner names the capture date and the reason** (the loop needs a
  local LLM, so this replays real runs instead of computing new ones).
- **The capture script is not wired into CI** — it needs a local Ollama model,
  and a CI job that cannot run is worse than no job.
- **Existing suites must stay green throughout:** 141 backend tests at the
  `--cov-fail-under=91` gate, 22 frontend tests, `npm run typecheck`, `npm run
  lint`.
- **A resolver miss must fail loudly**, never render an empty panel — an empty
  panel reads as a bug in RootLens itself.

---

### Task 1: Demo fixture resolver

**Files:**
- Create: `apps/web/lib/demo-data.ts`
- Test: `apps/web/lib/__tests__/demo-data.test.ts`

**Interfaces:**
- Produces: `buildDemoKey(method: string, path: string, params?: Record<string, string>): string`
  and `resolveDemoFixture<T>(method: string, path: string, params?: Record<string, string>): Promise<T>`
  — both exported from `apps/web/lib/demo-data.ts`. Task 2 imports
  `resolveDemoFixture` from here. Task 3's capture script must build manifest
  keys with the exact same rule as `buildDemoKey`: `"${method} ${path}"` with no
  params, or `"${method} ${path}?${sortedParams.join("&")}"` where params are
  sorted lexicographically by key and joined as `key=value`.

- [ ] **Step 1: Write the failing tests**

```typescript
// apps/web/lib/__tests__/demo-data.test.ts
import { afterEach, describe, expect, it, vi } from "vitest";
import { buildDemoKey, resolveDemoFixture } from "@/lib/demo-data";

describe("buildDemoKey", () => {
  it("returns a plain method-and-path key when there are no params", () => {
    expect(buildDemoKey("GET", "/api/investigations")).toBe("GET /api/investigations");
  });

  it("sorts params so callers passing them in a different order collide on the same key", () => {
    const a = buildDemoKey("GET", "/api/metrics/summary", {
      current_start: "2018-01-01",
      comparison_start: "2017-12-01",
    });
    const b = buildDemoKey("GET", "/api/metrics/summary", {
      comparison_start: "2017-12-01",
      current_start: "2018-01-01",
    });
    expect(a).toBe(b);
    expect(a).toBe(
      "GET /api/metrics/summary?comparison_start=2017-12-01&current_start=2018-01-01",
    );
  });
});

describe("resolveDemoFixture", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches the manifest, then the matching fixture file", async () => {
    const manifest = [{ key: "GET /api/investigations", file: "investigations-list.json" }];
    const fixture = [{ investigation_id: "inv-1", status: "completed" }];

    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url === "/demo/manifest.json") {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(manifest) });
        }
        if (url === "/demo/investigations-list.json") {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(fixture) });
        }
        throw new Error(`unexpected fetch: ${url}`);
      }),
    );

    const result = await resolveDemoFixture("GET", "/api/investigations");
    expect(result).toEqual(fixture);
  });

  it("throws when no manifest entry matches the request", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve([]) }),
    );

    await expect(resolveDemoFixture("GET", "/api/investigations")).rejects.toThrow(
      "Demo fixture not found for GET /api/investigations",
    );
  });

  it("throws when the manifest itself fails to load", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));

    await expect(resolveDemoFixture("GET", "/api/investigations")).rejects.toThrow(
      "Failed to load /demo/manifest.json: 500",
    );
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd apps/web && npx vitest run lib/__tests__/demo-data.test.ts`
Expected: FAIL — `Cannot find module '@/lib/demo-data'` (the file doesn't exist yet).

- [ ] **Step 3: Write the resolver**

```typescript
// apps/web/lib/demo-data.ts

interface DemoManifestEntry {
  key: string;
  file: string;
}

export function buildDemoKey(
  method: string,
  path: string,
  params?: Record<string, string>,
): string {
  if (!params || Object.keys(params).length === 0) {
    return `${method} ${path}`;
  }
  const query = Object.keys(params)
    .sort()
    .map((key) => `${key}=${params[key]}`)
    .join("&");
  return `${method} ${path}?${query}`;
}

async function fetchDemoJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load ${url}: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function resolveDemoFixture<T>(
  method: string,
  path: string,
  params?: Record<string, string>,
): Promise<T> {
  const key = buildDemoKey(method, path, params);
  const manifest = await fetchDemoJson<DemoManifestEntry[]>("/demo/manifest.json");
  const entry = manifest.find((item) => item.key === key);
  if (!entry) {
    throw new Error(`Demo fixture not found for ${key}`);
  }
  return fetchDemoJson<T>(`/demo/${entry.file}`);
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd apps/web && npx vitest run lib/__tests__/demo-data.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add apps/web/lib/demo-data.ts apps/web/lib/__tests__/demo-data.test.ts
git commit -m "feat(web): add the demo fixture resolver"
```

---

### Task 2: Wire the resolver into `fetchJson`, gate the build

**Files:**
- Modify: `apps/web/lib/api-client.ts:139-156` (the `fetchJson` function)
- Modify: `apps/web/lib/__tests__/api-client.test.ts` (imports + one new `describe` block)
- Modify: `apps/web/next.config.ts`
- Modify: `apps/web/package.json` (`scripts`)

**Interfaces:**
- Consumes: `resolveDemoFixture` from Task 1 (`apps/web/lib/demo-data.ts`).
- Produces: `NEXT_PUBLIC_DEMO_MODE` as the build-time flag every later task
  reads (`process.env.NEXT_PUBLIC_DEMO_MODE`), and the `npm run build:demo`
  script Task 4, 6, and 7 all invoke to produce the static export.

- [ ] **Step 1: Write the failing test**

Add `getInvestigations` to the existing import block at the top of
`apps/web/lib/__tests__/api-client.test.ts`:

```typescript
import {
  cancelInvestigation,
  getEvaluation,
  getEvaluations,
  getEvidence,
  getInvestigation,
  getInvestigationEvents,
  getInvestigations,
  getMetricsSummary,
} from "@/lib/api-client";
```

Append this block at the end of the file:

```typescript
describe("fetchJson in demo mode", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    delete process.env.NEXT_PUBLIC_DEMO_MODE;
  });

  it("resolves from the demo fixture manifest instead of calling the real API", async () => {
    process.env.NEXT_PUBLIC_DEMO_MODE = "1";
    const manifest = [{ key: "GET /api/investigations", file: "investigations-list.json" }];
    const fixture = [{ investigation_id: "inv-1", status: "completed" }];

    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url === "/demo/manifest.json") {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(manifest) });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve(fixture) });
      }),
    );

    const result = await getInvestigations();
    expect(result).toEqual(fixture);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd apps/web && npx vitest run lib/__tests__/api-client.test.ts`
Expected: FAIL — the demo-mode test receives `undefined` (or throws on the
`API_BASE_URL`-constructed URL), because `fetchJson` doesn't check the flag yet.

- [ ] **Step 3: Add the branch to `fetchJson`**

In `apps/web/lib/api-client.ts`, add the import near the top:

```typescript
import { resolveDemoFixture } from "@/lib/demo-data";
```

Then at the start of the `fetchJson` function body (immediately after the
opening `{`, before `const url = new URL(...)`):

```typescript
  if (process.env.NEXT_PUBLIC_DEMO_MODE) {
    return resolveDemoFixture<T>(init?.method ?? "GET", path, params);
  }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd apps/web && npx vitest run lib/__tests__/api-client.test.ts`
Expected: PASS (all existing tests plus the new one)

- [ ] **Step 5: Gate the static export on the same flag**

Replace the contents of `apps/web/next.config.ts`:

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  ...(process.env.NEXT_PUBLIC_DEMO_MODE ? { output: "export" } : {}),
};

export default nextConfig;
```

- [ ] **Step 6: Add the demo build script**

In `apps/web/package.json`, add to `"scripts"` (alongside the existing `"build"` line):

```json
    "build:demo": "NEXT_PUBLIC_DEMO_MODE=1 next build --turbopack",
```

- [ ] **Step 7: Run the full frontend suite and confirm the normal build is untouched**

Run: `cd apps/web && npm run test && npm run typecheck`
Expected: PASS. Then confirm the flag is off by default:
Run: `cd apps/web && npm run build`
Expected: succeeds exactly as before (no `output: "export"`, since
`NEXT_PUBLIC_DEMO_MODE` is unset).

- [ ] **Step 8: Commit**

```bash
git add apps/web/lib/api-client.ts apps/web/lib/__tests__/api-client.test.ts \
  apps/web/next.config.ts apps/web/package.json
git commit -m "feat(web): route fetchJson through demo fixtures when NEXT_PUBLIC_DEMO_MODE is set"
```

---

### Task 3: Capture script and real fixtures

**Files:**
- Create: `scripts/capture_demo.py`
- Create (generated by running the script, then committed):
  `apps/web/public/demo/manifest.json`,
  `apps/web/public/demo/investigation-ids.json`,
  `apps/web/public/demo/evaluation-ids.json`,
  `apps/web/public/demo/captured-at.json`,
  and one JSON file per captured response.

**Interfaces:**
- Produces: `public/demo/manifest.json` (array of `{key, file}`, using the
  exact key format from Task 1's `buildDemoKey`); `public/demo/investigation-ids.json`
  and `public/demo/evaluation-ids.json` (each a JSON array of id strings) —
  Task 4's `generateStaticParams` reads these two directly.
  `public/demo/captured-at.json` (`{"captured_at": "YYYY-MM-DD"}`) — Task 6's
  banner reads this.

- [ ] **Step 1: Write the capture script**

```python
#!/usr/bin/env python3
"""Captures real RootLens API responses into apps/web/public/demo/ so the
static demo build (`npm run build:demo`) can resolve requests from disk
instead of a live backend.

Preconditions — a fully running local stack with a real local LLM:
    make up && make migrate && make ingest-fixtures
    ollama pull qwen3:8b   # if not already pulled, then `ollama serve`

Optionally, to also capture a benchmark run for the /evaluations page:
    make eval

Then, from the repo root:
    python3 scripts/capture_demo.py

Not wired into CI: it needs a local model, and a CI job that cannot run
is worse than no job.
"""

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

API_BASE_URL = "http://localhost:8000"
OUT_DIR = Path(__file__).resolve().parent.parent / "apps/web/public/demo"

INVESTIGATIONS: list[dict[str, Any]] = [
    {
        "metric": "product_revenue",
        "current_period": {"start": "2018-01-01", "end": "2018-01-31"},
        "comparison_period": {"start": "2017-12-01", "end": "2017-12-31"},
        "question": "Why did revenue decline?",
    },
    {
        "metric": "product_revenue",
        "current_period": {"start": "2018-02-01", "end": "2018-02-28"},
        "comparison_period": {"start": "2018-01-01", "end": "2018-01-31"},
        "question": None,
    },
    {
        "metric": "orders",
        "current_period": {"start": "2018-03-01", "end": "2018-03-31"},
        "comparison_period": {"start": "2018-02-01", "end": "2018-02-28"},
        "question": "What drove the change in order volume?",
    },
]


def build_demo_key(method: str, path: str, params: dict[str, str] | None = None) -> str:
    """Must match apps/web/lib/demo-data.ts's buildDemoKey exactly."""
    if not params:
        return f"{method} {path}"
    query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return f"{method} {path}?{query}"


def request(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    query: dict[str, str] | None = None,
) -> Any:
    url = f"{API_BASE_URL}{path}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(sorted(query.items()))}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read())


def wait_for_api() -> None:
    for _ in range(30):
        try:
            request("GET", "/api/health")
            return
        except (urllib.error.URLError, ConnectionError):
            time.sleep(1)
    print("API not reachable at http://localhost:8000 -- run `make up` first.", file=sys.stderr)
    sys.exit(1)


def wait_for_completion(investigation_id: str) -> dict[str, Any]:
    for _ in range(150):  # up to 5 minutes
        investigation = request("GET", f"/api/investigations/{investigation_id}")
        if investigation["status"] != "running":
            return investigation
        time.sleep(2)
    raise RuntimeError(f"investigation {investigation_id} never left 'running'")


def evidence_ids_from(events: list[dict[str, Any]]) -> list[str]:
    ids = []
    for event in events:
        if event["event_type"] == "tool_call":
            evidence_id = event["payload"].get("evidence_id")
            if evidence_id:
                ids.append(evidence_id)
    return ids


def write(relative_path: str, payload: Any) -> str:
    file_path = OUT_DIR / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(payload, indent=2))
    return relative_path


def main() -> None:
    wait_for_api()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, str]] = []
    investigation_ids: list[str] = []

    # The home page requests this on every load, with these exact
    # hardcoded defaults (apps/web/app/page.tsx).
    summary_params = {
        "current_start": "2018-01-01",
        "current_end": "2018-01-31",
        "comparison_start": "2017-12-01",
        "comparison_end": "2017-12-31",
    }
    summary = request("GET", "/api/metrics/summary", query=summary_params)
    file_name = write("metrics-summary-default.json", summary)
    manifest.append(
        {"key": build_demo_key("GET", "/api/metrics/summary", summary_params), "file": file_name}
    )

    for spec in INVESTIGATIONS:
        created = request("POST", "/api/investigations", spec)
        investigation_id = created["investigation_id"]
        print(f"created investigation {investigation_id}, waiting for completion...")
        investigation = wait_for_completion(investigation_id)
        investigation_ids.append(investigation_id)

        file_name = write(f"investigation-{investigation_id}.json", investigation)
        manifest.append(
            {"key": build_demo_key("GET", f"/api/investigations/{investigation_id}"), "file": file_name}
        )

        events = request("GET", f"/api/investigations/{investigation_id}/events")
        file_name = write(f"investigation-{investigation_id}-events.json", events)
        manifest.append(
            {
                "key": build_demo_key("GET", f"/api/investigations/{investigation_id}/events"),
                "file": file_name,
            }
        )

        for evidence_id in evidence_ids_from(events):
            evidence = request(
                "GET", f"/api/investigations/{investigation_id}/evidence/{evidence_id}"
            )
            file_name = write(f"evidence-{evidence_id}.json", evidence)
            manifest.append(
                {
                    "key": build_demo_key(
                        "GET", f"/api/investigations/{investigation_id}/evidence/{evidence_id}"
                    ),
                    "file": file_name,
                }
            )

    investigations_list = request("GET", "/api/investigations")
    file_name = write("investigations-list.json", investigations_list)
    manifest.append({"key": build_demo_key("GET", "/api/investigations"), "file": file_name})

    evaluation_ids: list[str] = []
    evaluations_list = request("GET", "/api/evaluations")
    file_name = write("evaluations-list.json", evaluations_list)
    manifest.append({"key": build_demo_key("GET", "/api/evaluations"), "file": file_name})

    if evaluations_list:
        run_id = evaluations_list[0]["run_id"]
        evaluation_ids.append(run_id)
        evaluation_detail = request("GET", f"/api/evaluations/{run_id}")
        file_name = write(f"evaluation-{run_id}.json", evaluation_detail)
        manifest.append(
            {"key": build_demo_key("GET", f"/api/evaluations/{run_id}"), "file": file_name}
        )
    else:
        print(
            "no evaluation runs found -- run `make eval` first if you want the "
            "benchmark page in the demo",
            file=sys.stderr,
        )

    write("manifest.json", manifest)
    write("investigation-ids.json", investigation_ids)
    write("evaluation-ids.json", evaluation_ids)
    write("captured-at.json", {"captured_at": date.today().isoformat()})

    print(
        f"captured {len(investigation_ids)} investigations, "
        f"{len(evaluation_ids)} evaluation run(s) -> {OUT_DIR}"
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Bring up the local stack**

Run: `make up && make migrate && make ingest-fixtures`
Expected: all three services healthy; `curl -s localhost:8000/api/health` returns
`{"status":"ok"}` (or equivalent 200).

Confirm Ollama is reachable and has the model: `ollama list` should show
`qwen3:8b`. If not: `ollama pull qwen3:8b`.

- [ ] **Step 3: Run the capture script**

Run: `python3 scripts/capture_demo.py`
Expected: prints "created investigation ..." three times, then "captured 3
investigations, N evaluation run(s) -> .../apps/web/public/demo". This can
take several minutes — each investigation runs the real bounded loop against
the local model.

If you want the `/evaluations` page in the demo too, run `make eval` before
this step so `evaluations_list` is non-empty.

- [ ] **Step 4: Sanity-check the output**

Run: `python3 -m json.tool apps/web/public/demo/manifest.json | head -20`
Expected: valid JSON, at least 8 entries (1 summary + 3 investigations + 3
event lists + 1 investigations list, plus one evidence entry per exhibit).

Run: `cat apps/web/public/demo/investigation-ids.json`
Expected: a JSON array of exactly 3 UUID strings.

- [ ] **Step 5: Commit**

```bash
git add scripts/capture_demo.py apps/web/public/demo
git commit -m "feat: capture real investigation runs for the static demo"
```

---

### Task 4: Split the two dynamic routes for static export

**Files:**
- Create: `apps/web/app/investigations/[id]/investigation-view.tsx`
  (the current body of `page.tsx`, as a named-export client component)
- Modify: `apps/web/app/investigations/[id]/page.tsx` (replaced with a thin
  server component)
- Create: `apps/web/app/evaluations/[id]/evaluation-view.tsx`
- Modify: `apps/web/app/evaluations/[id]/page.tsx`

**Interfaces:**
- Consumes: `apps/web/public/demo/investigation-ids.json` and
  `apps/web/public/demo/evaluation-ids.json` from Task 3.
- Produces: `InvestigationView({ id }: { id: string })` and
  `EvaluationView({ id }: { id: string })`, both **named** exports, imported
  by their respective server `page.tsx`.

- [ ] **Step 1: Create `investigation-view.tsx` from the current page**

Copy the entire current contents of
`apps/web/app/investigations/[id]/page.tsx` into a new file
`apps/web/app/investigations/[id]/investigation-view.tsx`, then make two
changes to the copy:

1. Remove `use` from the React import (no longer needed):
   ```typescript
   import { useCallback, useEffect, useMemo, useRef, useState } from "react";
   ```
2. Replace the component signature and drop the `use(params)` line:
   ```typescript
   export function InvestigationView({ id }: { id: string }) {
   ```
   (delete the old `const { id } = use(params);` line — `id` now arrives as a prop)

Everything else in the file — all state, `load`, polling, `openEvidence`,
`handleCancel`, the JSX — is unchanged.

- [ ] **Step 2: Replace `page.tsx` with a thin server component**

```typescript
// apps/web/app/investigations/[id]/page.tsx
import fs from "node:fs";
import path from "node:path";
import { InvestigationView } from "./investigation-view";

export function generateStaticParams() {
  if (!process.env.NEXT_PUBLIC_DEMO_MODE) return [];
  const idsPath = path.join(process.cwd(), "public/demo/investigation-ids.json");
  const ids = JSON.parse(fs.readFileSync(idsPath, "utf-8")) as string[];
  return ids.map((id) => ({ id }));
}

export default async function InvestigationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <InvestigationView id={id} />;
}
```

- [ ] **Step 3: Repeat the same split for evaluations**

Copy `apps/web/app/evaluations/[id]/page.tsx` into
`apps/web/app/evaluations/[id]/evaluation-view.tsx`, then:

1. Remove `use` from the React import:
   ```typescript
   import { useEffect, useMemo, useState } from "react";
   ```
2. Change the signature and drop the `use(params)` line:
   ```typescript
   export function EvaluationView({ id }: { id: string }) {
   ```

Then replace `apps/web/app/evaluations/[id]/page.tsx`:

```typescript
// apps/web/app/evaluations/[id]/page.tsx
import fs from "node:fs";
import path from "node:path";
import { EvaluationView } from "./evaluation-view";

export function generateStaticParams() {
  if (!process.env.NEXT_PUBLIC_DEMO_MODE) return [];
  const idsPath = path.join(process.cwd(), "public/demo/evaluation-ids.json");
  const ids = JSON.parse(fs.readFileSync(idsPath, "utf-8")) as string[];
  return ids.map((id) => ({ id }));
}

export default async function EvaluationDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <EvaluationView id={id} />;
}
```

- [ ] **Step 4: Typecheck and confirm no behavior regression**

Run: `cd apps/web && npm run typecheck`
Expected: PASS (no unused `use` import, no signature mismatches).

Run: `cd apps/web && npm run test:e2e`
Expected: PASS — `investigation.spec.ts` and `evaluations.spec.ts` exercise
these exact pages via `npm run dev` (normal, non-demo mode) and must still pass
unchanged, since the rendered behavior is identical.

- [ ] **Step 5: Confirm the demo build actually produces static pages for the captured ids**

Run: `cd apps/web && npm run build:demo`
Expected: succeeds, and the build log lists one static route per id from
`investigation-ids.json` and `evaluation-ids.json` (e.g.
`○ /investigations/<uuid>`), not a single dynamic `[id]` entry.

- [ ] **Step 6: Commit**

```bash
git add apps/web/app/investigations/\[id\] apps/web/app/evaluations/\[id\]
git commit -m "refactor(web): split dynamic routes so they can be statically exported"
```

---

### Task 5: Demo banner and disabled controls

**Files:**
- Create: `apps/web/components/demo-banner.tsx`
- Modify: `apps/web/app/layout.tsx`
- Modify: `apps/web/app/page.tsx`

**Interfaces:**
- Consumes: `apps/web/public/demo/captured-at.json` from Task 3.

- [ ] **Step 1: Write the banner component**

```typescript
// apps/web/components/demo-banner.tsx
import fs from "node:fs";
import path from "node:path";

export function DemoBanner() {
  const metaPath = path.join(process.cwd(), "public/demo/captured-at.json");
  const { captured_at: capturedAt } = JSON.parse(fs.readFileSync(metaPath, "utf-8")) as {
    captured_at: string;
  };

  return (
    <div className="border-b border-line bg-surface px-6 py-2 text-center font-mono text-xs text-muted">
      Read-only demo — investigations captured {capturedAt}. The investigation
      loop needs a local LLM, so this replays real runs instead of computing
      new ones.
    </div>
  );
}
```

- [ ] **Step 2: Render it conditionally from the layout**

In `apps/web/app/layout.tsx`, add the import:

```typescript
import { DemoBanner } from "@/components/demo-banner";
```

Then, as the first child inside `<body className={...}>`, before the
`<header>`:

```tsx
{process.env.NEXT_PUBLIC_DEMO_MODE && <DemoBanner />}
```

- [ ] **Step 3: Disable the date pickers and investigate button in demo mode**

In `apps/web/app/page.tsx`:

Give `DateField` a `disabled` prop:

```typescript
function DateField({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="eyebrow">{label}</span>
      <input
        type="date"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="rounded border border-line bg-surface px-2.5 py-1.5 font-mono text-xs text-ink transition-colors hover:border-line-strong disabled:opacity-50"
      />
    </label>
  );
}
```

Inside `Home()`, add near the top of the function body:

```typescript
  const isDemoMode = process.env.NEXT_PUBLIC_DEMO_MODE === "1";
```

Pass `disabled={isDemoMode}` to all four `<DateField>` call sites (current
start/end, comparison start/end).

Change the investigate button's `disabled` prop:

```typescript
          disabled={isInvestigating || isDemoMode}
```

And add, immediately after the existing `{investigateError && (...)}` block:

```tsx
        {isDemoMode && (
          <p className="mt-2.5 font-mono text-xs text-faint">
            Disabled in this read-only demo.
          </p>
        )}
```

- [ ] **Step 4: Confirm normal mode is unaffected**

Run: `cd apps/web && npm run test && npm run typecheck`
Expected: PASS. `isDemoMode` is `false` when the env var is unset, so every
existing behavior and test is unchanged.

- [ ] **Step 5: Commit**

```bash
git add apps/web/components/demo-banner.tsx apps/web/app/layout.tsx apps/web/app/page.tsx
git commit -m "feat(web): add the read-only demo banner and disable controls in demo mode"
```

---

### Task 6: End-to-end test against the built static export

**Files:**
- Create: `apps/web/playwright.demo.config.ts`
- Create: `apps/web/e2e/demo.spec.ts`
- Modify: `apps/web/package.json` (`scripts`)

**Interfaces:**
- Consumes: the `out/` directory produced by `npm run build:demo` (Task 2, 4).

- [ ] **Step 1: Write the demo Playwright config**

```typescript
// apps/web/playwright.demo.config.ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "demo.spec.ts",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:4173",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npx --yes serve@latest out -l 4173",
    url: "http://localhost:4173",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
```

- [ ] **Step 2: Write the demo spec**

```typescript
// apps/web/e2e/demo.spec.ts
import { expect, test } from "@playwright/test";

test("landing investigation renders with a working citation, and controls are disabled", async ({
  page,
}) => {
  await page.goto("/");

  await expect(page.getByText(/Read-only demo/)).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Investigate revenue change" }),
  ).toBeDisabled();

  await page.locator('a[href^="/investigations/"]').first().click();

  await expect(page.getByTestId("investigation-status")).toHaveText("completed");

  const firstCitation = page.getByRole("button", { name: /^E1/ });
  await firstCitation.click();

  const dialog = page.getByRole("dialog", { name: "Evidence detail" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText("rows")).toBeVisible();
});
```

- [ ] **Step 3: Add the npm script**

In `apps/web/package.json`, add to `"scripts"`:

```json
    "test:e2e:demo": "playwright test --config=playwright.demo.config.ts",
```

- [ ] **Step 4: Build the demo export and run the spec**

Run: `cd apps/web && npm run build:demo`
Expected: succeeds, produces `apps/web/out/`.

Run: `cd apps/web && npm run test:e2e:demo`
Expected: PASS. This is the test that catches drift between the demo and the
real app — it exercises the same `InvestigationView` and `EvidenceDrawer`
components the live app uses.

If it fails on the citation step, check that at least one captured
investigation's report actually cites evidence (`findings[].evidence_ids`
non-empty) — rerun `scripts/capture_demo.py` against a scenario that produces
findings if not.

- [ ] **Step 5: Commit**

```bash
git add apps/web/playwright.demo.config.ts apps/web/e2e/demo.spec.ts apps/web/package.json
git commit -m "test(web): add an e2e spec against the built demo export"
```

---

### Task 7: Deploy and link from the portfolio (manual — external account)

This task creates a new project on an external service tied to your account.
It is not something to run unsupervised — walk through it yourself, or have
it run with you watching.

**Files:**
- Modify (in the Portfolio repo, `~/Desktop/website/Portfolio`):
  `src/data/projects.tsx` (RootLens entry, add a demo URL)

- [ ] **Step 1: Push the `hosted-demo` branch and open a PR**

```bash
git push -u origin hosted-demo
gh pr create --title "Add a hosted read-only demo" --body "$(cat <<'EOF'
## Summary
- Static, read-only demo of RootLens, built from real captured investigation runs
- No server, no database, no API keys in the deployed site — $0, zero maintenance
- See docs/superpowers/specs/2026-09-11-hosted-demo-design.md for the design

## Test plan
- [x] apps/web unit tests pass (`npm run test`)
- [x] apps/web e2e against the built static export (`npm run test:e2e:demo`)
- [x] Normal (non-demo) build unaffected (`npm run build`)
EOF
)"
```

Wait for CI to go green, then merge (same flow as the `coverage-reporting`
PR: `gh pr merge --squash` or via the GitHub UI, whichever you prefer).

- [ ] **Step 2: Create the Vercel project**

From `apps/web/`, with the Vercel CLI (`npm i -g vercel` if you don't have
it):

```bash
cd apps/web
vercel login   # interactive — opens a browser
vercel link    # create a NEW project, separate from the portfolio's Vercel project
```

When prompted for build settings:
- Build command: `npm run build:demo`
- Output directory: `out`

- [ ] **Step 3: Deploy to production**

```bash
vercel --prod
```

Expected: prints a `https://<project>.vercel.app` URL. Open it and confirm the
banner, the landing investigation, and a citation click all work exactly as
in the local `test:e2e:demo` run.

- [ ] **Step 4: Link it from the portfolio**

In `~/Desktop/website/Portfolio/src/data/projects.tsx`, find the RootLens
entry and add the deployed URL as its demo link (following whatever field the
`Project` type already uses for a live-demo link — check the type definition
in that file before adding a new one).

- [ ] **Step 5: Commit and open a PR in the Portfolio repo**

```bash
cd ~/Desktop/website/Portfolio
git checkout -b link-rootlens-demo
git add src/data/projects.tsx
git commit -m "Link the RootLens hosted demo from its project card"
git push -u origin link-rootlens-demo
gh pr create --title "Link the RootLens hosted demo" --body "Adds the deployed static demo URL to the RootLens project card."
```

---

## Task Order and Dependencies

Tasks 1 → 2 → 3 are strictly sequential (each produces an interface the next
consumes), and Task 4 must follow Task 3: its `generateStaticParams` reads
`investigation-ids.json` / `evaluation-ids.json`, and its Step 5 check ("one
static route per id") is only meaningful once those ids come from a real
capture. Task 5 depends on Task 3's `captured-at.json`. Task 6 depends on
Tasks 2, 4, and 5 all being in place (it builds and tests the
whole demo). Task 7 depends on everything before it being merged.
