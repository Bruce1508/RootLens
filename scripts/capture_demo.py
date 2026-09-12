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

API_BASE_URL = "http://127.0.0.1:8010"
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
        "metric": "product_revenue",
        "current_period": {"start": "2018-04-01", "end": "2018-04-30"},
        "comparison_period": {"start": "2018-03-01", "end": "2018-03-31"},
        "question": "What drove the change in revenue this period?",
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
                "key": build_demo_key(
                    "GET", f"/api/investigations/{investigation_id}/events"
                ),
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
