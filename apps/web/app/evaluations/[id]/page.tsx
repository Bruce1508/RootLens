"use client";

import Link from "next/link";
import { use, useEffect, useMemo, useState } from "react";
import {
  getEvaluation,
  type CaseStatus,
  type EvaluationRunDetailView,
} from "@/lib/api-client";

const METRIC_LABELS: Record<string, string> = {
  root_cause_accuracy: "Root cause accuracy",
  dimension_accuracy: "Dimension accuracy",
  evidence_citation_validity_rate: "Evidence citation validity",
  tool_execution_success_rate: "Tool execution success",
  unsupported_claim_rate: "Unsupported claim rate",
  abstention_accuracy: "Abstention accuracy",
  average_tool_calls: "Avg. tool calls",
  average_latency_ms: "Avg. latency (ms)",
  completion_rate: "Completion rate",
  scenario_count: "Scenarios",
};

const STATUS_FILTERS: (CaseStatus | "all")[] = ["all", "pass", "fail", "abstained", "execution_error"];

const STATUS_STYLES: Record<CaseStatus, string> = {
  pass: "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300",
  fail: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
  abstained: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  execution_error: "bg-neutral-200 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300",
};

function formatMetricValue(key: string, value: number): string {
  if (key.endsWith("_rate") || key.endsWith("_accuracy")) {
    return `${(value * 100).toFixed(1)}%`;
  }
  if (key === "average_latency_ms") {
    return value.toFixed(0);
  }
  if (key === "average_tool_calls") {
    return value.toFixed(1);
  }
  return String(value);
}

export default function EvaluationDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);

  const [run, setRun] = useState<EvaluationRunDetailView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<CaseStatus | "all">("all");

  useEffect(() => {
    getEvaluation(id)
      .then(setRun)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Failed to load evaluation run"),
      );
  }, [id]);

  const filteredCases = useMemo(() => {
    if (!run) return [];
    return filter === "all" ? run.cases : run.cases.filter((c) => c.status === filter);
  }, [run, filter]);

  if (error) {
    return (
      <main className="mx-auto max-w-4xl p-8">
        <p className="text-sm text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      </main>
    );
  }

  if (!run) {
    return (
      <main className="mx-auto max-w-4xl p-8">
        <p className="text-sm text-neutral-500">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl p-8">
      <h1 className="text-xl font-semibold">
        {run.model_name} — {run.split}
      </h1>
      <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
        {new Date(run.started_at).toLocaleString()} · {run.status}
      </p>

      {run.aggregate_metrics && (
        <div className="mt-6 grid grid-cols-3 gap-3">
          {Object.entries(run.aggregate_metrics).map(([key, value]) => (
            <div
              key={key}
              className="rounded-lg border border-neutral-200 p-3 text-sm dark:border-neutral-800"
            >
              <p className="text-xs text-neutral-500 dark:text-neutral-400">
                {METRIC_LABELS[key] ?? key}
              </p>
              <p className="mt-1 text-lg font-semibold">{formatMetricValue(key, value)}</p>
            </div>
          ))}
        </div>
      )}

      <div className="mt-6 flex gap-2">
        {STATUS_FILTERS.map((status) => (
          <button
            key={status}
            type="button"
            onClick={() => setFilter(status)}
            className={`rounded px-2 py-1 text-xs font-medium ${
              filter === status
                ? "bg-neutral-800 text-white dark:bg-neutral-200 dark:text-neutral-900"
                : "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400"
            }`}
          >
            {status}
          </button>
        ))}
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr>
              <th className="border-b border-neutral-200 px-2 py-1 text-left dark:border-neutral-800">
                Scenario
              </th>
              <th className="border-b border-neutral-200 px-2 py-1 text-left dark:border-neutral-800">
                Template
              </th>
              <th className="border-b border-neutral-200 px-2 py-1 text-left dark:border-neutral-800">
                Predicted driver
              </th>
              <th className="border-b border-neutral-200 px-2 py-1 text-left dark:border-neutral-800">
                Status
              </th>
              <th className="border-b border-neutral-200 px-2 py-1 text-left dark:border-neutral-800">
                Replay
              </th>
            </tr>
          </thead>
          <tbody>
            {filteredCases.map((c) => (
              <tr key={c.scenario_id}>
                <td className="border-b border-neutral-100 px-2 py-1 font-mono text-xs dark:border-neutral-900">
                  {c.scenario_id}
                </td>
                <td className="border-b border-neutral-100 px-2 py-1 text-xs dark:border-neutral-900">
                  {c.template ?? "—"}
                </td>
                <td className="border-b border-neutral-100 px-2 py-1 text-xs dark:border-neutral-900">
                  {c.predicted_primary_driver ?? "—"}
                </td>
                <td className="border-b border-neutral-100 px-2 py-1 dark:border-neutral-900">
                  <span
                    className={`rounded px-1.5 py-0.5 text-xs font-medium ${STATUS_STYLES[c.status]}`}
                  >
                    {c.status}
                  </span>
                </td>
                <td className="border-b border-neutral-100 px-2 py-1 dark:border-neutral-900">
                  {c.investigation_id ? (
                    <Link
                      href={`/investigations/${c.investigation_id}`}
                      className="text-blue-600 underline dark:text-blue-400"
                    >
                      view
                    </Link>
                  ) : (
                    <span className="text-xs text-neutral-400">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
