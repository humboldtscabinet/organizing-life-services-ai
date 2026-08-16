import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, it } from "node:test";
import { ffmpegAvailable, runFfmpeg } from "../compose.ts";
import {
  bodySampleTimes,
  reviewBodyVideo,
  tesseractAvailable,
  wordsFromTsv,
} from "./sceneTextQa.ts";

describe("bodySampleTimes", () => {
  it("samples 2s / 8s / 14s on an 18s remake, before the last 3s CTA", () => {
    assert.deepEqual(bodySampleTimes(18), [2, 8, 14]);
  });

  it("drops samples that would land on the CTA hold", () => {
    assert.deepEqual(bodySampleTimes(8), [2]);
  });
});

describe("wordsFromTsv", () => {
  it("keeps confident word rows and drops noise", () => {
    const tsv = [
      "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext",
      "5\t1\t1\t1\t1\t1\t10\t10\t40\t20\t92\tKITCHEN",
      "5\t1\t1\t1\t1\t2\t60\t10\t30\t20\t12\tqx",
      "5\t1\t1\t1\t1\t3\t100\t10\t40\t20\t80\tHOX",
    ].join("\n");
    assert.deepEqual(wordsFromTsv(tsv), ["KITCHEN", "HOX"]);
  });
});

describe("reviewBodyVideo", () => {
  it("passes a blank clip when ffmpeg and tesseract are installed", async (t) => {
    if (!(await ffmpegAvailable()) || !(await tesseractAvailable())) {
      t.skip("ffmpeg or tesseract is not on PATH");
      return;
    }

    const dir = await mkdtemp(path.join(tmpdir(), "scene-text-qa-"));
    try {
      const videoPath = path.join(dir, "blank.mp4");
      await runFfmpeg([
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=0xC4A882:s=320x180:d=6:r=24",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        videoPath,
      ]);
      const verdict = await reviewBodyVideo(videoPath, {
        aspectRatio: "16:9",
        framesDir: path.join(dir, "frames"),
        durationSeconds: 6,
      });
      assert.equal(verdict.pass, true);
      assert.equal(verdict.aspectRatio, "16:9");
    } finally {
      await rm(dir, { recursive: true, force: true });
    }
  });
});
