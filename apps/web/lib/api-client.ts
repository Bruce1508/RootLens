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
      body && typeof body === "object" && "detail" in body ? String(body.detail) : null;
    throw new Error(detail ?? `Request to ${path} failed with status ${response.status}`);
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
