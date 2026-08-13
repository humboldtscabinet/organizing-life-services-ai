import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, it } from "node:test";
import {
  appendCtaHold,
  ffmpegAvailable,
  probeDurationSeconds,
  probeHasAudio,
  replaceEndingWithCta,
  runFfmpeg,
} from "./compose.ts";
import { writeCtaCanvas } from "./cta.ts";
import { CTA_HOLD_SECONDS } from "./types.ts";

async function writeColorClip(opts: {
  outputPath: string;
  color: string;
  size: string;
  duration: number;
  audio?: "silence" | "tone";
}): Promise<void> {
  const args = [
    "-y",
    "-f",
    "lavfi",
    "-i",
    `color=c=${opts.color}:s=${opts.size}:d=${opts.duration}:r=24`,
  ];
  if (opts.audio === "tone") {
    args.push("-f", "lavfi", "-i", `sine=frequency=440:duration=${opts.duration}`);
  } else if (opts.audio === "silence") {
    args.push("-f", "lavfi", "-i", `anullsrc=r=44100:cl=stereo:d=${opts.duration}`);
  }
  args.push("-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p");
  if (opts.audio) {
    args.push("-c:a", "aac");
  }
  args.push(opts.outputPath);
  await runFfmpeg(args);
}

async function writeCtaPng(dir: string): Promise<string> {
  const ctaPath = path.join(dir, "cta.png");
  const canvasPath = path.join(dir, "cta-16x9.png");
  await runFfmpeg([
    "-y",
    "-f",
    "lavfi",
    "-i",
    "color=c=blue:s=100x180:d=1",
    "-frames:v",
    "1",
    ctaPath,
  ]);
  await writeCtaCanvas({
    sourceImagePath: ctaPath,
    aspectRatio: "16:9",
    outputPath: canvasPath,
  });
  return canvasPath;
}

describe("ffmpeg CTA compose", () => {
  it("concats a short body clip with a 3s CTA hold", async (t) => {
    if (!(await ffmpegAvailable())) {
      t.skip("ffmpeg is not on PATH");
      return;
    }

    const dir = await mkdtemp(path.join(tmpdir(), "seedance-compose-"));
    try {
      const bodyPath = path.join(dir, "body.mp4");
      const outputPath = path.join(dir, "out.mp4");
      await writeColorClip({
        outputPath: bodyPath,
        color: "red",
        size: "320x180",
        duration: 1,
        audio: "silence",
      });
      await appendCtaHold({
        bodyVideoPath: bodyPath,
        ctaImagePath: await writeCtaPng(dir),
        aspectRatio: "16:9",
        outputPath,
      });

      const duration = await probeDurationSeconds(outputPath);
      assert.ok(
        duration >= 1 + CTA_HOLD_SECONDS - 0.4,
        `expected ~${1 + CTA_HOLD_SECONDS}s, got ${duration}`,
      );
      assert.ok(duration < 1 + CTA_HOLD_SECONDS + 1.5, `too long: ${duration}`);
    } finally {
      await rm(dir, { recursive: true, force: true });
    }
  });

  it("replaces the last 3s with the CTA and muxes original audio onto a silent body", async (t) => {
    if (!(await ffmpegAvailable())) {
      t.skip("ffmpeg is not on PATH");
      return;
    }

    const dir = await mkdtemp(path.join(tmpdir(), "seedance-replace-"));
    try {
      const bodyPath = path.join(dir, "body.mp4");
      const sourcePath = path.join(dir, "source.mp4");
      const outputPath = path.join(dir, "out.mp4");
      await writeColorClip({
        outputPath: bodyPath,
        color: "red",
        size: "320x180",
        duration: 4,
      });
      await writeColorClip({
        outputPath: sourcePath,
        color: "green",
        size: "180x320",
        duration: 4,
        audio: "tone",
      });

      await replaceEndingWithCta({
        bodyVideoPath: bodyPath,
        sourceAudioPath: sourcePath,
        ctaImagePath: await writeCtaPng(dir),
        aspectRatio: "16:9",
        outputPath,
      });

      const duration = await probeDurationSeconds(outputPath);
      assert.ok(duration >= 4 - 0.4, `expected ~4s, got ${duration}`);
      assert.ok(duration < 4 + 1.2, `appended extra time instead of replacing: ${duration}`);
      assert.equal(await probeHasAudio(outputPath), true);
    } finally {
      await rm(dir, { recursive: true, force: true });
    }
  });
});
