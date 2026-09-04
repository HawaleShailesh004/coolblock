#!/usr/bin/env node
// Fetches the running API's OpenAPI schema and generates ./generated/api.d.ts.
// Wired for real in Phase 7 once apps/api exposes /openapi.json with actual routes.
import { existsSync, mkdirSync } from "node:fs";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

async function main() {
  const res = await fetch(`${API_URL}/openapi.json`);
  if (!res.ok) {
    console.error(`Could not fetch ${API_URL}/openapi.json (${res.status}). Is the API running?`);
    process.exit(1);
  }

  if (!existsSync("./generated")) mkdirSync("./generated");

  const { default: openapiTS, astToString } = await import("openapi-typescript");
  const ast = await openapiTS(await res.json());
  const contents = astToString(ast);

  await import("node:fs/promises").then((fs) => fs.writeFile("./generated/api.d.ts", contents));
  console.log("Wrote packages/schema/generated/api.d.ts");
}

main();
