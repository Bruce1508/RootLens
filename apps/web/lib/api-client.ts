const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface MetricComparison {
  current_value: number;
  comparison_value: number;
  absolute_change: number;
  percent_change: number | null;
}

export interface MetricsSummary {
  product_revenue: MetricComparison;
  orders: MetricComparison;
}

export interface DateRangeResponse {
  min_date: string | null;
  max_date: string | null;
}

export type ReportStatus = "answered" | "partial" | "insufficient_evidence";
export type ClaimType = "observed_fact" | "interpretation";
export type Confidence = "low" | "medium" | "high";
export type InvestigationStatus =
  "running" | "completed" | "partial" | "failed" | "timed_out" | "cancelled";

export interface ObservedChange {
  metric: string;
  current_value: number;
  comparison_value: number;
  percent_change: number | null;
  evidence_ids: string[];
}

export interface ReportFinding {
  claim: string;
  claim_type: ClaimType;
  evidence_ids: string[];
  confidence: Confidence;
}

export interface InvestigationReport {
  status: ReportStatus;
  headline: string;
  observed_change: ObservedChange;
  findings: ReportFinding[];
  limitations: string[];
  recommended_next_checks: string[];
}

export interface DatePeriod {
  start: string;
  end: string;
}

export interface InvestigationView {
  investigation_id: string;
  metric: string;
  metric_definition_version: string;
  current_period: DatePeriod;
  comparison_period: DatePeriod;
  question: string | null;
  status: InvestigationStatus;
  step_count: number;
  query_count: number;
  created_at: string;
  updated_at: string;
  report: InvestigationReport | null;
}

export interface InvestigationEventView {
  id: number;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface EvidenceView {
  evidence_id: string;
  tool_name: string;
  params: Record<string, unknown>;
  sql: string;
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  execution_ms: number;
  warnings: string[];
  created_at: string;
}

export interface HypothesisPayload {
  id: string;
  statement: string;
  status: "untested" | "testing" | "supported" | "rejected" | "inconclusive";
  confidence: Confidence | null;
  supporting_evidence_ids: string[];
  contradicting_evidence_ids: string[];
}

export interface EvaluationRunView {
  run_id: string;
  model_name: string;
  split: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  aggregate_metrics: Record<string, number> | null;
}

export type CaseStatus = "pass" | "fail" | "abstained" | "execution_error";

export interface EvaluationCaseResultView {
  scenario_id: string;
  template: string | null;
  is_unanswerable: boolean | null;
  investigation_id: string | null;
  predicted_direction: string | null;
  predicted_primary_driver: string | null;
  predicted_dimensions: Record<string, string> | null;
  correct_driver: boolean | null;
  correct_dimension: boolean | null;
  abstained: boolean;
  expected_abstain: boolean;
  evidence_citation_valid: boolean;
  tool_execution_success: boolean;
  unsupported_claim_count: number;
  total_claim_count: number;
  tool_call_count: number;
  latency_ms: number | null;
  status: CaseStatus;
  notes: string | null;
}

export interface EvaluationRunDetailView extends EvaluationRunView {
  cases: EvaluationCaseResultView[];
}

async function fetchJson<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(path, API_BASE_URL);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      url.searchParams.set(key, value);
    }
  }

  const response = await fetch(url.toString());
  if (!response.ok) {
    // FastAPI's HTTPException responses carry the actual reason in
    // `detail` (e.g. a 422 for invalid input) — surface that instead of
    // a generic status-code message, which misleadingly reads as "the
    // backend is unreachable" even when it responded correctly.
    const body: unknown = await response.json().catch(() => null);
    const detail =
      body && typeof body === "object" && "detail" in body
        ? String(body.detail)
        : null;
    throw new Error(
      detail ?? `Request to ${path} failed with status ${response.status}`,
    );
  }
  return response.json() as Promise<T>;
}

export function getDateRange(): Promise<DateRangeResponse> {
  return fetchJson<DateRangeResponse>("/api/metadata/date-range");
}

export function getMetricsSummary(
  currentStart: string,
  currentEnd: string,
  comparisonStart: string,
  comparisonEnd: string,
): Promise<MetricsSummary> {
  return fetchJson<MetricsSummary>("/api/metrics/summary", {
    current_start: currentStart,
    current_end: currentEnd,
    comparison_start: comparisonStart,
    comparison_end: comparisonEnd,
  });
}

export function getInvestigation(
  investigationId: string,
): Promise<InvestigationView> {
  return fetchJson<InvestigationView>(`/api/investigations/${investigationId}`);
}

export function getInvestigationEvents(
  investigationId: string,
): Promise<InvestigationEventView[]> {
  return fetchJson<InvestigationEventView[]>(
    `/api/investigations/${investigationId}/events`,
  );
}

export function getEvidence(
  investigationId: string,
  evidenceId: string,
): Promise<EvidenceView> {
  return fetchJson<EvidenceView>(
    `/api/investigations/${investigationId}/evidence/${evidenceId}`,
  );
}

export function getEvaluations(): Promise<EvaluationRunView[]> {
  return fetchJson<EvaluationRunView[]>("/api/evaluations");
}

export function getEvaluation(runId: string): Promise<EvaluationRunDetailView> {
  return fetchJson<EvaluationRunDetailView>(`/api/evaluations/${runId}`);
}
