import { expect, test } from "@playwright/test";

const RUN_ID = "run-e2e-1";
const INVESTIGATION_ID = "inv-e2e-2";

const RUN_LIST = [
  {
    run_id: RUN_ID,
    model_name: "qwen3:8b",
    split: "held_out",
    status: "completed",
    started_at: "2018-02-01T00:00:00Z",
    completed_at: "2018-02-01T00:05:00Z",
    aggregate_metrics: {
      scenario_count: 2,
      root_cause_accuracy: 0.5,
      dimension_accuracy: 0.5,
      evidence_citation_validity_rate: 1.0,
      tool_execution_success_rate: 1.0,
      unsupported_claim_rate: 0.0,
      abstention_accuracy: 1.0,
      average_tool_calls: 5.0,
      average_latency_ms: 20000.0,
      completion_rate: 1.0,
    },
  },
];

const RUN_DETAIL = {
  ...RUN_LIST[0],
  cases: [
    {
      scenario_id: "cs-01",
      template: "cancellation_spike",
      is_unanswerable: false,
      investigation_id: INVESTIGATION_ID,
      predicted_direction: "decrease",
      predicted_primary_driver: "cancellation",
      predicted_dimensions: { customer_state: "SP" },
      correct_driver: true,
      correct_dimension: true,
      abstained: false,
      expected_abstain: false,
      evidence_citation_valid: true,
      tool_execution_success: true,
      unsupported_claim_count: 0,
      total_claim_count: 2,
      tool_call_count: 5,
      latency_ms: 18000.0,
      status: "pass",
      notes: null,
    },
    {
      scenario_id: "ua-01",
      template: "order_volume_decline",
      is_unanswerable: true,
      investigation_id: null,
      predicted_direction: null,
      predicted_primary_driver: null,
      predicted_dimensions: null,
      correct_driver: null,
      correct_dimension: null,
      abstained: true,
      expected_abstain: true,
      evidence_citation_valid: true,
      tool_execution_success: true,
      unsupported_claim_count: 0,
      total_claim_count: 0,
      tool_call_count: 3,
      latency_ms: 12000.0,
      status: "abstained",
      notes: null,
    },
  ],
};

const INVESTIGATION_STUB = {
  investigation_id: INVESTIGATION_ID,
  metric: "product_revenue",
  metric_definition_version: "product_revenue:v1",
  current_period: { start: "2017-09-01", end: "2017-09-30" },
  comparison_period: { start: "2017-08-01", end: "2017-08-31" },
  question: null,
  status: "completed",
  step_count: 5,
  query_count: 4,
  cancel_requested: false,
  created_at: "2018-02-01T00:00:00Z",
  updated_at: "2018-02-01T00:01:00Z",
  report: null,
};

test("evaluations list navigates to detail, filters cases, and replays an investigation", async ({
  page,
}) => {
  await page.route("**/api/evaluations", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(RUN_LIST) });
  });
  await page.route(`**/api/evaluations/${RUN_ID}`, async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(RUN_DETAIL) });
  });
  await page.route(`**/api/investigations/${INVESTIGATION_ID}`, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(INVESTIGATION_STUB),
    });
  });
  await page.route(`**/api/investigations/${INVESTIGATION_ID}/events`, async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify([]) });
  });

  await page.goto("/evaluations");
  await expect(page.getByText("qwen3:8b — held_out")).toBeVisible();

  await page.getByText("qwen3:8b — held_out").click();
  await expect(page).toHaveURL(`/evaluations/${RUN_ID}`);
  await expect(page.getByText("Root cause accuracy")).toBeVisible();
  await expect(page.getByRole("cell", { name: "cs-01" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "ua-01" })).toBeVisible();

  await page.getByRole("button", { name: "abstained", exact: true }).click();
  await expect(page.getByRole("cell", { name: "ua-01" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "cs-01" })).not.toBeVisible();

  await page.getByRole("button", { name: "all", exact: true }).click();
  await page.getByRole("link", { name: "view" }).click();
  await expect(page).toHaveURL(`/investigations/${INVESTIGATION_ID}`);
  await expect(page.getByTestId("investigation-status")).toHaveText("completed");
});
