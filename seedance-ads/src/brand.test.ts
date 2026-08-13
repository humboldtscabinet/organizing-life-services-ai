import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  OLS_BRAND,
  OLS_REFERENCE_IMAGES,
  appendReferenceGuidance,
  buildOlsPrompt,
  resolveNamedBrief,
} from "./brand.ts";

describe("OLS brand brief", () => {
  it("uses first-party facts only", () => {
    const prompt = buildOlsPrompt();
    assert.ok(prompt.includes(OLS_BRAND.legalName));
    assert.ok(prompt.includes("Tampa Bay"));
    assert.ok(prompt.includes("Pinellas"));
    assert.ok(prompt.includes("since 2010"));
    assert.ok(prompt.includes("Do not invent people"));
    assert.equal(prompt.includes("Estate-sale specialist walking"), false);
  });

  it("numbers every curated sale photo as [Image N]", () => {
    const prompt = buildOlsPrompt();
    for (const [index, image] of OLS_REFERENCE_IMAGES.entries()) {
      assert.ok(prompt.includes(`[Image ${index + 1}]`));
      assert.ok(prompt.includes(image.description.slice(0, 24)));
    }
    assert.equal(OLS_REFERENCE_IMAGES.length, 6);
  });

  it("resolveNamedBrief(ols) returns the prompt and public Shopify URLs", () => {
    const brief = resolveNamedBrief("ols");
    assert.equal(brief.prompt, buildOlsPrompt());
    assert.deepEqual(
      brief.referenceImages,
      OLS_REFERENCE_IMAGES.map((image) => image.url),
    );
    for (const url of brief.referenceImages ?? []) {
      assert.ok(url.startsWith("https://cdn.shopify.com/"));
    }
  });

  it("skips homepage stock art that is not a real sale photo", () => {
    const urls = OLS_REFERENCE_IMAGES.map((image) => image.url).join("\n");
    assert.equal(urls.includes("estate-sale-palm-harbor"), false);
    assert.equal(urls.includes("estate-sale-pinellas-county"), false);
  });
});

describe("appendReferenceGuidance", () => {
  it("is a no-op when the prompt already names Image 1", () => {
    const prompt = "Use [Image 1] teak credenza as the first shot.";
    assert.equal(appendReferenceGuidance(prompt, 2), prompt);
  });

  it("adds Image labels when the caller only passed URLs", () => {
    const guided = appendReferenceGuidance("Slow pan across the staged kitchen.", 3);
    assert.ok(guided.includes("[Image 1]"));
    assert.ok(guided.includes("[Image 3]"));
    assert.ok(guided.includes("Do not invent people"));
  });
});
