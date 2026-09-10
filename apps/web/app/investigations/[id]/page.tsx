"use client";

import { use, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { EvidenceDrawer } from "@/components/evidence-drawer";
import { EvidenceLedger, type Exhibit } from "@/components/evidence-ledger";
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

const STATUS_STYLES: Record<string, string> = {
  running: "text-signal",
  completed: "text-positive",
  partial: "text-caution",
  failed: "text-negative",
  timed_out: "text-negative",
  cancelled: "text-faint",
};

function latestHypotheses(events: InvestigationEventView[]): HypothesisPayload[] {
  const byId = new Map<string, HypothesisPayload>();
  for (const event of events) {
    if (event.event_type !== "hypothesis_update") continue;
    const hypothesis = event.payload as unknown as HypothesisPayload;
    byId.set(hypothesis.id, hypothesis);
  }
  return Array.from(byId.values());
}

/** Every executed query becomes a numbered exhibit, in execution order.
    The ordinal — not the uuid — is how a reader refers to evidence, so the
    ledger deliberately never renders the raw id. */
function exhibitsFrom(events: InvestigationEventView[]): Exhibit[] {
  const exhibits: Exhibit[] = [];
  for (const event of events) {
    if (event.event_type !== "tool_call") continue;
    const { evidence_id, tool_name, row_count, execution_ms } = event.payload;
    if (typeof evidence_id !== "string" || typeof tool_name !== "string") continue;
    exhibits.push({
      evidenceId: evidence_id,
      ordinal: exhibits.length + 1,
      toolName: tool_name,
      rowCount: typeof row_count === "number" ? row_count : 0,
      executionMs: typeof execution_ms === "number" ? execution_ms : 0,
    });
  }
  return exhibits;
}

export default function InvestigationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);

  const [investigation, setInvestigation] = useState<InvestigationView | null>(null);
  const [events, setEvents] = useState<InvestigationEventView[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<EvidenceView | null>(null);
  const [isEvidenceLoading, setIsEvidenceLoading] = useState(false);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);

  const [linkedEvidenceId, setLinkedEvidenceId] = useState<string | null>(null);

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
      setError(err instanceof Error ? err.message : "Failed to load investigation");
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
        setEvidenceError(err instanceof Error ? err.message : "Failed to load evidence");
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

  const exhibits = useMemo(() => exhibitsFrom(events), [events]);
  const ordinalByEvidenceId = useMemo(
    () => new Map(exhibits.map((exhibit) => [exhibit.evidenceId, exhibit.ordinal])),
    [exhibits],
  );

  if (isLoading) {
    return (
      <main className="mx-auto max-w-6xl px-6 py-10">
        <p className="font-mono text-xs text-faint">Loading…</p>
      </main>
    );
  }

  if (error || !investigation) {
    return (
      <main className="mx-auto max-w-6xl px-6 py-10">
        <p className="text-sm text-negative" role="alert">
          {error ?? "Investigation not found"}
        </p>
      </main>
    );
  }

  const hypotheses = latestHypotheses(events);
  const report = investigation.report;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line pb-6">
        <div>
          <p className="eyebrow">{investigation.metric}</p>
          <h1 className="mt-2 font-mono text-2xl tracking-tight tabular-nums">
            {investigation.current_period.start} → {investigation.current_period.end}
          </h1>
          <p className="mt-1.5 font-mono text-xs text-faint tabular-nums">
            compared with {investigation.comparison_period.start} →{" "}
            {investigation.comparison_period.end}
          </p>
          {investigation.question && (
            <p className="mt-3 max-w-xl text-sm text-muted">
              &ldquo;{investigation.question}&rdquo;
            </p>
          )}
        </div>
        <div className="flex items-center gap-3">
          {investigation.status === "running" && (
            <button
              type="button"
              onClick={handleCancel}
              disabled={isCancelling || investigation.cancel_requested}
              className="rounded border border-line px-2.5 py-1.5 font-mono text-xs text-muted transition-colors hover:border-line-strong hover:text-ink disabled:opacity-50"
            >
              {investigation.cancel_requested ? "Cancelling…" : "Cancel"}
            </button>
          )}
          <span
            data-testid="investigation-status"
            className={`font-mono text-xs font-medium tracking-wider uppercase ${
              STATUS_STYLES[investigation.status] ?? "text-faint"
            }`}
          >
            {investigation.status}
          </span>
        </div>
      </div>

      {/* The two columns are the product's central claim: everything on the
          left is an assertion, everything on the right is the executed
          query behind it. */}
      <div className="mt-8 grid gap-10 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="space-y-10">
          <section>
            <h2 className="eyebrow">Hypotheses</h2>
            <div className="mt-3">
              <HypothesisPanel hypotheses={hypotheses} />
            </div>
          </section>

          {report && (
            <section>
              <h2 className="eyebrow">Report</h2>
              <div className="mt-3 rounded border border-line bg-surface p-6">
                <p className="font-serif text-2xl leading-snug tracking-tight text-balance">
                  {report.headline}
                </p>

                <div className="mt-6 flex gap-10 border-y border-line py-4">
                  <div>
                    <p className="eyebrow">Current</p>
                    <p className="mt-1 font-mono text-lg tabular-nums">
                      {formatCurrency(report.observed_change.current_value)}
                    </p>
                  </div>
                  <div>
                    <p className="eyebrow">Change</p>
                    <p className="mt-1 font-mono text-lg tabular-nums">
                      {formatPercentChange(report.observed_change.percent_change)}
                    </p>
                  </div>
                </div>

                <ul className="mt-5 space-y-5">
                  {report.findings.map((finding, index) => (
                    // Findings have no stable id — index is fine, this list
                    // never reorders after the report is generated.

                    <li key={index}>
                      <p className="font-serif text-base leading-relaxed">{finding.claim}</p>
                      <div className="mt-2 flex flex-wrap items-center gap-2 font-mono text-xs">
                        <span className="text-faint">
                          {finding.claim_type} · {finding.confidence}
                        </span>
                        {finding.evidence_ids.map((evidenceId) => {
                          const ordinal = ordinalByEvidenceId.get(evidenceId);
                          const isLinked = evidenceId === linkedEvidenceId;
                          return (
                            <button
                              key={evidenceId}
                              type="button"
                              onClick={() => openEvidence(evidenceId)}
                              onMouseEnter={() => setLinkedEvidenceId(evidenceId)}
                              onMouseLeave={() => setLinkedEvidenceId(null)}
                              onFocus={() => setLinkedEvidenceId(evidenceId)}
                              onBlur={() => setLinkedEvidenceId(null)}
                              className={`flex items-baseline gap-1.5 rounded border px-1.5 py-0.5 transition-colors ${
                                isLinked
                                  ? "border-signal text-signal"
                                  : "border-line text-muted hover:border-line-strong hover:text-ink"
                              }`}
                            >
                              {/* The ordinal is what makes the citation
                                  findable in the ledger without hovering;
                                  the id stays visible because it is what
                                  the API and the report contract actually
                                  key on. */}
                              {ordinal && <span className="font-medium">E{ordinal}</span>}
                              <span className={isLinked ? "" : "text-faint"}>
                                {evidenceId.slice(0, 8)}
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    </li>
                  ))}
                </ul>

                {report.limitations.length > 0 && (
                  <div className="mt-6 border-t border-line pt-4">
                    <p className="eyebrow">Limitations</p>
                    <ul className="mt-2 space-y-1">
                      {report.limitations.map((limitation) => (
                        <li key={limitation} className="text-sm text-muted">
                          {limitation}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </section>
          )}
        </div>

        {/* The right rail is everything the machine did — the step trace and
            the queries it ran. The left column is what it is willing to
            claim off the back of that. */}
        <aside className="space-y-8 lg:sticky lg:top-8 lg:self-start">
          <section>
            <h2 className="eyebrow">
              Trace · {investigation.step_count} steps · {investigation.query_count} queries
            </h2>
            <ol className="mt-3 space-y-1.5">
              {events.map((event) => (
                <li key={event.id} className="font-mono text-xs">
                  {event.event_type === "tool_call" &&
                  typeof event.payload.tool_name === "string" ? (
                    <span className="text-signal">{event.payload.tool_name}</span>
                  ) : (
                    <span className="text-faint">{event.event_type}</span>
                  )}
                </li>
              ))}
            </ol>
          </section>

          <EvidenceLedger
            exhibits={exhibits}
            linkedEvidenceId={linkedEvidenceId}
            onHoverExhibit={setLinkedEvidenceId}
            onOpenExhibit={openEvidence}
          />
        </aside>
      </div>

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
