#!/usr/bin/env npx tsx
/**
 * CLI: remake existing 9:16 OLS ads into 1:1 / 16:9 via Seedance,
 * then hard-append the branded CTA card with ffmpeg.
 *
 *   npx tsx scripts/reframe-ad.ts --manifest examples/ols-reframe.manifest.json --dry-run
 *   npx tsx scripts/reframe-ad.ts --video <url> --cta <url> --service estate-sales --ratios 1:1,16:9
 */

import { config as loadEnv } from "dotenv";
import { mkdir, readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";
import { SeedanceClient, prepareGeneration } from "../src/client.ts";
import { appendCtaHold, downloadToFile, requireFfmpeg } from "../src/compose.ts";
import { writeAllCtaCanvases } from "../src/cta.ts";
import { FRAMING_CTA_RULES, hasFramingRule } from "../src/framing.ts";
import { logger } from "../src/logger.ts";
import {
  filterManifestByService,
  parseReframeManifest,
  type ReframeManifest,
  type ReframeVideo,
} from "../src/manifest.ts";
import {
  OLS_SERVICES,
  buildReframeGenerateOptions,
} from "../src/prompts/reframe.ts";
import { buildSeevioPayload } from "../src/seevio.ts";
import {
  CTA_HOLD_SECONDS,
  DEFAULT_SEEDANCE_MODEL,
  REFRAME_BODY_SECONDS,
  aspectRatioSchema,
  generateAdOptionsSchema,
  type AspectRatio,
} from "../src/types.ts";

const here = dirname(fileURLToPath(import.meta.url));
loadEnv({ path: resolve(here, "../.env"), quiet: true });
loadEnv({ quiet: true });

const HELP = `
seedance-ads — remake 9:16 source ads into 1:1 / 16:9 and append the CTA card

USAGE
  npx tsx scripts/reframe-ad.ts --manifest examples/ols-reframe.manifest.json --dry-run
  npx tsx scripts/reframe-ad.ts --manifest examples/ols-reframe.manifest.json --service estate-sales
  npx tsx scripts/reframe-ad.ts --video <url> --cta <url> --service jewelry --ratios 1:1,16:9

SOURCE (one of)
  --manifest <path>        JSON with ctaImageUrl + videos[]
  --video <url>            Single public source MP4 (requires --cta and --service)

OPTIONS
  --cta <url>              Public 9:16 CTA still (required with --video)
  --service <id>           Filter manifest, or tag a single --video
  --ratios 1:1,16:9        Target ratios (default: 1:1,16:9)
  --with-vertical          Also write CTA-appended 9:16 from the original (ffmpeg only)
  --output <dir>           Override manifest outputDir
  --dry-run                Print Seevio payloads; no API call, no ffmpeg
  --help                   Show this message

Seedance remakes are ${REFRAME_BODY_SECONDS}s; ffmpeg then appends a ${CTA_HOLD_SECONDS}s CTA hold.
Seevio requires public HTTPS URLs. ffmpeg must be on PATH for live compose.
`.trim();

type FlagValue = string | boolean;

function parseArgv(argv: string[]): Record<string, FlagValue> {
  const flags: Record<string, FlagValue> = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token?.startsWith("--")) {
      throw new Error(`Unexpected argument: ${token}`);
    }
    const key = token.slice(2);
    if (key === "help" || key === "dry-run" || key === "with-vertical") {
      flags[key] = true;
      continue;
    }
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      throw new Error(`Flag --${key} requires a value`);
    }
    i += 1;
    flags[key] = next;
  }
  return flags;
}

const cliSchema = z.object({
  manifest: z.string().min(1).optional(),
  video: z.string().min(1).optional(),
  cta: z.string().min(1).optional(),
  service: z.enum(OLS_SERVICES).optional(),
  ratios: z.string().min(1).optional(),
  output: z.string().min(1).optional(),
  "with-vertical": z.boolean().optional(),
  "dry-run": z.boolean().optional(),
  help: z.boolean().optional(),
});

function parseRatios(raw: string | undefined, withVertical: boolean): AspectRatio[] {
  const requested = (raw ?? "1:1,16:9")
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => aspectRatioSchema.parse(part));
  const ratios: AspectRatio[] = [];
  for (const ratio of requested) {
    if (!ratios.includes(ratio)) ratios.push(ratio);
  }
  if (withVertical && !ratios.includes("9:16")) {
    ratios.push("9:16");
  }
  return ratios;
}

function ratioFileToken(ratio: AspectRatio): string {
  return ratio.replace(":", "x");
}

async function loadManifest(flags: z.infer<typeof cliSchema>): Promise<ReframeManifest> {
  if (flags.manifest) {
    const path = resolve(flags.manifest);
    const raw = JSON.parse(await readFile(path, "utf8")) as unknown;
    let manifest = parseReframeManifest(raw);
    if (flags.output) {
      manifest = { ...manifest, outputDir: flags.output };
    }
    if (flags.service) {
      manifest = filterManifestByService(manifest, flags.service);
    }
    return manifest;
  }

  if (!flags.video || !flags.cta || !flags.service) {
    throw new Error("Provide --manifest, or --video plus --cta plus --service");
  }

  return parseReframeManifest({
    ctaImageUrl: flags.cta,
    outputDir: flags.output ?? "output/reframe",
    videos: [
      {
        id: "single",
        service: flags.service,
        sourceVideoUrl: flags.video,
      },
    ],
  });
}

function printDryRun(
  videos: ReframeVideo[],
  ctaImageUrl: string,
  ratios: AspectRatio[],
  model: string,
): void {
  console.log(`\nDry run — model: ${model}`);
  console.log(
    `Seedance body ${REFRAME_BODY_SECONDS}s + CTA hold ${CTA_HOLD_SECONDS}s. No API call.\n`,
  );

  for (const video of videos) {
    for (const aspectRatio of ratios) {
      if (aspectRatio === "9:16") {
        console.log(`── ${video.id}  9:16  (ffmpeg only — original + CTA, no Seedance)`);
        continue;
      }
      const options = generateAdOptionsSchema.parse(
        buildReframeGenerateOptions({
          service: video.service,
          aspectRatio,
          sourceVideoUrl: video.sourceVideoUrl,
          ctaImageUrl,
        }),
      );
      const prepared = prepareGeneration(options, model);
      const payload = buildSeevioPayload(options, prepared, model);
      console.log(`── ${video.id}  ${aspectRatio}`);
      console.log(`generation_type=${payload.input.generation_type}`);
      console.log(`duration=${payload.input.duration}s  ratio=${payload.input.aspect_ratio}`);
      console.log(`video_urls=${JSON.stringify(payload.input.video_urls)}`);
      console.log(`image_urls=${JSON.stringify(payload.input.image_urls)}`);
      console.log(`framing=${hasFramingRule(payload.input.prompt, aspectRatio)}`);
      console.log(`ctaHold=${payload.input.prompt.includes(FRAMING_CTA_RULES[aspectRatio])}`);
      console.log(payload.input.prompt);
      console.log("");
    }
  }
}

async function remakeRatio(opts: {
  video: ReframeVideo;
  aspectRatio: AspectRatio;
  ctaImageUrl: string;
  ctaCanvasPath: string;
  outputDir: string;
  client: SeedanceClient;
}): Promise<string> {
  const workDir = resolve(opts.outputDir, opts.video.service, opts.video.id);
  await mkdir(workDir, { recursive: true });
  const finalPath = resolve(workDir, `${opts.video.id}-${ratioFileToken(opts.aspectRatio)}.mp4`);

  if (opts.aspectRatio === "9:16") {
    const sourcePath = resolve(workDir, "source-9x16.mp4");
    await downloadToFile(opts.video.sourceVideoUrl, sourcePath);
    await appendCtaHold({
      bodyVideoPath: sourcePath,
      ctaImagePath: opts.ctaCanvasPath,
      aspectRatio: "9:16",
      outputPath: finalPath,
    });
    return finalPath;
  }

  const bodyDir = resolve(workDir, "body");
  const result = await opts.client.generate(
    buildReframeGenerateOptions({
      service: opts.video.service,
      aspectRatio: opts.aspectRatio,
      sourceVideoUrl: opts.video.sourceVideoUrl,
      ctaImageUrl: opts.ctaImageUrl,
      outputDir: bodyDir,
    }),
  );
  if (!result.videoPath) {
    throw new Error(`Seedance returned no local file for ${opts.video.id} ${opts.aspectRatio}`);
  }
  await appendCtaHold({
    bodyVideoPath: result.videoPath,
    ctaImagePath: opts.ctaCanvasPath,
    aspectRatio: opts.aspectRatio,
    outputPath: finalPath,
  });
  return finalPath;
}

async function main(): Promise<void> {
  const rawArgv = process.argv.slice(2);
  if (rawArgv.length === 0 || rawArgv.includes("--help") || rawArgv.includes("-h")) {
    console.log(HELP);
    if (rawArgv.length === 0) process.exit(1);
    return;
  }

  const flags = cliSchema.parse(parseArgv(rawArgv));
  const withVertical = Boolean(flags["with-vertical"]);
  const ratios = parseRatios(flags.ratios, withVertical);
  const manifest = await loadManifest(flags);
  const model = process.env.SEEDANCE_MODEL ?? DEFAULT_SEEDANCE_MODEL;

  if (flags["dry-run"]) {
    printDryRun(manifest.videos, manifest.ctaImageUrl, ratios, model);
    return;
  }

  await requireFfmpeg();
  const staging = resolve(manifest.outputDir, "_cta");
  await mkdir(staging, { recursive: true });
  const ctaSourcePath = resolve(staging, "cta-source.png");
  await downloadToFile(manifest.ctaImageUrl, ctaSourcePath);
  const canvases = await writeAllCtaCanvases(ctaSourcePath, staging);

  const client = new SeedanceClient({ model });
  let failed = 0;

  for (const video of manifest.videos) {
    for (const aspectRatio of ratios) {
      try {
        const outputPath = await remakeRatio({
          video,
          aspectRatio,
          ctaImageUrl: manifest.ctaImageUrl,
          ctaCanvasPath: canvases[aspectRatio],
          outputDir: manifest.outputDir,
          client,
        });
        logger.info("Reframe ready", {
          id: video.id,
          service: video.service,
          aspectRatio,
          path: outputPath,
        });
      } catch (error) {
        failed += 1;
        const message = error instanceof Error ? error.message : String(error);
        logger.error(`Failed ${video.id} ${aspectRatio}: ${message}`);
      }
    }
  }

  if (failed > 0) {
    process.exitCode = 1;
  }
}

main().catch((error: unknown) => {
  const message = error instanceof Error ? error.message : String(error);
  logger.error(message);
  process.exit(1);
});
