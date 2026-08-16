# OLS Google Ads remakes — 1:1 and 16:9

Production remakes of the 14 existing ~18s 9:16 masters into native **1:1** and **16:9** for Google Ads. Pipeline: Seedance `seedance-2-5` via Seevio (`reference-to-video`, 720p, ~18s) → ffmpeg replaces the last 3s with the Shopify CTA and muxes the original voiceover.

Agent run: [Google ads generated videos](https://cursor.com/agents/bc-a3bf2d04-d43a-43f7-a763-eaad52619bdf)

Do **not** send the CTA still to Seedance. Do **not** regenerate 9:16 through Seedance unless asked (`--with-vertical` is ffmpeg-only).

Keepers are tracked in the repo so they show in the file explorer, one folder per service:

```
google-ads/{service}/{id}-{ratio}.mp4
```

## Status (2026-08-14)

| Service | 01 1:1 | 01 16:9 | 02 1:1 | 02 16:9 | Notes |
| --- | --- | --- | --- | --- | --- |
| jewelry | done | done | done | done | Operator approved. See [`jewelry-reframe-log.md`](jewelry-reframe-log.md). |
| estate-sales | done | done | done | done | Keepers written 2026-08-14. |
| liquidation | done | **removed** | **removed** | **removed** | `01-16x9`, `02-16x9`, and `02-1x1` deleted 2026-08-16 (gibberish box labels). |
| downsizing | done | done | done | done | |
| cleanouts | done | **removed** | done | done | `cleanouts-01-16x9.mp4` deleted 2026-08-16 (glitch). |
| listing-prep | done | **removed** | done | done | `listing-prep-01-16x9.mp4` deleted 2026-08-16 (quality issue). 01 1:1 had needed one Seedance retry. |
| appraisals | done | done | done | done | 02 16:9 needed one Seedance retry (video-edit routing). |

**23** keepers remain in `google-ads/{service}/`. Removed for quality: `cleanouts-01-16x9.mp4` (glitch); `liquidation-01-16x9.mp4`, `liquidation-02-16x9.mp4`, `liquidation-02-1x1.mp4` (gibberish box labels); `listing-prep-01-16x9.mp4` (quality issue). Last 3s restamped 2026-08-16 with native-ratio CTA canvases (ffmpeg only).

Post-upload audit (2026-08-16): [`google-ads-upload-audit-2026-08-16.md`](google-ads-upload-audit-2026-08-16.md). Live Ads API was not queried. Newly flagged for the same box-label issue: `downsizing-01-16x9.mp4`, `cleanouts-02-16x9.mp4`.

## Estate-sales keepers (2026-08-14)

| File | Pixels | Duration | Encode |
| --- | --- | --- | --- |
| `estate-sales-01-1x1.mp4` | 960×960 | ~18.08s | H.264 Main, AAC LC ~192k |
| `estate-sales-01-16x9.mp4` | 1280×720 | ~18.08s | same |
| `estate-sales-02-1x1.mp4` | 960×960 | ~18.08s | same |
| `estate-sales-02-16x9.mp4` | 1280×720 | ~18.08s | same |

Last frame of each file is the “Ready to Get Started?” card (native 1:1 or 16:9 canvas), not the old “Call Today” card. Opening shots are estate-sale interiors / specialist, matching the 9:16 masters.

Download copies (right-click → Download in the file explorer):

- [`google-ads/`](../../google-ads/) — one folder per service

Play locally if in-chat video looks silent (players often start muted).

## How

```bash
cd seedance-ads
npx tsx scripts/reframe-ad.ts --manifest examples/ols-reframe.manifest.json --service <id>
```

- Model: `seedance-2-5`, `reference-to-video`, 720p, 18s, source MP4 in `video_urls` only.
- ffmpeg **replaces** last 3s with a native-ratio CTA canvas from [`OLS_CTA_Card_Google_Ads.png`](https://cdn.shopify.com/s/files/1/0294/7966/5708/files/OLS_CTA_Card_Google_Ads.png?v=1786654544).
- Original VO is muxed; it already ends before the end-card, so the CTA hold is silent like the masters.
- Encode: H.264 Main, no B-frames, 192k AAC, `+faststart`.

## Native CTA canvases (2026-08-16)

Do **not** send the card through Seedance — generated text comes back misspelled or warped. Canvases live in [`google-ads/cta/`](../../google-ads/cta/):

| File | Pixels | How it is built |
| --- | --- | --- |
| `cta-9x16.png` | 720×1280 | Uniform scale of the Shopify master (original pixels, cream pad if needed) |
| `cta-1x1.png` | 960×960 | Logo lockup cropped from the master + locked copy, screenshot in Chrome |
| `cta-16x9.png` | 1280×720 | Same locked copy, wide layout |

Locked wording (verbatim): `Ready to Get Started?` / `Estate Sales - Liquidation - Downsizing` / `Cleanouts - Appraisals - Jewelry Buying` / `Get Your Free Consultation` / `organizinglifeservices.com` / `PROFESSIONAL - RELIABLE - TRUSTED`. The ORGANIZING / LIFE SERVICES / “Licensed, Trusted & Insured Since 2010” lockup is never re-typeset.

```bash
cd seedance-ads
npx tsx scripts/render-cta.ts
npx tsx scripts/restamp-cta.ts   # ffmpeg-only swap of the last 3s on existing keepers
```
