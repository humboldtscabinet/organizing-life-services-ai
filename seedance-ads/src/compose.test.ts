import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, it } from "node:test";
import { appendCtaHold, ffmpegAvailable, probeDurationSeconds, runFfmpeg } from "./compose.ts";
import { writeCtaCanvas } from "./cta.ts";
import { CTA_HOLD_SECONDS } from "./types.ts";

describe("ffmpeg CTA compose", () => {
  it("concats a short body clip with a 3s CTA hold", async (t) => {
    if (!(await ffmpegAvailable())) {
      t.skip("ffmpeg is not on PATH");
      return;
    }

    const dir = await mkdtemp(path.join(tmpdir(), "seedance-compose-"));
    try {
      const bodyPath = path.join(dir, "body.mp4");
      const ctaPath = path.join(dir, "cta.png");
      const canvasPath = path.join(dir, "cta-16x9.png");
      const outputPath = path.join(dir, "out.mp4");

      await runFfmpeg([
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=red:s=320x180:d=1:r=24",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=44100:cl=stereo:d=1",
        "-shortest",
        "-pix_fmt",
        "yuv420p",
        bodyPath,
      ]);
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
      await appendCtaHold({
        bodyVideoPath: bodyPath,
        ctaImagePath: canvasPath,
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
});
