import { expect, test } from "@playwright/test";

test("dashboard loads and shows KPI cards from the mocked metrics summary", async ({ page }) => {
  await page.route("**/api/metrics/summary*", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        product_revenue: {
          current_value: 150.0,
          comparison_value: 250.0,
          absolute_change: -100.0,
          percent_change: -0.4,
        },
        orders: {
          current_value: 2,
          comparison_value: 3,
          absolute_change: -1,
          percent_change: -0.3333,
        },
      }),
    });
  });

  await page.goto("/");

  await expect(page.getByText("RootLens")).toBeVisible();
  await expect(page.getByText("Product revenue")).toBeVisible();
  await expect(page.getByText("$150.00")).toBeVisible();
  await expect(page.getByText("-40.0%")).toBeVisible();
  await expect(page.getByText("Orders")).toBeVisible();
  await expect(page.getByText("2", { exact: true })).toBeVisible();
});

test("dashboard shows a clear error when the backend is unreachable", async ({ page }) => {
  await page.route("**/api/metrics/summary*", async (route) => {
    await route.abort("connectionrefused");
  });

  await page.goto("/");

  await expect(page.getByText(/backend running/)).toBeVisible();
});
