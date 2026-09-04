# Performance notes (Milestone 6)

Informal, locally-measured numbers from one developer machine during this
milestone's own smoke testing — not a controlled benchmark, not a
cross-hardware guarantee (PRD §17 tracks this rather than promising it).
Model: `qwen3:8b` via Ollama, Apple Silicon, real ingested Olist dataset
(~99k orders).

## Analytics query latency (deterministic tools)

Measured from real `Evidence.execution_ms` values recorded during actual
investigations against the full dataset:

| Tool | Observed |
|---|---:|
| `compare_periods` (revenue/orders/cancellation_rate) | 2–25 ms |
| `calculate_contribution` (segment breakdown) | 15–25 ms |

Well inside the NFR targets (dashboard summary < 2s, evidence query < 3s)
— these are simple, indexed, parameterized queries; latency here was
never the bottleneck.

## Full investigation latency (dominated by the local model)

| Run | Steps | Outcome | Wall clock |
|---|---:|---|---:|
| Cancellation-spike scenario (`ov-08`, small-state) | 4 | completed | ~28s |
| Demo investigation, attempt 1 | 5 | **failed — hit the 120s per-call Ollama timeout** during report generation | 120s+ |
| Demo investigation, attempt 2 (same periods) | 8 (used the ad hoc SQL step) | completed | ~70–80s |

The spread between the two "demo" attempts — identical input, ~28s vs.
120s+ — is the headline finding: **local LLM latency on this hardware is
highly variable per call**, not a function of query complexity. A
`DecompositionPlan` or `ReportNarrative` call can take anywhere from a
few seconds to over two minutes for the same prompt shape. This is why
Milestone 6 added a bounded timeout to `OllamaProvider` (previously
unbounded — a slow call could hang a scenario, and the whole evaluation
run behind it, forever) rather than assuming local models respond
quickly.

## Practical implications

- **`make eval`'s wall-clock cost is dominated by model latency, not the
  harness.** 35 scenarios × up to ~5 LLM calls each, at this machine's
  observed variance, means a full run's duration is not tightly
  predictable — budget accordingly rather than assuming a fixed runtime.
- **The 120s per-call timeout is a real trade-off**, not just a safety
  net: it will occasionally fail an investigation that would have
  succeeded on more time (as seen in "attempt 1" above). A faster/smaller
  model, or a longer timeout for non-benchmark interactive use, are the
  two levers available without further code changes.
- **The ad hoc `run_safe_sql` step (Milestone 6) adds one extra LLM
  round-trip** only when a hypothesis is inconclusive — it does not run
  on every investigation, so its cost is conditional, not fixed overhead.
