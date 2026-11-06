# Phase 2 baseline (2026-11-05)

Model: qwen3:8b. Commit: `redteam-suite` branch, post Phase 1. Seed data: existing
`eval.eval_scenarios`/`eval.eval_ground_truth` (35 scenarios: 24 dev / 11 held-out),
seeded before this session.

No code change shipped this phase (see `docs/evaluation/error-analysis-2026-11-05.md`
for the full investigation and why) — these numbers are both the "before" and the
final reported result for Phase 2.

## Dev split (24 scenarios)

Run: `docs/evaluation/results/39455219-61bb-4754-b51f-323450c91237.json`

| metric | value |
|---|---|
| root_cause_accuracy | 23.8% (5/21 scored) |
| dimension_accuracy | 4.8% (1/21 scored) |
| completion_rate | 83.3% (20/24) |
| abstention_accuracy | 87.5% (21/24) |
| evidence_citation_validity_rate | 79.2% |
| average_latency_ms | 68,810 |

## Held-out split (11 scenarios)

Run: `docs/evaluation/results/9ae3790f-dc27-4666-8424-a709e419d0ec.json`

| metric | value |
|---|---|
| root_cause_accuracy | 55.6% |
| dimension_accuracy | 0.0% |
| completion_rate | 81.8% |
| abstention_accuracy | 81.8% |
| evidence_citation_validity_rate | 81.8% |
| average_latency_ms | 66,365 |

Consistent with the plan's documented historical benchmark (2026-09-13: ~28.6% dev /
~55.6% held-out root-cause accuracy) — held-out matches almost exactly; dev is close
within run-to-run LLM variance.
