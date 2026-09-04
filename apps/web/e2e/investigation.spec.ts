import { expect, test } from "@playwright/test";

const INVESTIGATION_ID = "inv-e2e-1";
const EVIDENCE_ID = "ev-e2e-1";

const INVESTIGATION = {
  investigation_id: INVESTIGATION_ID,
  metric: "product_revenue",
  metric_definition_version: "product_revenue:v1",
  current_period: { start: "2018-01-01", end: "2018-01-31" },
  comparison_period: { start: "2017-12-01", end: "2017-12-31" },
  question: null,
  status: "completed",
  step_count: 5,
  query_count: 4,
  cancel_requested: false,
  created_at: "2018-02-01T00:00:00Z",
  updated_at: "2018-02-01T00:01:00Z",
  report: {
    status: "answered",
    headline: "Revenue decline concentrated in São Paulo",
    observed_change: {
      metric: "product_revenue",
      current_value: 750.0,
      comparison_value: 1000.0,
      percent_change: -0.25,
      evidence_ids: [EVIDENCE_ID],
    },
    findings: [
      {
        claim: "Revenue fell 25% compared to the prior period.",
        claim_type: "observed_fact",
        evidence_ids: [EVIDENCE_ID],
        confidence: "high",
      },
    ],
    limitations: ["Synthetic e2e fixture data only."],
    recommended_next_checks: [],
  },
};

const EVENTS = [
  {
    id: 1,
    event_type: "hypothesis_update",
    payload: {
      id: "hyp-1",
      statement: "The change is primarily driven by order_volume.",
      status: "supported",
      confidence: "high",
      supporting_evidence_ids: [EVIDENCE_ID],
      contradicting_evidence_ids: [],
    },
    created_at: "2018-02-01T00:00:30Z",
  },
  {
    id: 2,
    event_type: "tool_call",
    payload: { tool_name: "compare_periods" },
    created_at: "2018-02-01T00:00:45Z",
  },
];

const EVIDENCE = {
  evidence_id: EVIDENCE_ID,
  tool_name: "compare_periods",
  params: { metric: "product_revenue" },
  sql: "see app.analytics.compare_periods",
  columns: ["current_value", "comparison_value"],
  rows: [{ current_value: 750.0, comparison_value: 1000.0 }],
  row_count: 1,
  execution_ms: 12.3,
  warnings: [],
  created_at: "2018-02-01T00:00:20Z",
};

test("investigation page renders hypotheses, the report, and opens the evidence drawer", async ({
  page,
}) => {
  await page.route(`**/api/investigations/${INVESTIGATION_ID}`, async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(INVESTIGATION) });
  });
  await page.route(`**/api/investigations/${INVESTIGATION_ID}/events`, async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(EVENTS) });
  });
  await page.route(
    `**/api/investigations/${INVESTIGATION_ID}/evidence/${EVIDENCE_ID}`,
    async (route) => {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(EVIDENCE) });
    },
  );

  await page.goto(`/investigations/${INVESTIGATION_ID}`);

  await expect(page.getByTestId("investigation-status")).toHaveText("completed");
  await expect(page.getByText("supported")).toBeVisible();
  await expect(page.getByText("Revenue decline concentrated in São Paulo")).toBeVisible();
  await expect(page.getByText("Revenue fell 25% compared to the prior period.")).toBeVisible();

  await page.getByRole("button", { name: EVIDENCE_ID.slice(0, 8) }).click();

  const dialog = page.getByRole("dialog", { name: "Evidence detail" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText("compare_periods", { exact: true })).toBeVisible();
  await expect(dialog.getByRole("cell", { name: "750" })).toBeVisible();
});
