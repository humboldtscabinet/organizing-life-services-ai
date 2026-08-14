# Jewelry reframe log — 2026-08-14

First live production batch of OLS Google Ads remakes: existing 9:16 jewelry masters → native **1:1** and **16:9**, original voiceover muxed in, Shopify CTA replacing the old “Call Today” end-card.

Agent run: [Google ads generated videos](https://cursor.com/agents/bc-a3bf2d04-d43a-43f7-a763-eaad52619bdf)

## What

Four keepers (operator approved 2026-08-14):

| File | Ratio | Pixels | Notes |
| --- | --- | --- | --- |
| `jewelry-01-1x1.mp4` | 1:1 | 960×960 | ~18.08s |
| `jewelry-01-16x9.mp4` | 16:9 | 1280×720 | ~18.08s |
| `jewelry-02-1x1.mp4` | 1:1 | 960×960 | Opening freeze trimmed 0.25s (~17.84s) |
| `jewelry-02-16x9.mp4` | 16:9 | 1280×720 | ~18.08s |

MP4s are **gitignored** (`seedance-ads/.gitignore`). Local copies live under `seedance-ads/output/` after a live run. Seevio result URLs expire; do not treat the API URL as the archive.

## Why

Cannot losslessly re-aspect 9:16 → 1:1 / 16:9. Seedance 2.5 regenerates the new ratio from `[Video 1]`. ffmpeg then:

1. **Replaces** the last 3 seconds with [`OLS_CTA_Card_Google_Ads.png`](https://cdn.shopify.com/s/files/1/0294/7966/5708/files/OLS_CTA_Card_Google_Ads.png?v=1786654544) (contain, cream pad `#F7F4EE`, no stretch).
2. **Muxes the original source voiceover** onto the remake (the original VO already ends before the end-card, so the CTA hold is silent like the masters).

## How

```bash
cd seedance-ads
npx tsx scripts/reframe-ad.ts --manifest examples/ols-reframe.manifest.json --service jewelry
```

- Model: `seedance-2-5` via Seevio (`reference-to-video`, 720p, 18s).
- CTA still is **not** sent to Seedance (`image_urls` empty). Sending it made the model render a card, then ffmpeg added another.
- Encode: H.264 Main, no B-frames, 192k AAC, `+faststart` (chat/browser players otherwise looked silent).
- Credits: **444 per job**, **1,776** for the four jewelry outputs. One extra 444-credit retry of `jewelry-02` 1:1 still copied the source’s opening hitch, so that clip was trimmed in ffmpeg instead of kept as a second generation.

Related PRs: [#50](https://github.com/humboldtscabinet/organizing-life-services-ai/pull/50) pipeline, [#51](https://github.com/humboldtscabinet/organizing-life-services-ai/pull/51) VO + single CTA, [#52](https://github.com/humboldtscabinet/organizing-life-services-ai/pull/52) browser-safe encode.

## Issues found and how they were fixed

| Issue | Cause | Fix |
| --- | --- | --- |
| Duplicate CTA (old “Call Today” then Shopify card) | Source already ends on an end-card; Seedance copied it; ffmpeg **appended** 3s more | Stop sending the CTA still to Seedance. ffmpeg **replaces** last 3s |
| “No sound” in chat | Audio **was** muxed; in-chat player starts muted / some players skip AAC High+B-frames. First ~4s of jewelry-01 VO is also quiet on the masters | Re-encode Main/no-B-frames/192k AAC. Play downloaded MP4s locally |
| `jewelry-02-1x1` opening glitch (repeated/frozen first frame) | Same hitch exists on the 9:16 master; 1:1 crop made it obvious. A full Seedance retry reproduced it | Drop first 0.25s of that one file (A/V stay in sync) |

## Result / next

Jewelry 01/02 × 1:1 and 16:9 are approved keepers. Remaining services in the manifest (2 clips each): estate-sales, liquidation, downsizing, cleanouts, listing-prep, appraisals.

```bash
npx tsx scripts/reframe-ad.ts --manifest examples/ols-reframe.manifest.json --service estate-sales
```
