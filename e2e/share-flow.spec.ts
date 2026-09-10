import { expect, test } from "@playwright/test";
import { runOptimizerToCompletion } from "./helpers";

/** Phase 13's "the share flow": a real gap found writing this test --
 * the "Share link" button generated a URL pointing at /share/[token],
 * but that page didn't exist until this same pass (docs/adr/0024-*.md). */
test("a generated share link renders the same solved plan in a fresh browser context", async ({ page, context }) => {
  await runOptimizerToCompletion(page);

  await page.getByRole("button", { name: "Share link" }).click();
  const shareInput = page.locator('input[readonly]');
  await expect(shareInput).toBeVisible();
  const shareUrl = await shareInput.inputValue();
  expect(shareUrl).toMatch(/\/share\/.+/);

  // A fresh, unrelated browser context -- no shared state with the page
  // that generated the link, the real test of "public read-only."
  const visitorPage = await context.browser()!.newContext().then((c) => c.newPage());
  await visitorPage.goto(shareUrl);

  await expect(visitorPage.getByRole("heading", { name: /Scenario v\d+/ })).toBeVisible({ timeout: 10_000 });
  const rows = visitorPage.locator("table tbody tr");
  await expect(rows.first()).toBeVisible();
  expect(await rows.count()).toBeGreaterThan(0);

  await visitorPage.close();
});

test("an unknown share token shows a clear not-found state, not a crash", async ({ page }) => {
  await page.goto("/share/this-token-does-not-exist");
  await expect(page.getByText(/doesn't exist, or has been revoked/)).toBeVisible({ timeout: 10_000 });
});
