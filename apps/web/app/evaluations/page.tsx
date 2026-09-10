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
    <main className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="font-serif text-3xl tracking-tight">Benchmark runs</h1>
      <p className="mt-2 max-w-xl text-sm text-muted">
        Each run replays the incident scenarios against hidden ground truth and scores the
        result. Accuracy varies with the model and hardware — these are measured, not targets.
      </p>

      {error && (
        <p className="mt-6 text-sm text-negative" role="alert">
          {error}
        </p>
      )}

      {runs === null && !error && <p className="mt-6 font-mono text-xs text-faint">Loading…</p>}

      {runs !== null && runs.length === 0 && (
        <p className="mt-6 font-mono text-xs text-faint">
          No runs yet. Run <span className="text-ink">make eval</span> to produce one.
        </p>
      )}

      {runs !== null && runs.length > 0 && (
        <ul className="mt-8 border-t border-line">
          {runs.map((run) => (
            <li key={run.run_id}>
              <Link
                href={`/evaluations/${run.run_id}`}
                className="flex flex-wrap items-center gap-x-8 gap-y-3 border-b border-line px-1 py-4 transition-colors hover:bg-surface"
              >
                <div className="min-w-56">
                  <p className="font-mono text-sm text-ink">
                    {run.model_name} — {run.split}
                  </p>
                  <p className="mt-1 font-mono text-xs text-faint tabular-nums">
                    {new Date(run.started_at).toLocaleString()} · {run.status}
                  </p>
                </div>
                <div className="ml-auto flex gap-8">
                  {[
                    ["Root cause", run.aggregate_metrics?.root_cause_accuracy],
                    ["Dimension", run.aggregate_metrics?.dimension_accuracy],
                    ["Completion", run.aggregate_metrics?.completion_rate],
                  ].map(([label, value]) => (
                    <div key={String(label)} className="text-right">
                      <p className="eyebrow">{label}</p>
                      <p className="mt-1 font-mono text-sm tabular-nums">
                        {formatRate(value as number | undefined)}
                      </p>
                    </div>
                  ))}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
