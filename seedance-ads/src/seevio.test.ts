import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { prepareGeneration } from "./client.ts";
import { FRAMING_RULES, hasFramingRule } from "./framing.ts";
import { buildSeevioPayload } from "./seevio.ts";
import {
  DEFAULT_SEEDANCE_MODEL,
  generateAdOptionsSchema,
} from "./types.ts";

const BRIEF = "Estate-sale specialist walking a bright Tampa home, calm and trustworthy.";

describe("buildSeevioPayload", () => {
  it("sends the framed prompt and 9:16 ratio to Seevio", () => {
    const options = generateAdOptionsSchema.parse({
      prompt: BRIEF,
      aspectRatio: "9:16",
      duration: 8,
    });
    const prepared = prepareGeneration(options, DEFAULT_SEEDANCE_MODEL);
    const payload = buildSeevioPayload(options, prepared, DEFAULT_SEEDANCE_MODEL);

    assert.equal(payload.model, "seedance-2-5");
    assert.equal(payload.input.generation_type, "text-to-video");
    assert.equal(payload.input.aspect_ratio, "9:16");
    assert.equal(payload.input.duration, 8);
    assert.equal(payload.input.resolution, "720p");
    assert.ok(hasFramingRule(payload.input.prompt, "9:16"));
    assert.ok(payload.input.prompt.endsWith(FRAMING_RULES["9:16"]));
  });

  it("uses image-to-video + adaptive ratio when a first-frame URL is provided", () => {
    const options = generateAdOptionsSchema.parse({
      prompt: BRIEF,
      aspectRatio: "1:1",
      image: "https://cdn.example.com/first.jpg",
      lastFrameImage: "https://cdn.example.com/cta.jpg",
    });
    const prepared = prepareGeneration(options, DEFAULT_SEEDANCE_MODEL);
    const payload = buildSeevioPayload(options, prepared, DEFAULT_SEEDANCE_MODEL);

    assert.equal(payload.input.generation_type, "image-to-video");
    assert.equal(payload.input.aspect_ratio, "adaptive");
    assert.deepEqual(payload.input.image_urls, [
      "https://cdn.example.com/first.jpg",
      "https://cdn.example.com/cta.jpg",
    ]);
    assert.ok(hasFramingRule(payload.input.prompt, "1:1"));
  });

  it("rejects local image paths because Seevio needs public URLs", () => {
    const options = generateAdOptionsSchema.parse({
      prompt: BRIEF,
      image: "./local.png",
    });
    const prepared = prepareGeneration(options, DEFAULT_SEEDANCE_MODEL);
    assert.throws(
      () => buildSeevioPayload(options, prepared, DEFAULT_SEEDANCE_MODEL),
      /public HTTP\(S\) URL/,
    );
  });
});
