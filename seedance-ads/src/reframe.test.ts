import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { prepareGeneration } from "./client.ts";
import { FRAMING_CTA_RULES, hasFramingRule } from "./framing.ts";
import {
  OLS_SERVICES,
  SERVICE_VOICEOVER,
  assertNoMoneyUpfrontGuard,
  buildReframeGenerateOptions,
  buildReframePrompt,
} from "./prompts/reframe.ts";
import { buildSeevioPayload } from "./seevio.ts";
import {
  DEFAULT_SEEDANCE_MODEL,
  REFRAME_BODY_SECONDS,
  generateAdOptionsSchema,
  seedanceDurationSeconds,
} from "./types.ts";

describe("reframe prompts", () => {
  it("keeps the no-money-upfront claim on estate-sales only", () => {
    const estate = buildReframePrompt("estate-sales", "9:16");
    assert.ok(estate.includes("No money upfront"));
    assert.ok(SERVICE_VOICEOVER["estate-sales"].includes("No money upfront"));

    for (const service of OLS_SERVICES) {
      if (service === "estate-sales") continue;
      const prompt = buildReframePrompt(service, "1:1");
      assert.equal(prompt.toLowerCase().includes("no money upfront"), false);
      assertNoMoneyUpfrontGuard(service, prompt);
    }
  });

  it("tells Seedance to skip the original Call Today card", () => {
    const prompt = buildReframePrompt("jewelry", "1:1");
    assert.ok(prompt.includes("Skip the original end-card"));
    assert.equal(prompt.includes("uploaded CTA card"), false);
  });

  it("rejects a jewelry prompt that smuggles the estate-sales claim", () => {
    assert.throws(
      () =>
        assertNoMoneyUpfrontGuard(
          "jewelry",
          "Buy gold. No money upfront - we do the work, you get paid.",
        ),
      /must not include/,
    );
  });
});

describe("reframe generate options", () => {
  it("builds a reference-to-video payload without sending the CTA still to Seedance", () => {
    const raw = buildReframeGenerateOptions({
      service: "jewelry",
      aspectRatio: "16:9",
      sourceVideoUrl: "https://cdn.example.com/jewelry-01.mp4",
    });
    const options = generateAdOptionsSchema.parse(raw);
    const prepared = prepareGeneration(options, DEFAULT_SEEDANCE_MODEL);
    const payload = buildSeevioPayload(options, prepared, DEFAULT_SEEDANCE_MODEL);

    assert.equal(payload.input.generation_type, "reference-to-video");
    assert.equal(payload.input.duration, REFRAME_BODY_SECONDS);
    assert.equal(payload.input.aspect_ratio, "16:9");
    assert.equal(payload.input.generate_audio, true);
    assert.deepEqual(payload.input.video_urls, ["https://cdn.example.com/jewelry-01.mp4"]);
    assert.equal(payload.input.image_urls, undefined);
    assert.ok(hasFramingRule(payload.input.prompt, "16:9"));
    assert.equal(payload.input.prompt.includes(FRAMING_CTA_RULES["16:9"]), false);
    assert.ok(payload.input.prompt.includes("[Video 1]"));
    assert.ok(payload.input.prompt.includes("Skip the original end-card"));
    assert.equal(payload.input.prompt.includes("[Image 1]"), false);
    assert.equal(payload.input.prompt.toLowerCase().includes("no money upfront"), false);
  });

  it("uses a probed source duration when provided", () => {
    const raw = buildReframeGenerateOptions({
      service: "jewelry",
      aspectRatio: "1:1",
      sourceVideoUrl: "https://cdn.example.com/jewelry-01.mp4",
      duration: 18,
    });
    assert.equal(raw.duration, 18);
  });
});

describe("seedanceDurationSeconds", () => {
  it("rounds the OLS masters to 18s and clamps the Seedance window", () => {
    assert.equal(seedanceDurationSeconds(18.06), 18);
    assert.equal(seedanceDurationSeconds(0), REFRAME_BODY_SECONDS);
    assert.equal(seedanceDurationSeconds(2), 4);
    assert.equal(seedanceDurationSeconds(40), 30);
  });
});
