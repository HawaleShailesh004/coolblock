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

  // Real solve time: the exact solver proves the default pool in ~2s
  // (docs/adr/0028-*.md), and CELF is faster still where it falls back --
  // the budget below mostly covers real network/DB/job-queue round trips.
  // Matching the solver's own wording, not just "EWCB", keeps this
  // asserting that the run reached done rather than merely rendered.
  await expect(page.getByText(/EWCB · (proven optimal|greedy)/)).toBeVisible({ timeout: 40_000 });
}
