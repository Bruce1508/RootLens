import { afterEach, describe, expect, it, vi } from "vitest";
import { getMetricsSummary } from "@/lib/api-client";

describe("getMetricsSummary", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("throws the backend's detail message on a 4xx response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        json: () => Promise.resolve({ detail: "periods overlap: current=2018-01-01..2018-01-31" }),
      }),
    );

    await expect(
      getMetricsSummary("2018-01-01", "2018-01-31", "2018-01-01", "2018-01-31"),
    ).rejects.toThrow("periods overlap: current=2018-01-01..2018-01-31");
  });

  it("falls back to a generic message when the response has no detail field", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: () => Promise.resolve({}),
      }),
    );

    await expect(
      getMetricsSummary("2018-01-01", "2018-01-31", "2017-12-01", "2017-12-31"),
    ).rejects.toThrow("Request to /api/metrics/summary failed with status 500");
  });
});
