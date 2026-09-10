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

const STATUS_STYLES: Record<string, string> = {
  running: "text-signal",
  completed: "text-positive",
  partial: "text-caution",
  failed: "text-negative",
  timed_out: "text-negative",
  cancelled: "text-faint",
};

/** The headline states the measured fact, then asks the one question the
    product exists to answer. The percentage is rendered unsigned —
    direction is carried by the verb — so this never duplicates the KPI
    card's own signed value. */
function headlineFor(summary: MetricsSummary | null): string | null {
  const change = summary?.product_revenue.percent_change;
  if (change === null || change === undefined) return null;
  const verb = change < 0 ? "fell" : "rose";
  return `Revenue ${verb} ${Math.abs(change * 100).toFixed(1)}% this period.`;
}

function DateField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="eyebrow">{label}</span>
      <input
        type="date"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border border-line bg-surface px-2.5 py-1.5 font-mono text-xs text-ink transition-colors hover:border-line-strong"
      />
    </label>
  );
}

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

  const [recentInvestigations, setRecentInvestigations] = useState<InvestigationView[] | null>(
    null,
  );
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
      setInvestigateError(err instanceof Error ? err.message : "Failed to start investigation");
      setIsInvestigating(false);
    }
  }, [currentStart, currentEnd, comparisonStart, comparisonEnd, router]);

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex flex-wrap items-end gap-x-10 gap-y-6">
        <fieldset className="flex items-end gap-3">
          <legend className="eyebrow mb-2">This period</legend>
          <DateField label="From" value={currentStart} onChange={setCurrentStart} />
          <DateField label="To" value={currentEnd} onChange={setCurrentEnd} />
        </fieldset>
        <fieldset className="flex items-end gap-3">
          <legend className="eyebrow mb-2">Compared with</legend>
          <DateField label="From" value={comparisonStart} onChange={setComparisonStart} />
          <DateField label="To" value={comparisonEnd} onChange={setComparisonEnd} />
        </fieldset>
      </div>

      <h1 className="mt-10 max-w-2xl font-serif text-4xl leading-tight tracking-tight text-balance">
        {headlineFor(summary) ?? "What moved this period?"}{" "}
        {headlineFor(summary) && <span className="text-signal">Why?</span>}
      </h1>

      <div className="mt-8">
        {isLoading && <p className="font-mono text-xs text-faint">Loading…</p>}

        {error && (
          <p className="max-w-xl text-sm text-negative" role="alert">
            {error}
          </p>
        )}

        {summary && !isLoading && !error && (
          <div className="grid max-w-xl grid-cols-2 gap-8">
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

      <div className="mt-9">
        <button
          type="button"
          onClick={handleInvestigate}
          disabled={isInvestigating}
          className="rounded bg-signal px-4 py-2.5 font-mono text-xs font-medium tracking-wide text-bg transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {isInvestigating ? "Starting investigation…" : "Investigate revenue change"}
        </button>
        {investigateError && (
          <p className="mt-2.5 text-sm text-negative" role="alert">
            {investigateError}
          </p>
        )}
      </div>

      <section className="mt-16">
        <h2 className="eyebrow">Recent investigations</h2>

        {recentError && (
          <p className="mt-3 text-sm text-negative" role="alert">
            {recentError}
          </p>
        )}

        {recentInvestigations === null && !recentError && (
          <p className="mt-3 font-mono text-xs text-faint">Loading…</p>
        )}

        {recentInvestigations !== null && recentInvestigations.length === 0 && (
          <p className="mt-3 font-mono text-xs text-faint">
            No investigations yet — start one above.
          </p>
        )}

        {recentInvestigations !== null && recentInvestigations.length > 0 && (
          <ul className="mt-4 border-t border-line">
            {recentInvestigations.map((investigation) => (
              <li key={investigation.investigation_id}>
                <Link
                  href={`/investigations/${investigation.investigation_id}`}
                  className="flex items-baseline gap-4 border-b border-line px-1 py-3 transition-colors hover:bg-surface"
                >
                  <span className="font-mono text-xs text-ink">{investigation.metric}</span>
                  <span className="font-mono text-xs text-faint tabular-nums">
                    {investigation.current_period.start} → {investigation.current_period.end}
                  </span>
                  <span className="ml-auto font-mono text-xs text-faint tabular-nums">
                    {new Date(investigation.created_at).toLocaleDateString()}
                  </span>
                  <span
                    className={`w-20 text-right font-mono text-xs ${
                      STATUS_STYLES[investigation.status] ?? "text-faint"
                    }`}
                  >
                    {investigation.status}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
