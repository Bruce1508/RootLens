"use client";

import { use, useCallback, useEffect, useRef, useState } from "react";
import { EvidenceDrawer } from "@/components/evidence-drawer";
import { HypothesisPanel } from "@/components/hypothesis-panel";
import {
  cancelInvestigation,
  getEvidence,
  getInvestigation,
  getInvestigationEvents,
  type EvidenceView,
  type HypothesisPayload,
  type InvestigationEventView,
  type InvestigationView,
} from "@/lib/api-client";
import { formatCurrency, formatPercentChange } from "@/lib/format";

const RUNNING_POLL_INTERVAL_MS = 2000;

const STATUS_BADGE_STYLES: Record<string, string> = {
  running: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  completed:
    "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300",
  partial: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  failed: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
  timed_out: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
  cancelled:
    "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400",
};

function latestHypotheses(
  events: InvestigationEventView[],
): HypothesisPayload[] {
  const byId = new Map<string, HypothesisPayload>();
  for (const event of events) {
    if (event.event_type !== "hypothesis_update") continue;
    const hypothesis = event.payload as unknown as HypothesisPayload;
    byId.set(hypothesis.id, hypothesis);
  }
  return Array.from(byId.values());
}

export default function InvestigationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  const [investigation, setInvestigation] = useState<InvestigationView | null>(
    null,
  );
  const [events, setEvents] = useState<InvestigationEventView[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(
    null,
  );
  const [evidence, setEvidence] = useState<EvidenceView | null>(null);
  const [isEvidenceLoading, setIsEvidenceLoading] = useState(false);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const [investigationData, eventsData] = await Promise.all([
        getInvestigation(id),
        getInvestigationEvents(id),
      ]);
      setInvestigation(investigationData);
      setEvents(eventsData);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load investigation",
      );
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (investigation?.status === "running") {
      pollRef.current = setInterval(load, RUNNING_POLL_INTERVAL_MS);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [investigation?.status, load]);

  const openEvidence = useCallback(
    async (evidenceId: string) => {
      setSelectedEvidenceId(evidenceId);
      setIsEvidenceLoading(true);
      setEvidenceError(null);
      try {
        const data = await getEvidence(id, evidenceId);
        setEvidence(data);
      } catch (err) {
        setEvidenceError(
          err instanceof Error ? err.message : "Failed to load evidence",
        );
      } finally {
        setIsEvidenceLoading(false);
      }
    },
    [id],
  );

  const closeEvidence = useCallback(() => {
    setSelectedEvidenceId(null);
    setEvidence(null);
    setEvidenceError(null);
  }, []);

  const [isCancelling, setIsCancelling] = useState(false);
  const handleCancel = useCallback(async () => {
    setIsCancelling(true);
    try {
      const updated = await cancelInvestigation(id);
      setInvestigation(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to cancel investigation");
    } finally {
      setIsCancelling(false);
    }
  }, [id]);

  if (isLoading) {
    return (
      <main className="mx-auto max-w-3xl p-8">
        <p className="text-sm text-neutral-500">Loading…</p>
      </main>
    );
  }

  if (error || !investigation) {
    return (
      <main className="mx-auto max-w-3xl p-8">
        <p className="text-sm text-red-600 dark:text-red-400" role="alert">
          {error ?? "Investigation not found"}
        </p>
      </main>
    );
  }

  const hypotheses = latestHypotheses(events);
  const report = investigation.report;

  return (
    <main className="mx-auto max-w-3xl p-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">
            {investigation.metric} — {investigation.current_period.start}..
            {investigation.current_period.end}
          </h1>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            vs {investigation.comparison_period.start}..
            {investigation.comparison_period.end}
          </p>
          {investigation.question && (
            <p className="mt-2 text-sm text-neutral-700 dark:text-neutral-300">
              &ldquo;{investigation.question}&rdquo;
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {investigation.status === "running" && (
            <button
              type="button"
              onClick={handleCancel}
              disabled={isCancelling || investigation.cancel_requested}
              className="rounded border border-neutral-300 px-2 py-1 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-50 dark:border-neutral-700 dark:text-neutral-400 dark:hover:bg-neutral-900"
            >
              {investigation.cancel_requested ? "Cancelling…" : "Cancel"}
            </button>
          )}
          <span
            data-testid="investigation-status"
            className={`rounded px-2 py-1 text-xs font-medium ${
              STATUS_BADGE_STYLES[investigation.status] ??
              STATUS_BADGE_STYLES.cancelled
            }`}
          >
            {investigation.status}
          </span>
        </div>
      </div>

      <section className="mt-6">
        <h2 className="text-sm font-semibold text-neutral-500 dark:text-neutral-400">
          Hypotheses
        </h2>
        <div className="mt-2">
          <HypothesisPanel hypotheses={hypotheses} />
        </div>
      </section>

      <section className="mt-6">
        <h2 className="text-sm font-semibold text-neutral-500 dark:text-neutral-400">
          Live trace ({investigation.step_count} steps,{" "}
          {investigation.query_count} queries)
        </h2>
        <ol className="mt-2 space-y-1 text-sm">
          {events.map((event) => (
            <li
              key={event.id}
              className="text-neutral-600 dark:text-neutral-400"
            >
              <span className="font-mono text-xs">{event.event_type}</span>
              {event.event_type === "tool_call" &&
                typeof event.payload.tool_name === "string" &&
                ` — ${event.payload.tool_name}`}
            </li>
          ))}
        </ol>
      </section>

      {report && (
        <section className="mt-6">
          <h2 className="text-sm font-semibold text-neutral-500 dark:text-neutral-400">
            Report
          </h2>
          <div className="mt-2 rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
            <p className="font-medium">{report.headline}</p>

            <div className="mt-3 grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-neutral-500 dark:text-neutral-400">
                  Current
                </p>
                <p>{formatCurrency(report.observed_change.current_value)}</p>
              </div>
              <div>
                <p className="text-neutral-500 dark:text-neutral-400">Change</p>
                <p>
                  {formatPercentChange(report.observed_change.percent_change)}
                </p>
              </div>
            </div>

            <ul className="mt-4 space-y-2 text-sm">
              {report.findings.map((finding, index) => (
                // Findings have no stable id — index is fine, this list
                // never reorders after the report is generated.

                <li key={index}>
                  <p>{finding.claim}</p>
                  <div className="mt-1 flex flex-wrap items-center gap-1 text-xs">
                    <span className="text-neutral-500 dark:text-neutral-400">
                      {finding.claim_type} · {finding.confidence}
                    </span>
                    {finding.evidence_ids.map((evidenceId) => (
                      <button
                        key={evidenceId}
                        type="button"
                        onClick={() => openEvidence(evidenceId)}
                        className="rounded bg-neutral-100 px-1.5 py-0.5 font-mono text-neutral-700 hover:bg-neutral-200 dark:bg-neutral-800 dark:text-neutral-300 dark:hover:bg-neutral-700"
                      >
                        {evidenceId.slice(0, 8)}
                      </button>
                    ))}
                  </div>
                </li>
              ))}
            </ul>

            {report.limitations.length > 0 && (
              <div className="mt-4 text-sm">
                <p className="text-neutral-500 dark:text-neutral-400">
                  Limitations
                </p>
                <ul className="list-inside list-disc">
                  {report.limitations.map((limitation) => (
                    <li key={limitation}>{limitation}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </section>
      )}

      {selectedEvidenceId && (
        <EvidenceDrawer
          evidence={evidence}
          isLoading={isEvidenceLoading}
          error={evidenceError}
          onClose={closeEvidence}
        />
      )}
    </main>
  );
}
