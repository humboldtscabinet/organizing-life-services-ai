# Build this Seedance aspect-ratio pipeline for another company

This is the playbook for cloning the Organizing Life Services (OLS) system onto a new brand. The OLS repo is a working reference, not a drop-in white-label. Seedance cannot crop a 9:16 file into 1:1 or 16:9. It **regenerates** the story in the new frame. ffmpeg then stamps a **native-ratio CTA** and muxes the **original voiceover**.

If you skip that split (model for picture, ffmpeg for brand), you will ship stretched cards, duplicate end-cards, invented phone numbers, and gibberish box labels.

## What you are building

A small TypeScript package that turns existing **vertical (~19s) masters** into Google Ads / Performance Max keepers:

| Output | How it is made |
| --- | --- |
| **1:1** (960×960 at 720p) | Seedance `reference-to-video` of `[Video 1]`, then ffmpeg replaces the last 3s |
| **16:9** (1280×720 at 720p) | Same as 1:1, with widescreen framing |
| **9:16** (720×1280 at 720p) | Original file. ffmpeg only. No Seedance credits. |

Every keeper is H.264 Main, no B-frames, AAC stereo, `+faststart`, so it plays in browsers and Google Ads.

```
9:16 master (HTTPS) ──► Seedance 2.5 ──► body MP4 (1:1 or 16:9)
                              │
                              │  OCR gate on body frames
                              ▼
9:16 CTA PNG ──► native canvases ──► ffmpeg last-3s replace + original VO
                              │
                              ▼
                    google-ads/{service}/{id}-{ratio}.mp4
```

Text-to-video from a prompt is a **smoke test only**. It invents people, rooms, and branding. Production ads always start from a real master.

## Hard limits (do not bargain with these)

These are provider and product constraints, not OLS taste:

1. **Seedance 2.5 maxes at 720p.** Google prefers 1080p. Upload 720p anyway; do not request 1080p and expect it.
2. **Duration is an integer 4–30s.** Combined reference video must be **≤ 30s**. One ~19s master per job is fine.
3. **Seevio only accepts public HTTPS URLs.** Local files are not uploaded. Host masters and the CTA PNG on Shopify CDN, S3, or equivalent.
4. **Reference-to-video is a new generation**, not a crop. Expect drift: extra objects, warped hands, invented lettering on props.
5. **Do not send the CTA still to Seedance.** Passing it as `lastFrameImage` makes the model paint a card in the body. ffmpeg would then add a second card.
6. **Do not send CTA copy through the model.** Logo lockup stays as cropped pixels. Body copy is locked strings rendered in HTML + headless Chrome.
7. **Scene-text QA does not refund credits.** OCR runs after the Seevio job. A fail leaves the body in `_work/` and does not retry.
8. **Credits are real money.** OLS jewelry was **444 credits per ratio**. Four keepers (two masters × 1:1 + 16:9) cost 1,776. Dry-run until the payload is right.

## This repo’s file map

All paths below are relative to `seedance-ads/`.

| Path | Layer |
| --- | --- |
| `src/types.ts` | Ratio trio, pixel sizes, duration clamp |
| `src/framing.ts` | Mandatory 9:16 / 1:1 / 16:9 prompt tails |
| `src/client.ts` | `prepareGeneration()` — framing cannot be skipped |
| `src/seevio.ts` | Seevio HTTP payload |
| `src/generate.ts` | Single-ratio and full-set helpers |
| `src/compose.ts` | ffmpeg: replace last 3s, mux original VO |
| `src/cta.ts` | 9:16 scale vs native 1:1 / 16:9 canvases |
| `src/ctaLayout.ts` | HTML/CSS for native cards + Chrome screenshot |
| `src/ctaCopy.ts` | **Rewrite:** locked strings, colors, lockup crop |
| `src/brand.ts` | **Rewrite:** legal name, region, stills-only brief |
| `src/prompts/reframe.ts` | **Rewrite:** services, VOs, text/claim rules |
| `src/manifest.ts` | Manifest schema (service enum comes from prompts) |
| `src/qa/sceneText.ts` | **Rewrite:** allowed labels + body CTA phrases |
| `src/qa/sceneTextQa.ts` | Tesseract sampling of body frames |
| `scripts/reframe-ad.ts` | Production remake CLI |
| `scripts/render-cta.ts` | CTA stills only |
| `scripts/restamp-cta.ts` | ffmpeg restamp of existing keepers |
| `scripts/generate-ad.ts` | Smoke-test generate (not production remakes) |
| `examples/ols-reframe.manifest.json` | Replace with the new company’s public URLs |
| `../google-ads/{service}/` | Keeper MP4s |
| `../google-ads/cta/` | Native CTA PNGs |

## Architecture: what to copy vs what to replace

Think in four layers. Copy the first two. Rewrite the last two for the new company.

### Layer 1 — Ratio contract (copy)

| File | Job |
| --- | --- |
| `src/types.ts` | Canonical trio `9:16` / `1:1` / `16:9`, pixel map, 3s CTA hold, duration clamp |
| `src/framing.ts` | Mandatory framing sentences appended to every prompt |
| `src/client.ts` `prepareGeneration()` | Single choke point so no caller can skip framing |
| `src/seevio.ts` | HTTP payload: `aspect_ratio`, `generation_type`, public URLs |
| `src/generate.ts` | `generateSingleAd` / `generateFullAdSet` |

Framing is **not** a style hint. `buildPrompt()` appends exactly one ratio rule. Callers must not paste framing into `--prompt` (that duplicates it). A CTA-hold sentence is added **only** if a last-frame image is actually sent — production remakes omit it.

Current framing intent:

- **9:16** — subject in the middle third, tighter shots, clean top/bottom
- **1:1** — centered, medium shots, balanced headroom
- **16:9** — wider establishing shots, subject slightly off-center, negative space

Every rule also forbids invented logos, phone numbers, websites, watermarks, and end cards.

Image-to-video is a special case: Seevio gets `aspect_ratio: "adaptive"` because the first frame dictates the ratio. Framing for the *requested* ratio is still appended, plus a warning that the source image must already be that ratio. Production remakes use **reference-to-video**, not image-to-video.

### Layer 2 — Post pipeline (copy, then retune)

| File | Job |
| --- | --- |
| `src/compose.ts` | Probe duration/audio, pad to canvas, **replace** last 3s, mux original VO |
| `src/cta.ts` | 9:16 = uniform scale of the master PNG; 1:1 / 16:9 = native HTML screenshot |
| `src/ctaLayout.ts` | Flex layout: column for 1:1, row for 16:9 |
| `src/qa/sceneText.ts` + `sceneTextQa.ts` | Tesseract on frames at ~2s / 8s / 14s (before the CTA) |
| `scripts/reframe-ad.ts` | Production CLI |
| `scripts/render-cta.ts` | Rebuild three CTA canvases with no Seedance call |
| `scripts/restamp-cta.ts` | Swap last 3s on existing keepers (ffmpeg only) |
| `scripts/generate-ad.ts` | Smoke-test generate; not the production path |

`replaceEndingWithCta()` **does not append**. The source already ends on an old card. Appending produced OLS's first failure: old “Call Today” then the new Shopify card. Replacement keeps duration the same. Audio is taken from the **original master**, not from Seedance (the model often returns silence or a paraphrased VO).

Encode settings that mattered in production:

- `-profile:v main -bf 0` (no B-frames)
- AAC ~192k stereo
- `-movflags +faststart`

Chat players and some in-browser Ads previews look mute without that.

### Layer 3 — Brand, services, copy (rewrite)

This is the entire company-specific surface.

| File | What to change |
| --- | --- |
| `src/ctaCopy.ts` | Headline, service lines, button, URL, footer, colors, **lockup crop** |
| `src/brand.ts` | Legal name, phone, region, services, first-party stills (stills-only path) |
| `src/prompts/reframe.ts` | Service IDs, voiceover scripts, “do not invent text” rule, claim guards |
| `src/manifest.ts` | Zod enum of those service IDs |
| `src/qa/sceneText.ts` | Allowed environmental words; CTA phrases that must **not** appear in the body |
| `examples/*.manifest.json` | Public master URLs + CTA URL |
| `scripts/render-cta.ts` / `restamp-cta.ts` | Default CTA URL and output folder |
| Tests that assert exact OLS strings | Update expected copy |

### Layer 4 — Operators and keepers (new tree)

| Path | Job |
| --- | --- |
| `google-ads/{service}/` | Approved keepers only |
| `google-ads/cta/` | Native stills (`cta-9x16.png`, `cta-1x1.png`, `cta-16x9.png`) |
| `google-ads/_work/` | Seedance bodies, QA frames (gitignored) |
| `docs/*-reframe-log.md` | Credits, fails, operator decisions |

---

## Intake: collect this before writing code

Do not start a live batch until you have:

1. **Brand facts** — legal name, short name, domain, phone, claims you are allowed to make, claims that are illegal or exclusive to one service.
2. **Service list** — kebab-case IDs (`hvac-repair`, `roofing`) and a human label for the prompt.
3. **Voiceover per service** — the exact script on the masters, or a locked rewrite. Seedance is told to keep it verbatim; ffmpeg then **throws that audio away** and muxes the original WAV/AAC from the master. The prompt VO still matters because the model lip-syncs / paces to it.
4. **9:16 masters** — one MP4 per ad, public HTTPS, **≤ 30s**, clean documentary footage. Avoid stock people if the brand cannot show them.
5. **One 9:16 CTA master PNG** — logo + locked copy on the brand background. High enough resolution to crop a lockup (OLS master is 1536×2752).
6. **Lockup crop box** — pixel rectangle of logo + wordmark + tagline on that PNG, with **no** headline/button/URL. Measure in any image editor; store as `{ x, y, width, height }` plus the master `{ width, height }`.
7. **Allowed on-screen words** — if the footage has labels (boxes, menus, storefronts), list real English words that may appear. Everything else fails OCR.
8. **Seevio key** — `sk_live_…` from [seevio.ai](https://seevio.ai). Never paste it in chat. For Cloud Agents, use a Runtime Secret named `SEEDANCE_API_KEY`.
9. **Budget** — credits per ratio × masters × 2 (1:1 and 16:9), plus retries. OLS learned not to retry a glitch that already exists on the master.

Legal: if one service may say “no money upfront” and others may not, put that in a **prompt guard** that throws when the forbidden claim leaks into another service’s prompt. OLS does this for estate-sales.

---

## Recommended path: fork this package, then rebrand

Rebuilding from a blank folder is slower and you will miss the framing choke point. Fork `seedance-ads/` (and the `google-ads/` output tree) into the new repo.

### 1. Scaffold

```bash
# Node 20+, ffmpeg, tesseract, Chrome/Chromium on PATH
cd seedance-ads
npm install
cp .env.example .env
```

```
SEEDANCE_API_KEY=sk_live_your-seevio-key
SEEDANCE_MODEL=seedance-2-5
SEEDANCE_PROVIDER=seevio
```

ffmpeg is required for canvases and the last-3s swap. tesseract is required for live remakes (`apt install tesseract-ocr`). Chrome is required for native 1:1 / 16:9 CTA stills; without it the pipeline **letterboxes** the 9:16 PNG (ugly, but shipping-safe).

Keep the tests. `npm test` hits framing, payload, prompts, and OCR classifiers with **no API key**. That is how you know a rebrand did not drop the ratio rule.

### 2. Replace brand constants

**`src/ctaCopy.ts`**

- Put the new headline, service list, button, URL, footer in `CTA_COPY`.
- Set cream/ink/gold (`CTA_BACKGROUND`, `CTA_INK`, `CTA_GOLD`) to the brand palette.
- Set `CTA_MASTER_SIZE` to the PNG’s real pixels (`ffprobe -select_streams v:0 -show_entries stream=width,height`).
- Set `CTA_LOCKUP_CROP` so the crop contains **only** the mark + wordmark + tagline. If the crop includes “Call today”, that lettering will appear on 1:1 and 16:9 cards.

**`src/prompts/reframe.ts`**

- Rename `OLS_SERVICES` to the new IDs.
- Rewrite `SERVICE_VOICEOVER` and `SERVICE_LABEL`.
- Rewrite `RECREATE_CORE` so it names the new region and documentary feel (not “Tampa Bay”).
- Keep the structure: recreate `[Video 1]`, no invented people/rooms, skip original end-card, branded card is ffmpeg later.
- Keep a **no-invented-text** paragraph. Seedance treats “no on-screen text” as “no captions” and still paints fake letters on props. Allow real English; forbid gibberish.
- If some services are prop-heavy (boxes, menus, racks), keep a second rule only for those IDs.
- Add claim guards (exclusive guarantees, pricing, licenses).

**`src/brand.ts`**

- Replace `OLS_BRAND` and first-party stills. Stills must be **real** brand photography, not homepage stock. This file is for the stills-only `--brief` path, not the remake path.

**`src/qa/sceneText.ts`**

- Replace `PACKING_LABELS` with words that honestly appear in the new footage (or a smaller set).
- Replace `CTA_PHRASES` with the new URL, button, headline, and phone. Body frames that contain those strings fail — the model started drawing the end-card.
- Replace the hard-coded `ORGANIZINGLIFESERVICES` token check with the new domain squeezed to letters.

**`src/manifest.ts`**

- Point the service enum at the new ID list.

**Scripts and tests**

- Default CTA URL, default `--output ../google-ads`, service folder names.
- Any `assert.equal(CTA_COPY.headline, "…")` test must use the new locked strings.

### 3. Build native CTA canvases first (no Seedance)

This is the cheapest way to see if lockup crop + copy + colors work.

```bash
npx tsx scripts/render-cta.ts --source https://cdn.example.com/cta-9x16.png
```

Inspect `google-ads/cta/`:

| File | Pixels | Expectation |
| --- | --- | --- |
| `cta-9x16.png` | 720×1280 | Uniform scale of the master. No reflow. |
| `cta-1x1.png` | 960×960 | Cropped lockup on top, locked copy below, no wrapping that changes words |
| `cta-16x9.png` | 1280×720 | Lockup left, copy right (or your layout), same strings |

If 1:1 / 16:9 look letterboxed with huge side bars, Chrome was missing and you got `contain` fallback. Install Chromium and re-render.

Tune `src/ctaLayout.ts` font sizes if a long company name overflows. Keep `white-space: nowrap` on locked lines so Chrome cannot reflow “Get Your Free Consultation” onto two lines unless you deliberately split the string.

### 4. Write a manifest of public masters

```json
{
  "ctaImageUrl": "https://cdn.example.com/cta-9x16.png",
  "outputDir": "../google-ads",
  "videos": [
    {
      "id": "hvac-01",
      "service": "hvac-repair",
      "sourceVideoUrl": "https://cdn.example.com/hvac-01.mp4"
    }
  ]
}
```

IDs are lowercase kebab-case. URLs must be fetchable without cookies.

### 5. Dry-run until the payload is boring

```bash
npx tsx scripts/reframe-ad.ts --manifest examples/acme-reframe.manifest.json --dry-run
```

Read every line:

- `generation_type=reference-to-video`
- `ratio=1:1` or `16:9` (not `adaptive`)
- `video_urls` is the master only
- `image_urls` is **empty** (CTA not sent)
- `framing=true`
- `seedanceRendersCta=false`
- Prompt includes the no-invented-text rule, the service VO, and “skip the original end-card”
- Prompt does **not** include another service’s exclusive claim

`--dry-run` makes no API call. Do not live-run until this printout is correct for **each** service.

### 6. Live-run one service, two ratios

```bash
npx tsx scripts/reframe-ad.ts \
  --manifest examples/acme-reframe.manifest.json \
  --service hvac-repair \
  --ratios 1:1,16:9
```

What the CLI does per ratio:

1. Download master + CTA PNG.
2. Render three canvases into `_work` / `cta`.
3. **If 9:16:** ffmpeg replace last 3s on the original; keep original audio. Stop.
4. **If 1:1 or 16:9:** `prepareGeneration()` → Seevio job at ~source duration (clamped 4–30).
5. Download body to `google-ads/_work/{service}/{id}/`.
6. OCR frames before the last 3s. Fail → no keeper, no retry.
7. `replaceEndingWithCta` with the native canvas + original VO.
8. Write `google-ads/{service}/{id}-1x1.mp4` (or `-16x9`).

`--skip-existing` is safe for resume. `--skip-scene-text-qa` is how you ship gibberish; only use it when an operator has already accepted invented labels.

`--with-vertical` adds 9:16 keepers so each Performance Max asset group has the trio Google wants. OLS shipped 1:1 + 16:9 first and later had **zero** 9:16 keepers in Ads — Google will crop landscape into Shorts if you leave that hole.

### 7. Operator QA (do not skip)

Automated OCR is a floor, not approval. For every keeper:

1. Play locally (not only in chat). First seconds of VO may be quiet on the master.
2. Confirm last 3s are the **new** card, not the old phone slate, not both.
3. Confirm audio is the original VO, in sync, through the card hold (usually silence under the card if the master VO ended already).
4. Scrub ~2s / 8s / 14s for invented text on props, extra people, extra rooms.
5. If a hitch exists on the **master**, do not burn 444 credits retrying. Trim a few hundred milliseconds with ffmpeg instead (OLS jewelry-02 1:1).

Delete rejects from `google-ads/{service}/`. Leave bodies in `_work/` for forensics. Log credits and reasons in `docs/`.

### 8. Restamp without regenerating

Copy changes, new lockup, wrong hold length:

```bash
npx tsx scripts/render-cta.ts
npx tsx scripts/restamp-cta.ts
```

No Seevio call. Keepers are rewritten in place via a temp file so ffmpeg never reads and writes the same MP4.

---

## If you rebuild from scratch

Same layers, same choke points. Minimum viable system:

1. **Types** — `9:16 | 1:1 | 16:9`, pixel table, `CTA_HOLD_SECONDS = 3`, duration clamp.
2. **`buildPrompt(brief, ratio)`** — append canonical framing; refuse empty briefs; do not duplicate.
3. **`prepareGeneration()`** — the only path into the HTTP client; assert framing with `includes(FRAMING_RULES[ratio])`.
4. **Seevio client** — `reference-to-video` with `video_urls: [master]`, `aspect_ratio` set to the target, no CTA image.
5. **CTA renderer** — 9:16 scale; 1:1 / 16:9 crop lockup + HTML screenshot.
6. **ffmpeg replace last N seconds** — pad both streams to `canvasSize(ratio)`; audio from master.
7. **OCR gate** — tesseract on body frames; fail closed.
8. **CLI** — `--dry-run` prints the exact JSON you would POST.
9. **Tests** that lock framing copy, “CTA not in payload”, and service claim guards.

If generation can happen without going through `prepareGeneration()`, framing will eventually be skipped. That is the whole design.

---

## Prompt pattern that actually works

Production remake prompt (structure, not OLS wording):

```
Recreate [Video 1] as a new Google Ads clip in this aspect ratio.
Keep the same documentary story, cuts, pacing, {region} feel, and voiceover.
Do not invent people, rooms, or objects that are not in [Video 1].
No captions, logos, watermarks, phone numbers, or CTA graphics.

{NO_INVENTED_TEXT_RULE}

Skip the original end-card entirely. End on live-action only.
The branded CTA is added later in ffmpeg — do not generate one.

This is a {Brand} {service label} ad.
Voiceover (keep verbatim): "{locked script}"
{optional prop-heavy text rule}
```

Then `buildPrompt()` appends the 1:1 or 16:9 framing sentence.

Do **not**:

- Ask Seedance to “re-aspect” or “crop” the file
- Mention the CTA URL or “uploaded CTA card” on this path
- Say “no on-screen text” without allowing real environmental English
- Put two services’ claims in one prompt

---

## Google Ads / Performance Max notes

- Asset groups want **all three** orientations. Missing 9:16 → Google auto-crops 16:9.
- Technical floors OLS checked: MP4, H.264, AAC, **≥ 10s**, 1:1 or 16:9 (or 9:16).
- Seedance 720p is below Google’s 1080p preference. Still valid HD.
- Upload **keepers only**. Never upload `_work/` bodies (they still have the old end-card or none).
- Original 9:16 masters still end on the old card until you run `--with-vertical`.
- This pipeline does **not** talk to the Google Ads API. Upload is a human step (or a later agent with OAuth + developer token).

---

## Failure modes you should expect

| Symptom | Cause | Fix |
| --- | --- | --- |
| Old card then new card | ffmpeg **appended** or Seedance was given the CTA still | Replace last 3s; `image_urls` empty |
| “No sound” in chat | Player muted / High profile + B-frames | Encode Main, `-bf 0`, 192k AAC; play the file locally |
| Duplicate logo in the body | CTA still sent as last frame | Never set `lastFrameImage` on remakes |
| Gibberish on boxes/menus | Seedance invented letters | Prompt allows real English only; OCR fail closed; do not retry forever |
| Opening freeze | Hitch is on the master | Trim; do not regenerate |
| Square/landscape letterboxed CTA | Chrome missing | Install Chromium; `layout: native` |
| Seevio 402 | Out of credits | Stop the batch (`insufficient_credits` should abort the CLI) |
| QA fail after a long wait | OCR is post-paid | Budget for waste; inspect `_work/` |
| Wrong service claim on VO | Prompt leaked another service’s script | Guard in `buildReframePrompt` + unit test |
| Stretched faces on 16:9 | Model ignored widescreen framing | Check dry-run framing; regenerate once; then cut |

---

## Suggested build order (engineering)

Work in this order so you spend credits last:

1. Copy `types.ts` + `framing.ts` + tests that lock the three sentences.
2. Copy `prepareGeneration()` and Seevio payload builder; test `aspect_ratio` and empty `image_urls`.
3. Rebrand `ctaCopy.ts` + lockup crop; render stills; eyeball 1:1 and 16:9.
4. Copy `compose.ts`; unit-test replace-vs-append on a silent fixture if you can.
5. Rewrite services, VOs, claim guards; `npm test`.
6. Manifest + `--dry-run` for one service.
7. One live 1:1 **or** 16:9 (not both) to learn credit cost and OCR noise.
8. Rest of that service, then other services.
9. `--with-vertical` so Ads gets 9:16.
10. Human upload + a coverage table (1:1 / 16:9 / 9:16 per asset group).

---

## What not to reuse blindly from OLS

- Tampa Bay / Florida residential language
- Estate-sale packing lexicon (Kitchen, Fragile, Books) unless you film boxes
- “No money upfront” and licensed-since-year claims
- Shopify crop numbers `(300, 80, 936×1100)` — they only fit the OLS PNG
- Jewelry-batch credit numbers as a quote (Seevio pricing changes)
- The stills-only `--brief ols` path, unless you also have a first-party photo set

Reuse the **ratio contract**, the **framing choke point**, the **CTA-not-through-the-model** rule, and the **replace last 3s + original VO** compose step. That is the system.
