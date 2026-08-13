#!/usr/bin/env npx tsx
/**
 * CLI: generate Google Ads videos with Seedance.
 *
 *   npx tsx scripts/generate-ad.ts --prompt "..." --ratio 9:16
 *   npx tsx scripts/generate-ad.ts --prompt "..." --all
 *
 * Framing rules are applied automatically. Do not paste them into --prompt.
 */

import { config as loadEnv } from "dotenv";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";
import { SeedanceClient, prepareGeneration } from "../src/client.ts";
import { FRAMING_RULES, hasFramingRule } from "../src/framing.ts";
import { logger } from "../src/logger.ts";
import {
  ASPECT_RATIOS,
  DEFAULT_DURATION_SECONDS,
  DEFAULT_SEEDANCE_MODEL,
  aspectRatioSchema,
  generateAdOptionsSchema,
  videoResolutionSchema,
  type AspectRatio,
  type GenerateAdOptions,
} from "../src/types.ts";

const here = dirname(fileURLToPath(import.meta.url));
loadEnv({ path: resolve(here, "../.env"), quiet: true });
loadEnv({ quiet: true });

const HELP = `
seedance-ads — Google Ads video generation via ByteDance Seedance

USAGE
  npx tsx scripts/generate-ad.ts --prompt "<brief>" --ratio 9:16
  npx tsx scripts/generate-ad.ts --prompt "<brief>" --all
  npm run generate -- --prompt "<brief>" --ratio 1:1

REQUIRED
  --prompt <text>          Creative brief. Framing is appended automatically.

RATIO
  --ratio 9:16|1:1|16:9    Generate a single aspect ratio (default: 9:16)
  --all                    Generate the full Performance Max set (9:16, 1:1, 16:9)

OPTIONS
  --duration <seconds>     Clip length (default: ${DEFAULT_DURATION_SECONDS}; Seedance 2.0: 4–15)
  --image <path|url>       First-frame image for image-to-video
  --last-frame <path|url>  CTA / last-frame image
  --cta <path|url>         Alias for --last-frame
  --reference-image <url>  Repeatable reference still
  --reference-video <url>  Repeatable Seedance 2.0 reference clip
  --audio                  Request synchronized audio
  --resolution 480p|720p|1080p   Default: 720p (Seedance 2.0 max is 720p)
  --output <dir>           Download directory (default: ./output)
  --model <id>             Override SEEDANCE_MODEL / default ${DEFAULT_SEEDANCE_MODEL}
  --parallel               With --all, generate the three ratios concurrently
  --dry-run                Print framed prompts only; no API call
  --help                   Show this message

ENV
  ARK_API_KEY              BytePlus ModelArk API key (required unless --dry-run)
  SEEDANCE_MODEL           Optional model override
`.trim();

type FlagValue = string | boolean | string[];

function parseArgv(argv: string[]): Record<string, FlagValue> {
  const flags: Record<string, FlagValue> = {};
  const repeatable = new Set(["reference-image", "reference-video"]);

  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token?.startsWith("--")) {
      throw new Error(`Unexpected argument: ${token}`);
    }
    const key = token.slice(2);
    if (key === "help" || key === "all" || key === "audio" || key === "parallel" || key === "dry-run") {
      flags[key] = true;
      continue;
    }
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      throw new Error(`Flag --${key} requires a value`);
    }
    i += 1;
    if (repeatable.has(key)) {
      const existing = flags[key];
      const list = Array.isArray(existing) ? existing : [];
      list.push(next);
      flags[key] = list;
    } else {
      flags[key] = next;
    }
  }

  return flags;
}

const cliSchema = z.object({
  prompt: z.string().min(1),
  ratio: aspectRatioSchema.optional(),
  all: z.boolean().optional(),
  duration: z.coerce.number().int().min(4).max(15).optional(),
  image: z.string().min(1).optional(),
  "last-frame": z.string().min(1).optional(),
  cta: z.string().min(1).optional(),
  "reference-image": z.array(z.string().min(1)).optional(),
  "reference-video": z.array(z.string().min(1)).optional(),
  audio: z.boolean().optional(),
  resolution: videoResolutionSchema.optional(),
  output: z.string().min(1).optional(),
  model: z.string().min(1).optional(),
  parallel: z.boolean().optional(),
  "dry-run": z.boolean().optional(),
  help: z.boolean().optional(),
});

function flagsToOptions(flags: z.infer<typeof cliSchema>): GenerateAdOptions {
  return generateAdOptionsSchema.parse({
    prompt: flags.prompt,
    aspectRatio: flags.ratio ?? "9:16",
    duration: flags.duration,
    image: flags.image,
    lastFrameImage: flags["last-frame"] ?? flags.cta,
    referenceImages: flags["reference-image"],
    referenceVideos: flags["reference-video"],
    generateAudio: flags.audio,
    resolution: flags.resolution,
    outputDir: flags.output,
  });
}

function printDryRun(options: GenerateAdOptions, ratios: readonly AspectRatio[], model: string): void {
  console.log(`\nDry run — model: ${model}`);
  console.log("Framing will be applied automatically. No API call is made.\n");

  for (const aspectRatio of ratios) {
    const prepared = prepareGeneration(
      generateAdOptionsSchema.parse({ ...options, aspectRatio }),
      model,
    );
    const applied = hasFramingRule(prepared.framedPrompt, aspectRatio);
    console.log(`── ${aspectRatio}  (framing applied: ${applied})`);
    console.log(prepared.framedPrompt);
    console.log(`mode=${prepared.mode}  duration=${prepared.duration}s  pixels=${prepared.pixelResolution}`);
    console.log(`canonical rule:\n  ${FRAMING_RULES[aspectRatio]}\n`);
  }
}

async function main(): Promise<void> {
  const rawArgv = process.argv.slice(2);
  if (rawArgv.length === 0 || rawArgv.includes("--help") || rawArgv.includes("-h")) {
    console.log(HELP);
    if (rawArgv.length === 0) process.exit(1);
    return;
  }

  const parsedFlags = cliSchema.parse(parseArgv(rawArgv));
  if (!parsedFlags.prompt) {
    throw new Error("--prompt is required");
  }
  if (parsedFlags.ratio && parsedFlags.all) {
    throw new Error("Use either --ratio or --all, not both");
  }

  const options = flagsToOptions(parsedFlags);
  const model = parsedFlags.model ?? process.env.SEEDANCE_MODEL ?? DEFAULT_SEEDANCE_MODEL;
  const ratios: readonly AspectRatio[] = parsedFlags.all ? ASPECT_RATIOS : [options.aspectRatio ?? "9:16"];

  if (parsedFlags["dry-run"]) {
    printDryRun(options, ratios, model);
    return;
  }

  const client = new SeedanceClient({ model: parsedFlags.model });

  if (parsedFlags.all) {
    const { results, failures } = await client.generateAllRatios(options, {
      parallel: parsedFlags.parallel,
    });

    for (const result of results) {
      logger.info("Ad ready", {
        ratio: result.aspectRatio,
        path: result.videoPath,
        taskId: result.taskId,
        framingApplied: hasFramingRule(result.framedPrompt, result.aspectRatio),
      });
    }

    if (failures.length > 0) {
      for (const failure of failures) {
        logger.error(`Failed ${failure.aspectRatio}: ${failure.error}`);
      }
      process.exitCode = 1;
    }
    return;
  }

  const result = await client.generate(options);
  console.log(
    JSON.stringify(
      {
        aspectRatio: result.aspectRatio,
        framingApplied: hasFramingRule(result.framedPrompt, result.aspectRatio),
        videoPath: result.videoPath,
        taskId: result.taskId,
        duration: result.duration,
        model: result.model,
        warnings: result.warnings,
        elapsedMs: result.elapsedMs,
      },
      null,
      2,
    ),
  );
}

main().catch((error: unknown) => {
  const message = error instanceof Error ? error.message : String(error);
  logger.error(message);
  process.exit(1);
});
