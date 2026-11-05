# Error analysis — dev split baseline (2026-11-05)

Run: `docs/evaluation/results/39455219-61bb-4754-b51f-323450c91237.json`
Model: qwen3:8b. Split: dev (24 scenarios). Commit: current `redteam-suite` branch
(post Phase 1, pre any Phase 2 change).

## Aggregate (before any fix)

| metric | value |
|---|---|
| root_cause_accuracy | 23.8% (5/21 scored) |
| dimension_accuracy | 4.8% (1/21 scored) |
| completion_rate | 83.3% (20/24) |
| abstention_accuracy | 87.5% (21/24) |
| evidence_citation_validity_rate | 79.2% |
| average_latency_ms | 68,810 |

The plan's note to check the scorer first (a prior ~6.7% dimension accuracy) turned
out to point at something real, but not a scorer bug — the scorer's logic is correct
(verified by reading `app/evaluation/scoring.py`). The actual cause is upstream.

## Per-scenario breakdown

Ground truth by template (dev split):

| template | scenarios | true driver |
|---|---|---|
| `cancellation_spike` | cs-01..07 (7) | `cancellation` |
| `order_volume_decline` | ov-01..07 (7) | `order_volume` |
| `seller_category_decline` | sc-01..07 (7) | `order_volume` |
| `order_volume_decline` (unanswerable) | ua-01..03 (3) | none (expect abstain) |

Predicted `primary_driver_hypothesis` was `"cancellation"` for **18 of 24** scenarios,
regardless of the true driver. `root_cause_accuracy` (23.8%) is almost exactly the
dev split's share of scenarios that are actually cancellation-driven (7/24 ≈ 29%,
minus a couple of misses) — the model isn't discriminating between driver types at
all, it's defaulting to one label.

## Root cause (traced with a standalone probe, not guesswork)

Wrote a one-off script (`/tmp/probe_incident_numbers.py`, not committed — reran the
real incident-application + `compare_periods` path outside the LLM/engine) to see the
actual `orders` and `cancellation_rate` percent-changes the decomposition prompt is
built from:

| scenario | true driver / severity | orders % change | cancellation % change |
|---|---|---|---|
| cs-01 | cancellation / high | -2.4% | **+98.7%** |
| cs-04 | cancellation / low | -3.5% | **-44.4%** (wrong sign!) |
| ov-01 | order_volume / medium | +0.03% (flat) | -57.9% |
| ov-05 | order_volume / high | +1.4% | **+51.3%** |
| sc-05 | order_volume / high | -25.3% | -39.9% |
| ua-01 | unanswerable | +53.1% | +44.4% |

Two compounding problems, both load-bearing:

1. **Every incident is scoped to a narrow slice** (one `customer_state`, one
   `product_category`, or their intersection — see `apply_incident` in
   `app/evaluation/incidents.py`), but the decomposition step's only signal is the
   **global**, whole-dataset `orders` and `cancellation_rate` percent-change
   (`app/investigations/engine.py::_decompose`). Removing/cancelling a `medium`
   (18%) or even `high` (30%) fraction of orders *within one state* barely moves a
   ~99k-row, all-of-Brazil aggregate — `ov-01` ("medium" severity, a real incident)
   shows essentially **zero** visible order-count change at all.
2. **`cancellation_rate`'s natural period-to-period variance is comparable to or
   larger than a real incident's effect on it.** `cs-04` (a real, low-severity
   cancellation spike — the *ground truth positive*) shows the rate going *down*
   44%. `ov-05` (no cancellation incident at all — a *true negative*) shows the
   rate going *up* 51%, a bigger swing than the real positive. No fixed numeric
   threshold on this one global number can separate these cases — the signal itself
   doesn't carry enough information at this dilution level, independent of whether
   an LLM or deterministic code reads it.

This is why the model settling on "cancellation" isn't really the bug to fix in
isolation: tightening the prompt's threshold language, or replacing the LLM's
judgment with a hand-picked numeric cutoff on the same global numbers, would still
fail on exactly the hard cases above (the signal both methods would read from is the
same noisy number). A fix has to change *what evidence the driver call is based on*,
not just *who reads it*.

## Secondary findings (same run, smaller scope)

- **Dimension misses among correct-driver cases**: cs-01/03/04/06 all got the driver
  right (`cancellation`) but the predicted segment value was wrong. All four
  `cancellation_spike` incidents are a **(state × category) intersection** —
  `calculate_contribution` only breaks down one dimension at a time, marginalizing
  over the other, which dilutes an intersection-only effect the same way as above.
  `sc-05` (single-dimension `seller_category_decline` incident) got its segment
  exactly right, supporting this as the same dilution problem, one level down.
- **Unanswerable abstention is broken on this run**: all 3 `ua-*` scenarios failed
  to abstain (`abstained=False`); 2 of the 3 also hit `ReadTimeout`. Needs its own
  look — may be a consequence of the timeout cutting the investigation off before
  the abstain path is reached, or a separate gap. Not investigated further here to
  keep this analysis scoped to root-cause/dimension accuracy.
- **4/24 `execution_error` (ReadTimeout)** — matches the plan's historical timeout
  count. Phase 3's territory, not re-investigated here.
- **14/24 reports have `total_claim_count == 0`** (no scored `observed_fact`
  findings at all). Doesn't affect `root_cause_accuracy`/`dimension_accuracy`
  (those score off the decomposition event + contribution evidence directly, not
  the narrative report), but it's a real, separate report-generation gap worth a
  follow-up — out of scope for this phase's accuracy numbers.

## What this means for "fix 1-2 failure classes"

The plan's listed candidates (tighter prompt, deterministic threshold on the same
numbers, structured-output retry) address *who* reads the global aggregate, not the
dilution problem itself, and the probe above shows that's not enough — `cs-04`
(true positive, signal goes the wrong way) and `ov-05` (true negative, signal goes
the "right" way harder than the true positive) break any threshold on this input.

A fix that would actually move the needle has to bring a **segment-aware** signal
into the driver decision — e.g., running `calculate_contribution` on a candidate
dimension *before* classifying the driver, and classifying from the strongest
segment-level deviation rather than the global number. That's a bigger, genuinely
architectural change (reordering the decomposition step, not a prompt/threshold
edit), bigger than this phase's "one change at a time" budget was scoped for.

**Decision needed before continuing Phase 2**: attempt the segment-first
redesign now (real scope increase), or document this as the phase's finding and
move on to Phase 3/4, returning to accuracy work later with this analysis in hand.
Raised to the user rather than picked unilaterally, given the size of the change.
