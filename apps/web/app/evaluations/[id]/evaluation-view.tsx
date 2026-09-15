"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getEvaluation, type CaseStatus, type EvaluationRunDetailView } from "@/lib/api-client";

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

const STATUS_FILTERS: (CaseStatus | "all")[] = [
  "all",
  "pass",
  "fail",
  "abstained",
  "execution_error",
];

const STATUS_STYLES: Record<CaseStatus, string> = {
  pass: "text-positive",
  fail: "text-negative",
  abstained: "text-caution",
  execution_error: "text-faint",
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

export function EvaluationView({ id }: { id: string }) {
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
      <main className="mx-auto max-w-5xl px-6 py-10">
        <p className="text-sm text-negative" role="alert">
          {error}
        </p>
      </main>
    );
  }

  if (!run) {
    return (
      <main className="mx-auto max-w-5xl px-6 py-10">
        <p className="font-mono text-xs text-faint">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <div className="border-b border-line pb-6">
        <h1 className="font-mono text-2xl tracking-tight">
          {run.model_name} — {run.split}
        </h1>
        <p className="mt-1.5 font-mono text-xs text-faint tabular-nums">
          {new Date(run.started_at).toLocaleString()} · {run.status}
        </p>
      </div>

      {run.aggregate_metrics && (
        <div className="mt-8 grid grid-cols-2 gap-x-8 gap-y-6 sm:grid-cols-3 lg:grid-cols-5">
          {Object.entries(run.aggregate_metrics).map(([key, value]) => (
            <div key={key} className="border-l-2 border-line-strong pl-3">
              <p className="eyebrow">{METRIC_LABELS[key] ?? key}</p>
              <p className="mt-1.5 font-mono text-xl tabular-nums">
                {formatMetricValue(key, value)}
              </p>
            </div>
          ))}
        </div>
      )}

      <div className="mt-10 flex flex-wrap gap-2">
        {STATUS_FILTERS.map((status) => (
          <button
            key={status}
            type="button"
            onClick={() => setFilter(status)}
            className={`rounded border px-2.5 py-1 font-mono text-xs transition-colors ${
              filter === status
                ? "border-signal text-signal"
                : "border-line text-muted hover:border-line-strong hover:text-ink"
            }`}
          >
            {status}
          </button>
        ))}
      </div>

      <div className="mt-5 overflow-x-auto">
        <table className="w-full border-collapse font-mono text-xs">
          <thead>
            <tr>
              {["Scenario", "Template", "Predicted driver", "Status", "Replay"].map((heading) => (
                <th
                  key={heading}
                  className="border-b border-line-strong px-2 py-2 text-left font-medium tracking-wider text-faint uppercase"
                >
                  {heading}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredCases.map((c) => (
              <tr key={c.scenario_id} className="transition-colors hover:bg-surface">
                <td className="border-b border-line px-2 py-2 text-ink">{c.scenario_id}</td>
                <td className="border-b border-line px-2 py-2 text-muted">{c.template ?? "—"}</td>
                <td className="border-b border-line px-2 py-2 text-muted">
                  {c.predicted_primary_driver ?? "—"}
                </td>
                <td className={`border-b border-line px-2 py-2 ${STATUS_STYLES[c.status]}`}>
                  {c.status}
                </td>
                <td className="border-b border-line px-2 py-2">
                  {c.investigation_id ? (
                    <Link
                      href={`/investigations/${c.investigation_id}`}
                      className="text-signal transition-opacity hover:opacity-80"
                    >
                      view
                    </Link>
                  ) : (
                    <span className="text-faint">—</span>
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
