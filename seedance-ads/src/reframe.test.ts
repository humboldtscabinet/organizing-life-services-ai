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
  it("builds a reference-to-video payload with 16s body and CTA [Image 1]", () => {
    const raw = buildReframeGenerateOptions({
      service: "jewelry",
      aspectRatio: "16:9",
      sourceVideoUrl: "https://cdn.example.com/jewelry-01.mp4",
      ctaImageUrl: "https://cdn.example.com/cta-9x16.png",
    });
    const options = generateAdOptionsSchema.parse(raw);
    const prepared = prepareGeneration(options, DEFAULT_SEEDANCE_MODEL);
    const payload = buildSeevioPayload(options, prepared, DEFAULT_SEEDANCE_MODEL);

    assert.equal(payload.input.generation_type, "reference-to-video");
    assert.equal(payload.input.duration, REFRAME_BODY_SECONDS);
    assert.equal(payload.input.aspect_ratio, "16:9");
    assert.deepEqual(payload.input.video_urls, ["https://cdn.example.com/jewelry-01.mp4"]);
    assert.deepEqual(payload.input.image_urls, ["https://cdn.example.com/cta-9x16.png"]);
    assert.ok(hasFramingRule(payload.input.prompt, "16:9"));
    assert.ok(payload.input.prompt.includes(FRAMING_CTA_RULES["16:9"]));
    assert.ok(payload.input.prompt.includes("[Video 1]"));
    assert.ok(payload.input.prompt.includes("[Image 1]"));
    assert.equal(payload.input.prompt.toLowerCase().includes("no money upfront"), false);
  });
});
