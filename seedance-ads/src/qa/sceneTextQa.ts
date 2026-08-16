/**
 * Post-generation scene-text QA.
 *
 * Samples body frames (before the last 3s CTA), OCRs them with tesseract,
 * and fails the clip if tokens look like gibberish. Does not retry Seedance
 * and cannot refund Seevio credits.
 */

import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import type { QaAgent, QaVerdict } from "../agents/contracts.ts";
import { probeDurationSeconds, runFfmpeg } from "../compose.ts";
import { logger } from "../logger.ts";
import { CTA_HOLD_SECONDS, type AspectRatio, type GenerateAdResult } from "../types.ts";
import { classifySceneText, type SceneTextReport } from "./sceneText.ts";

export const SCENE_TEXT_SAMPLE_SECONDS = [2, 8, 14] as const;
export const TESSERACT_MIN_CONFIDENCE = 55;

export class TesseractMissingError extends Error {
  constructor() {
    super(
      "tesseract is required on PATH for scene-text QA (apt install tesseract-ocr). Pass --skip-scene-text-qa to bypass; that can ship gibberish box labels.",
    );
    this.name = "TesseractMissingError";
  }
}

export class SceneTextQaError extends Error {
  readonly verdict: QaVerdict;
  readonly bodyVideoPath: string;
  readonly reportPath?: string;

  constructor(
    message: string,
    opts: { verdict: QaVerdict; bodyVideoPath: string; reportPath?: string },
  ) {
    super(message);
    this.name = "SceneTextQaError";
    this.verdict = opts.verdict;
    this.bodyVideoPath = opts.bodyVideoPath;
    this.reportPath = opts.reportPath;
  }
}

export type FrameOcr = {
  seconds: number;
  path: string;
  text: string;
  report: SceneTextReport;
};

export type SceneTextQaReport = {
  pass: boolean;
  aspectRatio: AspectRatio;
  videoPath: string;
  durationSeconds: number;
  frames: FrameOcr[];
  notes: string[];
};

export function bodySampleTimes(
  durationSeconds: number,
  holdSeconds = CTA_HOLD_SECONDS,
): number[] {
  const bodyEnd = Math.max(durationSeconds - holdSeconds, 0.5);
  const times: number[] = [];
  for (const candidate of SCENE_TEXT_SAMPLE_SECONDS) {
    if (candidate < bodyEnd - 0.15) {
      times.push(candidate);
    }
  }
  if (times.length === 0) {
    times.push(Math.max(0.25, Number((bodyEnd / 2).toFixed(2))));
  }
  return times;
}

export async function requireTesseract(): Promise<void> {
  try {
    await runTesseract(["--version"]);
  } catch (error) {
    if (error instanceof TesseractMissingError) throw error;
    const message = error instanceof Error ? error.message : String(error);
    if (/not found|ENOENT/i.test(message)) {
      throw new TesseractMissingError();
    }
    throw error;
  }
}

export async function tesseractAvailable(): Promise<boolean> {
  try {
    await requireTesseract();
    return true;
  } catch (error) {
    if (error instanceof TesseractMissingError) return false;
    return false;
  }
}

async function runTesseract(args: string[]): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn("tesseract", args, { stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString();
    });
    child.on("error", (error: NodeJS.ErrnoException) => {
      if (error.code === "ENOENT") {
        reject(new TesseractMissingError());
        return;
      }
      reject(error);
    });
    child.on("close", (code) => {
      if (code === 0) {
        resolve(stdout || stderr);
        return;
      }
      reject(new Error(`tesseract exited ${code}: ${stderr.slice(-2000)}`));
    });
  });
}

export async function extractStill(opts: {
  videoPath: string;
  seconds: number;
  outputPath: string;
}): Promise<string> {
  await mkdir(path.dirname(opts.outputPath), { recursive: true });
  await runFfmpeg([
    "-y",
    "-ss",
    opts.seconds.toFixed(3),
    "-i",
    opts.videoPath,
    "-frames:v",
    "1",
    "-vf",
    "scale=iw*2:ih*2",
    "-q:v",
    "2",
    opts.outputPath,
  ]);
  return opts.outputPath;
}

/** Parse `tesseract … tsv` word rows, dropping low-confidence noise. */
export function wordsFromTsv(
  tsv: string,
  minConfidence = TESSERACT_MIN_CONFIDENCE,
): string[] {
  const words: string[] = [];
  for (const line of tsv.split(/\r?\n/)) {
    if (!line || line.startsWith("level")) continue;
    const cols = line.split("\t");
    const level = Number(cols[0]);
    const conf = Number(cols[10]);
    const text = (cols[11] ?? "").trim();
    if (level !== 5) continue;
    if (!Number.isFinite(conf) || conf < minConfidence) continue;
    if (!text) continue;
    words.push(text);
  }
  return words;
}

export async function ocrImage(imagePath: string): Promise<string> {
  const tsv = await runTesseract([
    imagePath,
    "stdout",
    "--psm",
    "11",
    "--oem",
    "1",
    "tsv",
  ]);
  return wordsFromTsv(tsv).join(" ");
}

export async function reviewBodyVideo(
  videoPath: string,
  opts: {
    aspectRatio: AspectRatio;
    framesDir: string;
    holdSeconds?: number;
    durationSeconds?: number;
  },
): Promise<QaVerdict> {
  const durationSeconds =
    opts.durationSeconds ?? (await probeDurationSeconds(videoPath));
  const times = bodySampleTimes(durationSeconds, opts.holdSeconds ?? CTA_HOLD_SECONDS);
  await mkdir(opts.framesDir, { recursive: true });

  const frames: FrameOcr[] = [];
  const notes: string[] = [];

  for (const seconds of times) {
    const framePath = path.join(
      opts.framesDir,
      `body-${String(seconds).replace(".", "p")}s.jpg`,
    );
    await extractStill({ videoPath, seconds, outputPath: framePath });
    const text = await ocrImage(framePath);
    const report = classifySceneText(text);
    frames.push({ seconds, path: framePath, text, report });
    if (!report.pass) {
      notes.push(
        `t=${seconds}s: ${report.failures.map((item) => item.token).join(", ") || report.notes.join("; ")}`,
      );
    }
  }

  const pass = frames.every((frame) => frame.report.pass);
  if (pass) {
    notes.push(
      `Scene-text QA passed (${times.map((time) => `${time}s`).join(", ")}). Real English labels are allowed; no gibberish tokens.`,
    );
  } else {
    notes.unshift(
      "Scene-text QA failed. Keeper not written. Seevio credits already spent; not retrying.",
    );
  }

  const report: SceneTextQaReport = {
    pass,
    aspectRatio: opts.aspectRatio,
    videoPath,
    durationSeconds,
    frames,
    notes,
  };
  const reportPath = path.join(opts.framesDir, "scene-text-qa.json");
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`);
  logger.info(pass ? "Scene-text QA passed" : "Scene-text QA failed", {
    videoPath,
    aspectRatio: opts.aspectRatio,
    reportPath,
    notes,
  });

  return { pass, notes, aspectRatio: opts.aspectRatio };
}

export class SceneTextQaAgent implements QaAgent {
  constructor(
    private readonly options: { framesDir: string; holdSeconds?: number },
  ) {}

  async review(result: GenerateAdResult): Promise<QaVerdict> {
    if (!result.videoPath) {
      return {
        pass: false,
        notes: ["No local video to OCR for scene-text QA."],
        aspectRatio: result.aspectRatio,
      };
    }
    return reviewBodyVideo(result.videoPath, {
      aspectRatio: result.aspectRatio,
      framesDir: this.options.framesDir,
      holdSeconds: this.options.holdSeconds,
    });
  }
}
