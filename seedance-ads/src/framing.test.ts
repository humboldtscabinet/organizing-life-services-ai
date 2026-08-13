import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  FRAMING_RULES,
  buildPrompt,
  hasFramingRule,
} from "./framing.ts";
import { ASPECT_RATIOS } from "./types.ts";

describe("framing rules", () => {
  it("defines exactly the three Google Ads ratios", () => {
    assert.deepEqual(Object.keys(FRAMING_RULES), ["9:16", "1:1", "16:9"]);
    assert.deepEqual([...ASPECT_RATIOS], ["9:16", "1:1", "16:9"]);
  });

  it("keeps the required 9:16 copy", () => {
    assert.equal(
      FRAMING_RULES["9:16"],
      "Frame vertically for 9:16 mobile. Keep the subject and any action centered in the middle third. Prefer tighter shots. Leave room above and below for the end card. End on the uploaded CTA card filling the full 9:16 frame for the final 3 seconds.",
    );
  });

  it("keeps the required 1:1 copy", () => {
    assert.equal(
      FRAMING_RULES["1:1"],
      "Frame for a 1:1 square. Center the composition. Use medium shots with balanced headroom. End on the uploaded CTA card filling the full 1:1 frame for the final 3 seconds.",
    );
  });

  it("keeps the required 16:9 copy", () => {
    assert.equal(
      FRAMING_RULES["16:9"],
      "Frame cinematically for 16:9 widescreen. Prefer wider establishing shots. Place the subject slightly off-center with clean negative space. End on the uploaded CTA card filling the full 16:9 frame for the final 3 seconds.",
    );
  });
});

describe("buildPrompt", () => {
  const brief = "Warm kitchen, organizer folding linens, natural window light.";

  for (const ratio of ASPECT_RATIOS) {
    it(`appends the ${ratio} framing rule on every call`, () => {
      const framed = buildPrompt(brief, ratio);
      assert.ok(framed.startsWith(brief));
      assert.ok(hasFramingRule(framed, ratio));
      assert.ok(framed.endsWith(FRAMING_RULES[ratio]));
      for (const other of ASPECT_RATIOS) {
        if (other !== ratio) {
          assert.equal(hasFramingRule(framed, other), false);
        }
      }
    });
  }

  it("does not duplicate framing if it is already present", () => {
    const once = buildPrompt(brief, "9:16");
    const twice = buildPrompt(once, "9:16");
    const matches = twice.split(FRAMING_RULES["9:16"]).length - 1;
    assert.equal(matches, 1);
  });

  it("rejects an empty prompt", () => {
    assert.throws(() => buildPrompt("   ", "1:1"), /empty/i);
  });
});
