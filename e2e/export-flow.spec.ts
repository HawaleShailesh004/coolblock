import { expect, test } from "@playwright/test";
import { runOptimizerToCompletion } from "./helpers";

/** Phase 13's "the export flow": a real bug found writing this test --
 * "Export GeoJSON"/"Export CSV" were plain <a href> links, which cannot
 * carry the X-Dev-Workspace-Id header the export endpoint requires; a
 * plain click resolved to the wrong dev-fallback workspace and 404'd
 * every time (confirmed directly against a running server, not assumed).
 * Fixed to fetch-with-headers-then-Blob-download instead
 * (docs/adr/0024-*.md). */
test("Export GeoJSON downloads real, non-empty GeoJSON for the solved plan", async ({ page }) => {
  await runOptimizerToCompletion(page);

  const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Export GeoJSON" }).click()]);
  expect(download.suggestedFilename()).toMatch(/\.geojson$/);

  const path = await download.path();
  expect(path).not.toBeNull();
  const fs = await import("node:fs/promises");
  const contents = JSON.parse(await fs.readFile(path!, "utf-8"));
  expect(contents.type).toBe("FeatureCollection");
  expect(Array.isArray(contents.features)).toBe(true);
  expect(contents.features.length).toBeGreaterThan(0);
});

test("Export CSV downloads a real, non-empty CSV for the solved plan", async ({ page }) => {
  await runOptimizerToCompletion(page);

  const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Export CSV" }).click()]);
  expect(download.suggestedFilename()).toMatch(/\.csv$/);

  const path = await download.path();
  expect(path).not.toBeNull();
  const fs = await import("node:fs/promises");
  const contents = await fs.readFile(path!, "utf-8");
  const lines = contents.trim().split("\n");
  expect(lines.length).toBeGreaterThan(1); // header + at least one real row
});
