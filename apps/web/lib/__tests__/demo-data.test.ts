import { afterEach, describe, expect, it, vi } from "vitest";
import { buildDemoKey, resolveDemoFixture } from "@/lib/demo-data";

describe("buildDemoKey", () => {
  it("returns a plain method-and-path key when there are no params", () => {
    expect(buildDemoKey("GET", "/api/investigations")).toBe("GET /api/investigations");
  });

  it("sorts params so callers passing them in a different order collide on the same key", () => {
    const a = buildDemoKey("GET", "/api/metrics/summary", {
      current_start: "2018-01-01",
      comparison_start: "2017-12-01",
    });
    const b = buildDemoKey("GET", "/api/metrics/summary", {
      comparison_start: "2017-12-01",
      current_start: "2018-01-01",
    });
    expect(a).toBe(b);
    expect(a).toBe(
      "GET /api/metrics/summary?comparison_start=2017-12-01&current_start=2018-01-01",
    );
  });
});

describe("resolveDemoFixture", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches the manifest, then the matching fixture file", async () => {
    const manifest = [{ key: "GET /api/investigations", file: "investigations-list.json" }];
    const fixture = [{ investigation_id: "inv-1", status: "completed" }];

    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url === "/demo/manifest.json") {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(manifest) });
        }
        if (url === "/demo/investigations-list.json") {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(fixture) });
        }
        throw new Error(`unexpected fetch: ${url}`);
      }),
    );

    const result = await resolveDemoFixture("GET", "/api/investigations");
    expect(result).toEqual(fixture);
  });

  it("throws when no manifest entry matches the request", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve([]) }),
    );

    await expect(resolveDemoFixture("GET", "/api/investigations")).rejects.toThrow(
      "Demo fixture not found for GET /api/investigations",
    );
  });

  it("throws when the manifest itself fails to load", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));

    await expect(resolveDemoFixture("GET", "/api/investigations")).rejects.toThrow(
      "Failed to load /demo/manifest.json: 500",
    );
  });
});
