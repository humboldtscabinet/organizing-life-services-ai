import { execFile } from "node:child_process";
import { access } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { promisify } from "node:util";
import {
  CTA_BACKGROUND,
  CTA_BUTTON_TEXT,
  CTA_COPY,
  CTA_GOLD,
  CTA_INK,
} from "./ctaCopy.ts";
import type { AspectRatio } from "./types.ts";

const execFileAsync = promisify(execFile);

const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  "google-chrome",
  "chromium",
  "chromium-browser",
].filter((value): value is string => Boolean(value));

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export async function resolveChromePath(): Promise<string | null> {
  for (const candidate of CHROME_CANDIDATES) {
    try {
      if (candidate.includes("/") || candidate.includes("\\")) {
        await access(candidate);
        return candidate;
      }
      await execFileAsync(candidate, ["--version"], { timeout: 5_000 });
      return candidate;
    } catch {
      // try next
    }
  }
  return null;
}

export function buildCtaHtml(opts: {
  aspectRatio: AspectRatio;
  lockupDataUri: string;
  width: number;
  height: number;
}): string {
  const copy = CTA_COPY;
  const lockup = escapeHtml(opts.lockupDataUri);
  const isWide = opts.aspectRatio === "16:9";
  const stack = `
    <img class="lockup" src="${lockup}" alt="" />
    <div class="copy">
      <h1>${escapeHtml(copy.headline)}</h1>
      <p class="services">${escapeHtml(copy.servicesLine1)}<br />${escapeHtml(copy.servicesLine2)}</p>
      <div class="button">${escapeHtml(copy.button)}</div>
      <p class="url">${escapeHtml(copy.url)}</p>
      <hr class="rule" />
      <p class="footer">${escapeHtml(copy.footer)}</p>
    </div>
  `;

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <style>
    html, body {
      margin: 0;
      width: ${opts.width}px;
      height: ${opts.height}px;
      overflow: hidden;
      background: ${CTA_BACKGROUND};
      color: ${CTA_INK};
      font-family: Inter, "Noto Sans", "Liberation Sans", Arial, sans-serif;
      -webkit-font-smoothing: antialiased;
      text-align: center;
    }
    body {
      display: flex;
      box-sizing: border-box;
      ${
        isWide
          ? "flex-direction: row; align-items: center; justify-content: center; gap: 40px; padding: 40px 56px;"
          : "flex-direction: column; align-items: center; justify-content: center; gap: 16px; padding: 32px 36px 28px;"
      }
    }
    .lockup {
      ${
        isWide
          ? "height: min(82%, 560px); width: auto; max-width: 40%;"
          : "height: min(46%, 440px); width: auto; max-width: 52%;"
      }
      object-fit: contain;
      display: block;
      flex-shrink: 0;
    }
    .copy {
      ${isWide ? "flex: 1; max-width: 620px;" : "width: 100%;"}
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }
    h1, .services, .button, .url, .footer {
      white-space: nowrap;
    }
    h1 {
      margin: 0;
      font-size: ${isWide ? "38px" : "36px"};
      font-weight: 700;
      letter-spacing: -0.02em;
      line-height: 1.15;
    }
    .services {
      margin: 0;
      font-size: ${isWide ? "18px" : "20px"};
      font-weight: 500;
      line-height: 1.4;
    }
    .button {
      margin-top: 2px;
      background: ${CTA_GOLD};
      color: ${CTA_BUTTON_TEXT};
      font-size: ${isWide ? "20px" : "22px"};
      font-weight: 700;
      padding: ${isWide ? "14px 28px" : "15px 30px"};
      border-radius: 999px;
      letter-spacing: 0.01em;
    }
    .url {
      margin: 0;
      font-size: ${isWide ? "17px" : "18px"};
      font-weight: 500;
    }
    .rule {
      border: none;
      border-top: 1px solid #C8C2B8;
      width: min(72%, 380px);
      margin: 6px 0 0;
    }
    .footer {
      margin: 0;
      font-size: ${isWide ? "13px" : "14px"};
      font-weight: 700;
      letter-spacing: 0.12em;
      color: ${CTA_GOLD};
    }
  </style>
</head>
<body>
  ${stack}
</body>
</html>`;
}

export async function screenshotHtml(opts: {
  htmlPath: string;
  outputPath: string;
  width: number;
  height: number;
  chromePath: string;
}): Promise<void> {
  const htmlUrl = pathToFileURL(resolve(opts.htmlPath)).href;
  const screenshotPath = resolve(opts.outputPath);
  try {
    await execFileAsync(
      opts.chromePath,
      [
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--hide-scrollbars",
        "--run-all-compositor-stages-before-draw",
        "--force-device-scale-factor=1",
        "--timeout=8000",
        `--window-size=${opts.width},${opts.height}`,
        `--screenshot=${screenshotPath}`,
        "--virtual-time-budget=2000",
        htmlUrl,
      ],
      { timeout: 15_000 },
    );
  } catch (error) {
    try {
      await access(screenshotPath);
    } catch {
      throw error;
    }
  }
}
