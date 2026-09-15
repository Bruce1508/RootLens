import { expect, test } from "@playwright/test";

test("landing investigation renders with a working citation, and controls are disabled", async ({
  page,
}) => {
  await page.goto("/");

  await expect(page.getByText(/Read-only demo/)).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Investigate revenue change" }),
  ).toBeDisabled();

  await page.locator('a[href^="/investigations/"]').first().click();

  await expect(page.getByTestId("investigation-status")).toHaveText("completed");

  // Two elements match "E1": the finding's inline citation and the sidebar
  // Evidence Ledger's exhibit entry — both call openEvidence() for the same
  // evidence id, so .first() (the inline citation, first in DOM order)
  // exercises the same citation flow deterministically.
  const firstCitation = page.getByRole("button", { name: /^E1/ }).first();
  await firstCitation.click();

  const dialog = page.getByRole("dialog", { name: "Evidence detail" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText("rows")).toBeVisible();
});
