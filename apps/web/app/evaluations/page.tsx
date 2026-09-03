"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getEvaluations, type EvaluationRunView } from "@/lib/api-client";

function formatRate(value: number | undefined): string {
  if (value === undefined) return "—";
  return `${(value * 100).toFixed(0)}%`;
}

export default function EvaluationsPage() {
  const [runs, setRuns] = useState<EvaluationRunView[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getEvaluations()
      .then(setRuns)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Failed to load evaluation runs"),
      );
  }, []);

  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-xl font-semibold">Evaluation runs</h1>
      <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
        Benchmark runs against the FR-13 incident scenarios (`make eval`).
      </p>

      {error && (
        <p className="mt-4 text-sm text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      )}

      {runs === null && !error && <p className="mt-4 text-sm text-neutral-500">Loading…</p>}

      {runs !== null && runs.length === 0 && (
        <p className="mt-4 text-sm text-neutral-500 dark:text-neutral-400">
          No evaluation runs yet. Run <code>make eval</code> to produce one.
        </p>
      )}

      {runs !== null && runs.length > 0 && (
        <ul className="mt-6 space-y-3">
          {runs.map((run) => (
            <li key={run.run_id}>
              <Link
                href={`/evaluations/${run.run_id}`}
                className="block rounded-lg border border-neutral-200 p-4 hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
              >
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="font-medium">
                      {run.model_name} — {run.split}
                    </p>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400">
                      {new Date(run.started_at).toLocaleString()} · {run.status}
                    </p>
                  </div>
                  <div className="flex gap-4 text-right text-xs text-neutral-600 dark:text-neutral-400">
                    <div>
                      <p className="text-neutral-400 dark:text-neutral-500">Root cause</p>
                      <p>{formatRate(run.aggregate_metrics?.root_cause_accuracy)}</p>
                    </div>
                    <div>
                      <p className="text-neutral-400 dark:text-neutral-500">Dimension</p>
                      <p>{formatRate(run.aggregate_metrics?.dimension_accuracy)}</p>
                    </div>
                    <div>
                      <p className="text-neutral-400 dark:text-neutral-500">Completion</p>
                      <p>{formatRate(run.aggregate_metrics?.completion_rate)}</p>
                    </div>
                  </div>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
