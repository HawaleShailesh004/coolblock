import { expect, type Page } from "@playwright/test";

/** Drives a real optimizer solve through the actual UI (no API shortcuts)
 * and waits for it to reach "done" -- shared by every spec below since
 * each one needs a real, solved scenario to exercise its own flow
 * against. Real backend, real ARQ job, real SSE stream (see
 * playwright.config.ts's own docstring for what infra this needs up). */
export async function runOptimizerToCompletion(page: Page): Promise<void> {
  await page.goto("/map");
  const runButton = page.getByRole("button", { name: "Run optimizer" });
  await expect(runButton).toBeVisible({ timeout: 15_000 });
  await runButton.click();

  // Real solve time (CELF is fast, ~0.05-0.2s per docs/METHODOLOGY.md) --
  // the budget below covers real network/DB/job-queue round trips, not
  // the solver itself.
  await expect(page.getByText(/EWCB \(/)).toBeVisible({ timeout: 30_000 });
}
