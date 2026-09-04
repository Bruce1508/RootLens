"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { KpiCard } from "@/components/kpi-card";
import {
  createInvestigation,
  getInvestigations,
  getMetricsSummary,
  type InvestigationView,
  type MetricsSummary,
} from "@/lib/api-client";
import { formatCurrency, formatPercentChange } from "@/lib/format";

// Defaults chosen to match the fixture dataset's two non-overlapping
// months so a fresh `make ingest-fixtures` run shows a populated
// dashboard without the user picking dates first.
const DEFAULT_CURRENT_START = "2018-01-01";
const DEFAULT_CURRENT_END = "2018-01-31";
const DEFAULT_COMPARISON_START = "2017-12-01";
const DEFAULT_COMPARISON_END = "2017-12-31";

export default function Home() {
  const router = useRouter();

  const [currentStart, setCurrentStart] = useState(DEFAULT_CURRENT_START);
  const [currentEnd, setCurrentEnd] = useState(DEFAULT_CURRENT_END);
  const [comparisonStart, setComparisonStart] = useState(DEFAULT_COMPARISON_START);
  const [comparisonEnd, setComparisonEnd] = useState(DEFAULT_COMPARISON_END);

  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const [isInvestigating, setIsInvestigating] = useState(false);
  const [investigateError, setInvestigateError] = useState<string | null>(null);

  const [recentInvestigations, setRecentInvestigations] = useState<
    InvestigationView[] | null
  >(null);
  const [recentError, setRecentError] = useState<string | null>(null);

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

  useEffect(() => {
    getInvestigations()
      .then(setRecentInvestigations)
      .catch((err: unknown) =>
        setRecentError(
          err instanceof Error ? err.message : "Failed to load recent investigations",
        ),
      );
  }, []);

  const handleInvestigate = useCallback(async () => {
    setIsInvestigating(true);
    setInvestigateError(null);
    try {
      const investigation = await createInvestigation({
        metric: "product_revenue",
        current_period: { start: currentStart, end: currentEnd },
        comparison_period: { start: comparisonStart, end: comparisonEnd },
      });
      router.push(`/investigations/${investigation.investigation_id}`);
    } catch (err) {
      setInvestigateError(
        err instanceof Error ? err.message : "Failed to start investigation",
      );
      setIsInvestigating(false);
    }
  }, [currentStart, currentEnd, comparisonStart, comparisonEnd, router]);

  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-xl font-semibold">RootLens</h1>
      <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
        KPI dashboard — pick two periods, then investigate why revenue changed
        between them.
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

      <div className="mt-6">
        <button
          type="button"
          onClick={handleInvestigate}
          disabled={isInvestigating}
          className="rounded bg-neutral-900 px-3 py-2 text-sm font-medium text-white hover:bg-neutral-700 disabled:opacity-50 dark:bg-neutral-100 dark:text-neutral-900 dark:hover:bg-neutral-300"
        >
          {isInvestigating ? "Starting investigation…" : "Investigate revenue change"}
        </button>
        {investigateError && (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400" role="alert">
            {investigateError}
          </p>
        )}
      </div>

      <section className="mt-10">
        <h2 className="text-sm font-semibold text-neutral-500 dark:text-neutral-400">
          Recent investigations
        </h2>

        {recentError && (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400" role="alert">
            {recentError}
          </p>
        )}

        {recentInvestigations === null && !recentError && (
          <p className="mt-2 text-sm text-neutral-500">Loading…</p>
        )}

        {recentInvestigations !== null && recentInvestigations.length === 0 && (
          <p className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
            No investigations yet — start one above.
          </p>
        )}

        {recentInvestigations !== null && recentInvestigations.length > 0 && (
          <ul className="mt-3 space-y-2">
            {recentInvestigations.map((investigation) => (
              <li key={investigation.investigation_id}>
                <Link
                  href={`/investigations/${investigation.investigation_id}`}
                  className="block rounded-lg border border-neutral-200 p-3 text-sm hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="font-medium">
                        {investigation.metric} — {investigation.current_period.start}..
                        {investigation.current_period.end}
                      </p>
                      <p className="text-xs text-neutral-500 dark:text-neutral-400">
                        {new Date(investigation.created_at).toLocaleString()}
                      </p>
                    </div>
                    <span className="text-xs text-neutral-600 dark:text-neutral-400">
                      {investigation.status}
                    </span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
