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

## Addendum: segment-first redesign attempt (same day)

User approved attempting the segment-first redesign. Four methods were tried, each
validated against real scenarios with a standalone probe (not guesswork, not wired
into the engine) before deciding whether to implement it for real. None of the
probe scripts below are committed — they're throwaway validation, kept here as the
record of what was tried and why it didn't land.

**Method 1 — rank candidate segments by revenue contribution** (today's
`calculate_contribution`, run across all 3 dimensions, take the biggest
`share_of_total_change`): the true segment was essentially never the top pick, even
for single-dimension incidents. `ov-01`/`ov-05` delete orders in one specific
state, yet revenue-contribution ranking picked a *different* state every time —
dollar revenue per segment is too noisy month-to-month (a handful of high-value
orders can swing a segment's total) to rank by at all.

**Method 2 — rank by raw per-segment order-count / cancellation-rate percent
change** (a direct, un-normalized version of the same idea): also unreliable —
small-sample segments produce huge relative swings from pure noise, so the ranking
is dominated by whichever segment happened to have the fewest orders that month,
not the one with a real incident.

**Method 3 — two-proportion z-test per segment** (statistically correct way to
normalize for sample size: compares each segment's rate in the two periods against
its own pooled binomial variance). Excluding `seller` (thousands of near-empty
segments, pure noise) and testing only `customer_state` (27) × `product_category`
(~70) ≈ 100 candidates: **2/14** scenarios tested got the right segment
(`cs-01`, `ov-02`). Real-world demand data isn't i.i.d. binomial — it's
overdispersed (seasonality, lumpy category/seller behavior) — so with ~100
candidates tested, several produce an apparently "extreme" z purely by chance
(classic multiple-comparisons), burying the real signal most of the time.

**Method 4 — 6-month historical-baseline z-score** (score each segment's
comparison→current change against *its own* trailing 6-month volatility, instead
of a single-formula binomial variance — directly addresses overdispersion):

| scenario family | correct dimension + segment |
|---|---|
| `cancellation_spike` (cs-01..07) | **4/7** (cs-01, cs-02, cs-03, cs-04) |
| `order_volume_decline` / `seller_category_decline` (ov-01..07, sc-01, sc-05) | **0/9** |

A real, measurable improvement for cancellation-type detection — but
`product_category`'s larger candidate pool (~70) keeps out-competing the true
`customer_state` segment (27) on every single order-volume scenario tested, the
true state was never once the top pick. This is a different unsolved problem from
the one Method 4 fixed, not a tuning tweak away.

**Conclusion**: four methodologically distinct approaches, one clear partial win
(cancellation detection) and one still-open problem (order-volume detection, the
*larger* of the two groups — 14/24 dev scenarios). Decided **not** to ship a
half-working mechanism into production code for this. A reliable fix likely needs
either a properly multiple-comparison-corrected threshold scaled by each
dimension's candidate count, a better null model for "order volume changed"
(absolute per-segment count against its own baseline, not share-of-total, which
conflates a segment's own change with everyone else's), or a different method
entirely (structural-break detection, CUSUM) — real, dedicated effort, not
something to land inside this phase's remaining budget.

## Phase 2 outcome (final)

No code change shipped. Before/after is before/before — the baseline numbers
stand as both the "before" and the final reported number for this phase:

| split | root_cause_accuracy | dimension_accuracy |
|---|---|---|
| dev | 23.8% (unchanged) | 4.8% (unchanged) |
| held-out | 55.6% (unchanged) | 0.0% (unchanged) |

Reported honestly per the plan's own instruction, rather than shipping an
unvalidated fix to produce a different number. The root cause (global/diluted
decomposition signal) and four attempted fixes are documented above for whoever
picks this up next.
