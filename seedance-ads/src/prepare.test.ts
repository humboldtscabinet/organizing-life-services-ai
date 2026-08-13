import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { prepareGeneration } from "./client.ts";
import { FRAMING_RULES, hasFramingRule } from "./framing.ts";
import {
  ASPECT_RATIOS,
  DEFAULT_SEEDANCE_MODEL,
  generateAdOptionsSchema,
} from "./types.ts";

const BRIEF = "Estate-sale specialist walking a bright Tampa home, calm and trustworthy.";

describe("prepareGeneration — framing is mandatory", () => {
  for (const ratio of ASPECT_RATIOS) {
    it(`injects ${ratio} framing for text-to-video`, () => {
      const prepared = prepareGeneration(
        generateAdOptionsSchema.parse({ prompt: BRIEF, aspectRatio: ratio }),
        DEFAULT_SEEDANCE_MODEL,
      );

      assert.equal(prepared.aspectRatio, ratio);
      assert.equal(prepared.mode, "text-to-video");
      assert.equal(prepared.sdkAspectRatio, ratio);
      assert.ok(hasFramingRule(prepared.framedPrompt, ratio));
      assert.ok(prepared.framedPrompt.includes(FRAMING_RULES[ratio]));
      assert.ok(prepared.framedPrompt.startsWith(BRIEF));
    });
  }

  it("still injects framing for image-to-video", () => {
    const prepared = prepareGeneration(
      generateAdOptionsSchema.parse({
        prompt: BRIEF,
        aspectRatio: "9:16",
        image: "https://example.com/first-frame.png",
      }),
      DEFAULT_SEEDANCE_MODEL,
    );

    assert.equal(prepared.mode, "image-to-video");
    assert.equal(prepared.sdkAspectRatio, "adaptive");
    assert.ok(hasFramingRule(prepared.framedPrompt, "9:16"));
    assert.ok(
      prepared.warnings.some((warning) => warning.includes("inherits the source image ratio")),
    );
  });

  it("clamps Seedance 2.5 1080p requests to 720p without dropping framing", () => {
    const prepared = prepareGeneration(
      generateAdOptionsSchema.parse({
        prompt: BRIEF,
        aspectRatio: "16:9",
        resolution: "1080p",
      }),
      DEFAULT_SEEDANCE_MODEL,
    );

    assert.equal(prepared.resolution, "720p");
    assert.equal(prepared.pixelResolution, "1280x720");
    assert.ok(hasFramingRule(prepared.framedPrompt, "16:9"));
  });
});
