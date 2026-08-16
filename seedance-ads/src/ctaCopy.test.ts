import assert from "node:assert/strict";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, it } from "node:test";
import { ffmpegAvailable, runFfprobe } from "./compose.ts";
import { CTA_COPY, CTA_COPY_STRINGS } from "./ctaCopy.ts";
import { buildCtaHtml, resolveChromePath, screenshotHtml } from "./ctaLayout.ts";

describe("CTA copy lock", () => {
  it("keeps the Shopify master wording verbatim", () => {
    assert.equal(CTA_COPY.headline, "Ready to Get Started?");
    assert.equal(CTA_COPY.servicesLine1, "Estate Sales - Liquidation - Downsizing");
    assert.equal(CTA_COPY.servicesLine2, "Cleanouts - Appraisals - Jewelry Buying");
    assert.equal(CTA_COPY.button, "Get Your Free Consultation");
    assert.equal(CTA_COPY.url, "organizinglifeservices.com");
    assert.equal(CTA_COPY.footer, "PROFESSIONAL - RELIABLE - TRUSTED");
  });

  it("embeds every locked string in the 1:1 and 16:9 HTML layouts", () => {
    for (const aspectRatio of ["1:1", "16:9"] as const) {
      const html = buildCtaHtml({
        aspectRatio,
        lockupDataUri: "data:image/png;base64,AAAA",
        width: 960,
        height: aspectRatio === "1:1" ? 960 : 720,
      });
      for (const line of CTA_COPY_STRINGS) {
        assert.ok(html.includes(line), `missing "${line}" in ${aspectRatio}`);
      }
      assert.equal(html.includes("Call Today"), false);
      assert.equal((html.match(/organizinglifeservices\.com/g) ?? []).length, 1);
      assert.ok(html.includes("white-space: nowrap"));
      assert.ok(!html.includes("Call Today for an Offer"));
    }
  });

  it("screenshots native layouts at the requested pixel size", async (t) => {
    if (!(await ffmpegAvailable())) {
      t.skip("ffmpeg is not on PATH");
      return;
    }
    const chromePath = await resolveChromePath();
    if (!chromePath) {
      t.skip("Chrome is not on PATH");
      return;
    }

    const dir = await mkdtemp(path.join(tmpdir(), "cta-layout-"));
    try {
      const html = buildCtaHtml({
        aspectRatio: "1:1",
        lockupDataUri:
          "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
        width: 960,
        height: 960,
      });
      const htmlPath = path.join(dir, "cta.html");
      const outputPath = path.join(dir, "cta.png");
      await writeFile(htmlPath, html, "utf8");
      await screenshotHtml({
        htmlPath,
        outputPath,
        width: 960,
        height: 960,
        chromePath,
      });
      const raw = await runFfprobe([
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=p=0:s=x",
        outputPath,
      ]);
      const [width, height] = raw.split("x").map((part) => Number(part));
      assert.ok(width && height, `could not probe screenshot: ${raw}`);
      assert.ok(Math.abs(width - 960) <= 16, `width ${width}`);
      assert.ok(Math.abs(height - 960) <= 16, `height ${height}`);
    } finally {
      await rm(dir, { recursive: true, force: true });
    }
  });
});
