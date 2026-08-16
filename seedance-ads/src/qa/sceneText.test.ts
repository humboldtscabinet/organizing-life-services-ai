import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  classifySceneText,
  classifyToken,
  tokenizeSceneText,
} from "./sceneText.ts";

describe("tokenizeSceneText", () => {
  it("keeps letter runs of three or more", () => {
    assert.deepEqual(tokenizeSceneText("FRAGILE  KITCHEN! books 12 HOX"), [
      "FRAGILE",
      "KITCHEN",
      "books",
      "HOX",
    ]);
  });
});

describe("classifyToken", () => {
  it("passes real packing labels", () => {
    for (const word of ["KITCHEN", "FRAGILE", "BOOKS", "LINENS", "kitchen", "Fragile"]) {
      const result = classifyToken(word);
      assert.equal(result.verdict, "ok", `${word} should pass`);
    }
  });

  it("fails HOX / DOX / PATX-style scribbles", () => {
    for (const word of ["HOX", "DOX", "PATX"]) {
      const result = classifyToken(word);
      assert.equal(result.verdict, "gibberish", `${word} should fail`);
    }
  });

  it("fails near-miss spellings of packing words", () => {
    const kitchen = classifyToken("KICHEN");
    assert.equal(kitchen.verdict, "misspelling");
    const fragile = classifyToken("FRAGLE");
    assert.equal(fragile.verdict, "misspelling");
  });

  it("passes plausible English that is not a packing label", () => {
    assert.equal(classifyToken("mahogany").verdict, "ok");
    assert.equal(classifyToken("antique").verdict, "ok");
    assert.equal(classifyToken("armoire").verdict, "ok");
  });
});

describe("classifySceneText", () => {
  it("passes a frame of real labels", () => {
    const report = classifySceneText("FRAGILE\nKITCHEN  BOOKS");
    assert.equal(report.pass, true);
    assert.equal(report.failures.length, 0);
  });

  it("fails a frame with invented box lettering", () => {
    const report = classifySceneText("HOX  DOX  PATX");
    assert.equal(report.pass, false);
    assert.deepEqual(
      report.failures.map((item) => item.token),
      ["HOX", "DOX", "PATX"],
    );
  });

  it("fails Seedance-drawn CTA copy in the body", () => {
    const report = classifySceneText("Ready to Get Started? organizinglifeservices.com");
    assert.equal(report.pass, false);
    assert.ok(report.failures.some((item) => item.verdict === "cta"));
  });
});
