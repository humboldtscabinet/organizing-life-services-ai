# OLS Google Ads remakes — 1:1 and 16:9

Production remakes of the 14 existing ~18s 9:16 masters into native **1:1** and **16:9** for Google Ads. Pipeline: Seedance `seedance-2-5` via Seevio (`reference-to-video`, 720p, ~18s) → ffmpeg replaces the last 3s with the Shopify CTA and muxes the original voiceover.

Agent run: [Google ads generated videos](https://cursor.com/agents/bc-a3bf2d04-d43a-43f7-a763-eaad52619bdf)

Do **not** send the CTA still to Seedance. Do **not** regenerate 9:16 through Seedance unless asked (`--with-vertical` is ffmpeg-only). MP4s are gitignored.

## Status (2026-08-14)

| Service | 01 1:1 | 01 16:9 | 02 1:1 | 02 16:9 | Notes |
| --- | --- | --- | --- | --- | --- |
| jewelry | done | done | done | done | Operator approved. See [`jewelry-reframe-log.md`](jewelry-reframe-log.md). |
| estate-sales | done | done | done | done | Keepers written 2026-08-14. |
| liquidation | blocked | blocked | blocked | blocked | Seevio HTTP 402 `insufficient_credits` after estate-sales. |
| downsizing | blocked | blocked | blocked | blocked | Same 402. |
| cleanouts | blocked | blocked | blocked | blocked | Same 402. |
| listing-prep | blocked | blocked | blocked | blocked | Same 402. |
| appraisals | blocked | blocked | blocked | blocked | Same 402. |

Each Seedance job reserves **444 credits**. After estate-sales the Seevio key had **426 available** (18 short of the next job). Remaining: **20 jobs × 444 = 8,880 credits** (top up by at least **8,454**).

Top up at [seevio.ai](https://seevio.ai), then:

```bash
cd seedance-ads
npx tsx scripts/reframe-ad.ts --manifest examples/ols-reframe.manifest.json \
  --service liquidation --skip-existing --output /opt/cursor/artifacts/seedance-reframe-all
```

`--skip-existing` leaves finished keepers in place. The CLI stops the rest of the batch on `insufficient_credits`.

## Estate-sales keepers (2026-08-14)

| File | Pixels | Duration | Encode |
| --- | --- | --- | --- |
| `estate-sales-01-1x1.mp4` | 960×960 | ~18.08s | H.264 Main, AAC LC ~192k |
| `estate-sales-01-16x9.mp4` | 1280×720 | ~18.08s | same |
| `estate-sales-02-1x1.mp4` | 960×960 | ~18.08s | same |
| `estate-sales-02-16x9.mp4` | 1280×720 | ~18.08s | same |

Last frame of each file is the Shopify “Ready to Get Started?” card (contain, cream pad `#F7F4EE`), not the old “Call Today” card. Opening shots are estate-sale interiors / specialist, matching the 9:16 masters.

Download copies (this UI’s chat links do not work — use the file explorer, right-click → Download):

- `seedance-ads/output/estate-sales-downloads/`
- `/opt/cursor/artifacts/seedance-reframe-estate-sales/`
- `/opt/cursor/artifacts/ols-estate-sales-ads.zip`

Play locally if in-chat video looks silent (players often start muted).

## How

```bash
cd seedance-ads
npx tsx scripts/reframe-ad.ts --manifest examples/ols-reframe.manifest.json --service <id>
```

- Model: `seedance-2-5`, `reference-to-video`, 720p, 18s, source MP4 in `video_urls` only.
- ffmpeg **replaces** last 3s with [`OLS_CTA_Card_Google_Ads.png`](https://cdn.shopify.com/s/files/1/0294/7966/5708/files/OLS_CTA_Card_Google_Ads.png?v=1786654544).
- Original VO is muxed; it already ends before the end-card, so the CTA hold is silent like the masters.
- Encode: H.264 Main, no B-frames, 192k AAC, `+faststart`.
