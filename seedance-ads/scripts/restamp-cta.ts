#!/usr/bin/env npx tsx
/**
 * Replace the last 3 seconds of existing google-ads keepers with native CTA
 * canvases. ffmpeg only — no Seedance. Writes via a temp file so ffmpeg never
 * reads and writes the same MP4.
 *
 *   npx tsx scripts/restamp-cta.ts
 */
import { readdir, rename, rm } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { downloadToFile, replaceEndingWithCta, requireFfmpeg } from "../src/compose.ts";
import { writeAllCtaCanvases } from "../src/cta.ts";
import { OLS_SERVICES } from "../src/prompts/reframe.ts";
import type { AspectRatio } from "../src/types.ts";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "../..");
const DEFAULT_CTA =
  "https://cdn.shopify.com/s/files/1/0294/7966/5708/files/OLS_CTA_Card_Google_Ads.png?v=1786654544";

function ratioFromName(name: string): AspectRatio | null {
  if (name.endsWith("-1x1.mp4")) return "1:1";
  if (name.endsWith("-16x9.mp4")) return "16:9";
  if (name.endsWith("-9x16.mp4")) return "9:16";
  return null;
}

async function main(): Promise<void> {
  await requireFfmpeg();
  const adsRoot = resolve(repoRoot, "google-ads");
  const ctaDir = resolve(adsRoot, "cta");
  const sourcePath = resolve(ctaDir, "_source/cta-source.png");
  await downloadToFile(DEFAULT_CTA, sourcePath);
  const canvases = await writeAllCtaCanvases(sourcePath, ctaDir, "720p", "native");

  for (const service of OLS_SERVICES) {
    const dir = resolve(adsRoot, service);
    let names: string[] = [];
    try {
      names = await readdir(dir);
    } catch {
      continue;
    }
    for (const name of names) {
      const aspectRatio = ratioFromName(name);
      if (!aspectRatio) continue;
      const outputPath = resolve(dir, name);
      const tmpPath = `${outputPath}.restamp-tmp.mp4`;
      try {
        await replaceEndingWithCta({
          bodyVideoPath: outputPath,
          sourceAudioPath: outputPath,
          ctaImagePath: canvases[aspectRatio],
          aspectRatio,
          outputPath: tmpPath,
        });
        await rename(tmpPath, outputPath);
        console.log(`restamped ${service}/${name}`);
      } finally {
        await rm(tmpPath, { force: true });
      }
    }
  }
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
