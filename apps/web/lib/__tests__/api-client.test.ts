import { afterEach, describe, expect, it, vi } from "vitest";
import {
  cancelInvestigation,
  getEvaluation,
  getEvaluations,
  getEvidence,
  getInvestigation,
  getInvestigationEvents,
  getInvestigations,
  getMetricsSummary,
} from "@/lib/api-client";

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
        json: () =>
          Promise.resolve({
            detail: "periods overlap: current=2018-01-01..2018-01-31",
          }),
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

describe("getInvestigation", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the parsed investigation on success", async () => {
    const body = { investigation_id: "inv-1", status: "completed" };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve(body),
      }),
    );

    const result = await getInvestigation("inv-1");
    expect(result).toEqual(body);
  });

  it("throws a 404 not-found detail message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: "investigation not found" }),
      }),
    );

    await expect(getInvestigation("does-not-exist")).rejects.toThrow(
      "investigation not found",
    );
  });
});

describe("getInvestigationEvents", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the parsed event list", async () => {
    const body = [
      { id: 1, event_type: "tool_call", payload: {}, created_at: "2018-01-01" },
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve(body),
      }),
    );

    const result = await getInvestigationEvents("inv-1");
    expect(result).toEqual(body);
  });
});

describe("getEvidence", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the parsed evidence on success", async () => {
    const body = {
      evidence_id: "ev-1",
      tool_name: "compare_periods",
      rows: [],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve(body),
      }),
    );

    const result = await getEvidence("inv-1", "ev-1");
    expect(result).toEqual(body);
  });

  it("throws a 404 not-found detail message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: "evidence not found" }),
      }),
    );

    await expect(getEvidence("inv-1", "does-not-exist")).rejects.toThrow(
      "evidence not found",
    );
  });
});

describe("getEvaluations", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the parsed list of runs", async () => {
    const body = [{ run_id: "run-1", model_name: "qwen3:8b", status: "completed" }];
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve(body) }),
    );

    const result = await getEvaluations();
    expect(result).toEqual(body);
  });
});

describe("getEvaluation", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the parsed run detail", async () => {
    const body = { run_id: "run-1", model_name: "qwen3:8b", cases: [] };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve(body) }),
    );

    const result = await getEvaluation("run-1");
    expect(result).toEqual(body);
  });

  it("throws a 404 not-found detail message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: "evaluation run not found" }),
      }),
    );

    await expect(getEvaluation("does-not-exist")).rejects.toThrow("evaluation run not found");
  });
});

describe("cancelInvestigation", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts to the cancel endpoint and returns the updated investigation", async () => {
    const body = { investigation_id: "inv-1", status: "running", cancel_requested: true };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(body),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await cancelInvestigation("inv-1");

    expect(result).toEqual(body);
    const [, init] = fetchMock.mock.calls[0];
    expect(init).toEqual({ method: "POST" });
  });
});

describe("fetchJson in demo mode", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    delete process.env.NEXT_PUBLIC_DEMO_MODE;
  });

  it("resolves from the demo fixture manifest instead of calling the real API", async () => {
    process.env.NEXT_PUBLIC_DEMO_MODE = "1";
    const manifest = [{ key: "GET /api/investigations", file: "investigations-list.json" }];
    const fixture = [{ investigation_id: "inv-1", status: "completed" }];

    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url === "/demo/manifest.json") {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(manifest) });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve(fixture) });
      }),
    );

    const result = await getInvestigations();
    expect(result).toEqual(fixture);
  });
});
