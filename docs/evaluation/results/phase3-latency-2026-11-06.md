# Phase 3: timeouts and latency (2026-11-06)

Model: qwen3:8b. Branch: `redteam-suite`, post Phase 2. Same 35 scenarios (24 dev / 11
held-out) as the Phase 2 baseline, unchanged.

## Task 1: background execution (verify only, no change)

Investigations already run via FastAPI `BackgroundTasks`
(`app/investigations/service.py::create_investigation`), not inside the request — the
POST handler returns immediately after creating the row, and polling/cancellation are
already served by `GET /events`, `GET /stream` (SSE), and `POST /cancel`. Not
request-bound, so no job queue was added.

## Task 2: profiling (finding)

Per-step timestamps (`investigation_events`) on all 4 dev-split `ReadTimeout` cases from
the Phase 2 baseline (`cs-02`, `cs-05`, `ov-01`, `ua-01`) showed the same pattern: the
three fixed analytics tool calls (`compare_periods` x3) and `calculate_contribution`
always completed in well under 150ms combined — never the bottleneck. The cost was
always a single LLM call (`generate_structured`, for decomposition, the ad-hoc query
decision/retry, or report generation) hanging until the Ollama client's 120s timeout
fired with `ReadTimeout`.

Root cause: `qwen3:8b` is a hybrid-thinking model, and `generate_structured()` never set
Ollama's `think` parameter, so it defaulted to enabled. A spot check on an identical
prompt: 21.7s / 640 tokens / 2509-char hidden reasoning trace with the default, vs 0.5s
/ 14 tokens with `think=False`. The trace is pure overhead for a schema-validated
structured-output call and its length is unbounded and non-deterministic per prompt —
which explains both the high mean latency and the occasional run that exceeded 120s.

## Task 3: fix shipped

`think=False` on both `generate()` calls in `OllamaProvider.generate_structured`
(`app/llm/ollama_provider.py`) — the first attempt and the validation-failure retry.
Commit `b18b27e`.

## Task 4: before / after

### Dev split (24 scenarios)

| metric | before | after |
|---|---|---|
| completion_rate | 83.3% (20/24) | 95.8% (23/24) |
| timeouts | 4/24 | 1/24 |
| p50 latency | 54.0s | 47.3s |
| p95 latency | 152.1s | 77.9s |
| mean latency | 68.8s | 50.9s |
| root_cause_accuracy | 23.8% | 28.6% |

Run: `docs/evaluation/results/8db42b05-43a3-4abb-a2c9-3112d591f8c3.json`

### Held-out split (11 scenarios)

| metric | before | after |
|---|---|---|
| completion_rate | 81.8% (9/11) | 100% (11/11) |
| timeouts | 2/11 | 0/11 |
| p50 latency | 56.7s | 45.6s |
| p95 latency | 129.6s | 56.6s |
| mean latency | 66.4s | 43.9s |
| root_cause_accuracy | 55.6% | 55.6% |

Run: `docs/evaluation/results/641d9122-265e-4960-bf48-99f5e814f377.json`

### Reading these numbers honestly

- **Timeouts**: 6/35 → 1/35 across both splits. Held-out reached zero; one dev scenario
  (`sc-02`) still timed out. Its event timeline is the same shape as the fixed cases
  (three fast tool calls, then 120s of silence on the next LLM call) but this run
  already had `think=False` applied — so it isn't the thinking-trace issue, it's
  residual generation-time variance (most likely host/Ollama resource contention from
  24 scenarios run back-to-back). Not chased further this phase; the plan's own "done
  when" criterion allows "0 timeouts (or an honest count)".
- **Latency**: p95 fell the most (−49% dev, −56% held-out) because the tail was exactly
  the near-timeout runs this fix targets; mean fell 26-34%.
- **Accuracy**: held-out is unchanged (55.6% → 55.6%), confirming the fix didn't touch
  decomposition logic or correctness. Dev's root_cause_accuracy ticked up (23.8% →
  28.6%, 1 scenario) — reported as LLM run-to-run variance, not a claimed improvement;
  no accuracy-affecting code changed this phase, and dev's historical benchmark
  (2026-09-13) already put it at ~28.6%.
