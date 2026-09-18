// End-to-end check of the two free-tier failure modes this project actually
// hit in production, run against the real deployed site:
//   1. the heat surface layer (needs TiTiler awake + NEXT_PUBLIC_TITILER_URL)
//   2. a real solve completing (needs the ARQ worker awake -- WORKER_WAKE_URL)
//
// Usage: node media/demo-video/verify-live.mjs
// Deliberately does NOT pre-ping anything: the point is to see what a visitor
// sees, including a cold start.
import { chromium } from "playwright";

const BASE = "https://coolblock.vercel.app";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });

const tiles = { ok: 0, failed: 0, hosts: new Set() };
page.on("response", (r) => {
  if (/\/cog\/tiles\//.test(r.url())) {
    tiles.hosts.add(new URL(r.url()).origin);
    if (r.status() === 200) tiles.ok++;
    else tiles.failed++;
  }
});
page.on("requestfailed", (r) => {
  if (/\/cog\/tiles\//.test(r.url())) tiles.failed++;
});

const t0 = Date.now();
await page.goto(`${BASE}/map`, { waitUntil: "networkidle" });
await page.waitForTimeout(20000); // give a cold TiTiler room to wake

console.log(`heat tiles: ${tiles.ok} ok, ${tiles.failed} failed  from ${[...tiles.hosts].join(", ") || "nowhere"}`);

await page.getByLabel("Budget").fill("20000");
await page.waitForTimeout(800);
const tSolve = Date.now();
await page.getByRole("button", { name: "Run optimizer" }).click();

let solved = false;
try {
  await page.getByRole("button", { name: /generate council memo/i }).waitFor({ state: "visible", timeout: 240000 });
  solved = true;
} catch {}
const secs = ((Date.now() - tSolve) / 1000).toFixed(1);

if (solved) {
  const summary = await page.getByText(/proven optimal|sites ·/).first().textContent().catch(() => null);
  console.log(`solve: COMPLETED in ${secs}s -> ${summary?.trim() ?? "(summary not read)"}`);
} else {
  console.log(`solve: DID NOT COMPLETE within ${secs}s -- worker likely still asleep`);
}
console.log(`total page time: ${((Date.now() - t0) / 1000).toFixed(1)}s`);

await browser.close();
process.exit(solved && tiles.ok > 0 ? 0 : 1);
