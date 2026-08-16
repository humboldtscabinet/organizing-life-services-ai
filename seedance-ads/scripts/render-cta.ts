#!/usr/bin/env npx tsx
/**
 * Render native 9:16 / 1:1 / 16:9 CTA cards from the Shopify master.
 * Text is never sent to Seedance. 9:16 is a uniform scale of the original;
 * 1:1 and 16:9 reflow locked copy around a crop of the original logo lockup.
 *
 *   npx tsx scripts/render-cta.ts
 *   npx tsx scripts/render-cta.ts --output ../google-ads/cta --layout native
 */
import { config as loadEnv } from "dotenv";
import { mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { downloadToFile, requireFfmpeg } from "../src/compose.ts";
import { writeAllCtaCanvases, type CtaLayout } from "../src/cta.ts";

const here = dirname(fileURLToPath(import.meta.url));
loadEnv({ path: resolve(here, "../.env"), quiet: true });
loadEnv({ quiet: true });

const DEFAULT_CTA =
  "https://cdn.shopify.com/s/files/1/0294/7966/5708/files/OLS_CTA_Card_Google_Ads.png?v=1786654544";

function flag(name: string): string | undefined {
  const index = process.argv.indexOf(`--${name}`);
  if (index === -1) return undefined;
  return process.argv[index + 1];
}

async function main(): Promise<void> {
  await requireFfmpeg();
  const sourceUrl = flag("source") ?? DEFAULT_CTA;
  const outputDir = resolve(here, flag("output") ?? "../../google-ads/cta");
  const layout = (flag("layout") ?? "native") as CtaLayout;
  await mkdir(outputDir, { recursive: true });
  const staging = resolve(outputDir, "_source");
  await mkdir(staging, { recursive: true });
  const sourcePath = resolve(staging, "cta-source.png");
  if (/^https?:\/\//i.test(sourceUrl)) {
    await downloadToFile(sourceUrl, sourcePath);
  }
  const canvases = await writeAllCtaCanvases(
    /^https?:\/\//i.test(sourceUrl) ? sourcePath : resolve(sourceUrl),
    outputDir,
    "720p",
    layout,
  );
  for (const [ratio, path] of Object.entries(canvases)) {
    console.log(`${ratio}  ${path}`);
  }
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
