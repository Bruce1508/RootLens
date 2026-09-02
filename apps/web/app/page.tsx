"use client";

import { useEffect, useState } from "react";
import { KpiCard } from "@/components/kpi-card";
import { getMetricsSummary, type MetricsSummary } from "@/lib/api-client";
import { formatCurrency, formatPercentChange } from "@/lib/format";

// Defaults chosen to match the fixture dataset's two non-overlapping
// months so a fresh `make ingest-fixtures` run shows a populated
// dashboard without the user picking dates first.
const DEFAULT_CURRENT_START = "2018-01-01";
const DEFAULT_CURRENT_END = "2018-01-31";
const DEFAULT_COMPARISON_START = "2017-12-01";
const DEFAULT_COMPARISON_END = "2017-12-31";

export default function Home() {
  const [currentStart, setCurrentStart] = useState(DEFAULT_CURRENT_START);
  const [currentEnd, setCurrentEnd] = useState(DEFAULT_CURRENT_END);
  const [comparisonStart, setComparisonStart] = useState(DEFAULT_COMPARISON_START);
  const [comparisonEnd, setComparisonEnd] = useState(DEFAULT_COMPARISON_END);

  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    getMetricsSummary(currentStart, currentEnd, comparisonStart, comparisonEnd)
      .then((data) => {
        if (!cancelled) setSummary(data);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        // A TypeError here means fetch() itself failed (network/CORS/DNS)
        // before any HTTP response existed — the backend's own error
        // detail (surfaced by api-client for 4xx/5xx responses) needs no
        // such hint, since the backend clearly did respond.
        if (err instanceof TypeError) {
          setError(`${err.message}. Is the backend running at NEXT_PUBLIC_API_BASE_URL?`);
        } else {
          setError(err instanceof Error ? err.message : "Failed to load metrics");
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [currentStart, currentEnd, comparisonStart, comparisonEnd]);

  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-xl font-semibold">RootLens</h1>
      <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
        KPI dashboard — deterministic period comparison (Milestone 1, no AI involved yet).
      </p>

      <div className="mt-6 grid grid-cols-2 gap-4 text-sm">
        <fieldset className="rounded-lg border border-neutral-200 p-3 dark:border-neutral-800">
          <legend className="px-1 text-neutral-500 dark:text-neutral-400">Current period</legend>
          <label className="flex items-center justify-between gap-2 py-1">
            Start
            <input
              type="date"
              value={currentStart}
              onChange={(e) => setCurrentStart(e.target.value)}
              className="rounded border border-neutral-300 px-2 py-1 dark:border-neutral-700 dark:bg-neutral-900"
            />
          </label>
          <label className="flex items-center justify-between gap-2 py-1">
            End
            <input
              type="date"
              value={currentEnd}
              onChange={(e) => setCurrentEnd(e.target.value)}
              className="rounded border border-neutral-300 px-2 py-1 dark:border-neutral-700 dark:bg-neutral-900"
            />
          </label>
        </fieldset>

        <fieldset className="rounded-lg border border-neutral-200 p-3 dark:border-neutral-800">
          <legend className="px-1 text-neutral-500 dark:text-neutral-400">
            Comparison period
          </legend>
          <label className="flex items-center justify-between gap-2 py-1">
            Start
            <input
              type="date"
              value={comparisonStart}
              onChange={(e) => setComparisonStart(e.target.value)}
              className="rounded border border-neutral-300 px-2 py-1 dark:border-neutral-700 dark:bg-neutral-900"
            />
          </label>
          <label className="flex items-center justify-between gap-2 py-1">
            End
            <input
              type="date"
              value={comparisonEnd}
              onChange={(e) => setComparisonEnd(e.target.value)}
              className="rounded border border-neutral-300 px-2 py-1 dark:border-neutral-700 dark:bg-neutral-900"
            />
          </label>
        </fieldset>
      </div>

      <div className="mt-6">
        {isLoading && <p className="text-sm text-neutral-500">Loading…</p>}

        {error && (
          <p className="text-sm text-red-600 dark:text-red-400" role="alert">
            {error}
          </p>
        )}

        {summary && !isLoading && !error && (
          <div className="grid grid-cols-2 gap-4">
            <KpiCard
              label="Product revenue"
              currentValue={formatCurrency(summary.product_revenue.current_value)}
              percentChange={formatPercentChange(summary.product_revenue.percent_change)}
              isNegative={summary.product_revenue.absolute_change < 0}
            />
            <KpiCard
              label="Orders"
              currentValue={String(summary.orders.current_value)}
              percentChange={formatPercentChange(summary.orders.percent_change)}
              isNegative={summary.orders.absolute_change < 0}
            />
          </div>
        )}
      </div>
    </main>
  );
}
