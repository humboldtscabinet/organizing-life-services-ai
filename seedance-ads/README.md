# seedance-ads

TypeScript pipeline for **Google Ads / Performance Max** video creatives with ByteDance **Seedance** via **[Seevio](https://seevio.ai)**.

**Production path:** remake existing 19s 9:16 OLS ads into native **1:1** and **16:9**. Seedance cannot losslessly re-aspect a file — 1:1 / 16:9 outputs are new generations that follow `[Video 1]`. ffmpeg then **replaces the last 3 seconds** with the Shopify CTA still (so the original “Call Today” card is not left in the file) and **muxes the original voiceover** onto the remake.

Seedance 2.5 maxes out at **720p**. Combined reference-video duration must be **≤ 30s** (one 19s source per job is fine).

## Setup

```bash
cd seedance-ads
npm install
cp .env.example .env
```

```bash
SEEDANCE_API_KEY=sk_live_your-seevio-key
SEEDANCE_MODEL=seedance-2-5
SEEDANCE_PROVIDER=seevio
```

Create or rotate keys at [seevio.ai/dashboard/user/api-keys](https://seevio.ai/dashboard/user/api-keys). **Do not paste the key in chat.** For Cloud Agents, add `SEEDANCE_API_KEY` as a Runtime Secret, then restart the agent.

ffmpeg must be on PATH for CTA canvases and replacing the original end-card.

## Reframe an existing 9:16 ad (recommended)

1. The 14 source MP4s and the 9:16 CTA still are already in [`examples/ols-reframe.manifest.json`](examples/ols-reframe.manifest.json).
2. Dry-run, then live-run one service batch.

```bash
npx tsx scripts/reframe-ad.ts --manifest examples/ols-reframe.manifest.json --dry-run
npx tsx scripts/reframe-ad.ts --manifest examples/ols-reframe.manifest.json --service estate-sales
npx tsx scripts/reframe-ad.ts --video https://cdn.shopify.com/.../jewelry-01.mp4 \
  --cta https://cdn.shopify.com/.../cta-9x16.png \
  --service jewelry --ratios 1:1,16:9
```

| Output | How it is built |
| --- | --- |
| 1:1, 16:9 | Seedance `reference-to-video` for **~18s** from the 9:16 MP4 (no CTA still in the prompt). ffmpeg **replaces the last 3s** with the Shopify card and muxes the original voiceover. |
| 9:16 (`--with-vertical`) | Original file; ffmpeg only replaces the last 3s with the Shopify card and keeps the original audio. No Seedance. |

Keepers land in `output/reframe/{service}/{id}-{ratio}.mp4` (gitignored).

**Jewelry (first live batch, 2026-08-14):** four keepers approved. Process, credits, and fixes are in [`docs/jewelry-reframe-log.md`](docs/jewelry-reframe-log.md).

`--dry-run` prints the framed prompt, `video_urls`, and duration with no API call. The CTA still is not sent to Seedance.

## Framing

Do **not** paste framing into `--prompt`. `buildPrompt()` appends the ratio rule. A CTA hold line is added only when a CTA image is provided; otherwise the model is told not to invent an end card.

## One-line text-to-video (smoke test only)

```bash
npx tsx scripts/generate-ad.ts \
  --prompt "Estate-sale specialist walking a bright Tampa home, calm and trustworthy." \
  --ratio 9:16 --duration 8 --dry-run
```

This invents people, homes, and branding. Do not use it for production OLS ads.

`--brief ols` still exists for stills-only reference-to-video from first-party sale photos. It is not the workflow for these 14 masters.

## Project structure

```
seedance-ads/
├── examples/ols-reframe.manifest.json
├── docs/jewelry-reframe-log.md   First live jewelry batch (2026-08-14)
├── scripts/reframe-ad.ts         Production remake + Shopify CTA replace
├── scripts/generate-ad.ts        Generic generate / smoke test
└── src/
    ├── prompts/reframe.ts        Recreate-this-ad prompts + service VO
    ├── manifest.ts               Batch JSON schema
    ├── cta.ts                    9:16 / 1:1 / 16:9 CTA canvases
    ├── compose.ts                ffmpeg: replace last 3s + mux original VO
    ├── seevio.ts                 Seevio HTTP client
    └── framing.ts                Google Ads framing rules
```

## Scripts

| Command | Purpose |
| --- | --- |
| `npm test` | Framing, payload, manifest, prompt tests (no API key) |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run reframe -- --manifest examples/ols-reframe.manifest.json --dry-run` | Print remake payloads |
| `npm run generate -- --prompt "..." --ratio 9:16 --dry-run` | Smoke-test generate CLI |

Videos download to `./output/`. Seevio result URLs expire; keep the local files.
