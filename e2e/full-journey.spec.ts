import { expect, test } from "@playwright/test";
import { runOptimizerToCompletion } from "./helpers";

/** Phase 13's "the full journey": the actual product's core loop, driven
 * through the real UI against the real backend -- no mocked responses. */
test("a visitor can run the optimizer and see a real, ranked plan", async ({ page }) => {
  await runOptimizerToCompletion(page);

  // The ranked-sites table (§8.6: "every map layer has a table view").
  await expect(page.getByText(/Ranked sites \(\d+\)/)).toBeVisible();
  const rows = page.locator("table tbody tr");
  await expect(rows.first()).toBeVisible();
  expect(await rows.count()).toBeGreaterThan(0);

  // A real cost figure, not a placeholder -- the summary line already
  // asserted in runOptimizerToCompletion includes a real dollar amount.
  await expect(page.getByText(/\$[\d,]+/).first()).toBeVisible();
});

test("adjusting the budget slider changes the number reflected in the UI", async ({ page }) => {
  await page.goto("/map");
  const slider = page.getByRole("slider", { name: "Budget" });
  await expect(slider).toBeVisible();
  await expect(page.getByText("$50,000")).toBeVisible(); // DEFAULT_BUDGET_USD, apps/web/app/map/OptimizerPanel.tsx

  await slider.fill("200000");

  await expect(page.getByText("$200,000")).toBeVisible();
});
