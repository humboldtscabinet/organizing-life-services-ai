import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";
import { filterManifestByService, parseReframeManifest } from "./manifest.ts";
import { OLS_SERVICES } from "./prompts/reframe.ts";

const here = dirname(fileURLToPath(import.meta.url));

describe("reframe manifest", () => {
  it("parses the 14-slot OLS example", () => {
    const raw = JSON.parse(
      readFileSync(resolve(here, "../examples/ols-reframe.manifest.json"), "utf8"),
    ) as unknown;
    const manifest = parseReframeManifest(raw);
    assert.equal(manifest.videos.length, 14);
    assert.equal(manifest.outputDir, "output");
    assert.ok(/^https:\/\//.test(manifest.ctaImageUrl));
    const services = new Set(manifest.videos.map((video) => video.service));
    assert.deepEqual([...services].sort(), [...OLS_SERVICES].sort());
  });

  it("rejects an unknown service", () => {
    assert.throws(
      () =>
        parseReframeManifest({
          ctaImageUrl: "https://cdn.example.com/cta.png",
          videos: [
            {
              id: "x-01",
              service: "cabinets",
              sourceVideoUrl: "https://cdn.example.com/x.mp4",
            },
          ],
        }),
      /Invalid option|Invalid enum|service/i,
    );
  });

  it("rejects local source paths", () => {
    assert.throws(
      () =>
        parseReframeManifest({
          ctaImageUrl: "https://cdn.example.com/cta.png",
          videos: [
            {
              id: "x-01",
              service: "jewelry",
              sourceVideoUrl: "./local.mp4",
            },
          ],
        }),
      /public HTTP/,
    );
  });

  it("filters by service", () => {
    const manifest = parseReframeManifest({
      ctaImageUrl: "https://cdn.example.com/cta.png",
      videos: [
        { id: "j-01", service: "jewelry", sourceVideoUrl: "https://cdn.example.com/j.mp4" },
        { id: "e-01", service: "estate-sales", sourceVideoUrl: "https://cdn.example.com/e.mp4" },
      ],
    });
    const jewelry = filterManifestByService(manifest, "jewelry");
    assert.deepEqual(
      jewelry.videos.map((video) => video.id),
      ["j-01"],
    );
    assert.throws(() => filterManifestByService(manifest, "cleanouts"), /No videos/);
  });
});
