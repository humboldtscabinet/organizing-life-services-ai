# Google Ads upload audit — 2026-08-16

Post-upload audit of OLS Performance Max video keepers after native-ratio CTA restamp and operator quality cuts. **This cloud agent cannot query customer `548-621-3910`:** `GOOGLE_ADS_*` credentials are unset here, the Ads API is still documented as deferred (OAuth + developer token), and the in-repo Ads client is read-only even when configured. Live asset-group membership was **not** verified against Google. Findings below are from the 23 remaining local MP4s plus sampled frames.

Agent run: [Google ads generated videos](https://cursor.com/agents/bc-a3bf2d04-d43a-43f7-a763-eaad52619bdf)

## Verdict

**Technically valid keepers; operator quality cuts already applied.** Every remaining file meets PMax technical floors (MP4 / H.264 Main / AAC / ≥10s / 1:1 or 16:9), last frames are the native “Ready to Get Started?” card, and audio is real voiceover. Sampled frames still show invented or illegible box lettering on `downsizing-01-16x9` and `cleanouts-02-16x9`; the operator **chose to keep those files** (2026-08-16). **No 9:16 remakes exist**, so every asset group is missing the vertical video Google recommends for Shorts and “Excellent” ad strength.

## What was checked

| Check | Method | Result |
| --- | --- | --- |
| Live Ads asset groups / YouTube video assets | Google Ads API `asset_group_asset` + `asset` | **Not run** — no developer token / OAuth in this environment |
| File matrix vs 14 sources × 1:1 + 16:9 | Filesystem | 23 keepers; 5 operator-removed |
| Encode / duration / audio | ffprobe + `volumedetect` | All 23 pass PMax technical floors |
| Last-frame CTA | ffmpeg last frame, hashed | Native 1:1 / 16:9 Shopify wording; not “Call Today” |
| In-scene text on boxes | Sampled frames at ~2s / 8s / 14s | Noted on `downsizing-01-16x9` and `cleanouts-02-16x9`; possible on `cleanouts-01-1x1`. **Operator kept all three.** |
| PMax ratio trio (16:9, 1:1, 9:16) | Coverage table | **Fail** — zero 9:16 keepers |

## Coverage vs PMax (recommended: one of each orientation per asset group)

Google: [About video assets for Performance Max](https://support.google.com/google-ads/answer/14528532). Videos optional but recommended; ≥10s; up to 15 per orientation; 1080p preferred; at least one 9:16 of 10–60s for Shorts. Missing video → Google auto-generates or crops other ratios.

| Asset group (service) | 1:1 keepers | 16:9 keepers | 9:16 keepers | Notes |
| --- | --- | --- | --- | --- |
| jewelry | 2 | 2 | **0** | Strongest set. `jewelry-02-1x1` is ~17.88s (0.25s hitch trim). |
| estate-sales | 2 | 2 | **0** | Complete 1:1 + 16:9. |
| appraisals | 2 | 2 | **0** | Complete 1:1 + 16:9. |
| downsizing | 2 | 2 | **0** | Sampled `01-16x9` box labels look invented; **kept by operator 2026-08-16**. |
| listing-prep | 2 | 1 | **0** | `01-16x9` already removed. Remaining 16:9 is `02` only. |
| cleanouts | 2 | 1 | **0** | `01-16x9` already removed. Sampled `02-16x9` labels look illegible; **kept by operator 2026-08-16**. |
| liquidation | 1 | **0** | **0** | Only `liquidation-01-1x1` remains. No landscape video for this group. |

**23 files on disk.** If the operator uploaded from this tree after the five deletions, those five should not be in Ads. If they uploaded from an earlier download, pull these from the live asset groups:

- `cleanouts-01-16x9.mp4` (glitch)
- `liquidation-01-16x9.mp4`, `liquidation-02-16x9.mp4`, `liquidation-02-1x1.mp4` (gibberish labels)
- `listing-prep-01-16x9.mp4` (quality)

## Box-label notes (kept)

Sampled frames showed invented or illegible lettering on boxes. The operator reviewed this on 2026-08-16 and **did not want those files removed**. They stay in the keeper set and may remain in live asset groups:

1. **`downsizing-01-16x9.mp4`** — stacked banker’s boxes with invented printed words on the face labels (~8s).
2. **`cleanouts-02-16x9.mp4`** — white stickers with unreadable / non-letter marks on boxes (~2s and ~8s). Empty-room ending (~14s) is clean.
3. **`cleanouts-01-1x1.mp4`** — white rectangles on boxes that are blank or illegible.

Sampled frames that did **not** show fake box copy: remaining jewelry, estate-sales (book-sale interior), appraisals (jewelry close-up), `liquidation-01-1x1` (plain boxes / empty-room key handoff), `listing-prep-02-*` (cleaning / floor work), `downsizing-02-16x9` (packing with pre-printed blank label lines, no fake words in the sampled frame).

AI anatomy (hands, rings, fused fingers) appears in several keepers. That is Seedance texture, not a delete criterion.

## Technical probe (all 23 keepers)

Every remaining file:

- Duration 17.875–18.125s (≥10s PMax floor)
- Pixels exact: 960×960 or 1280×720
- H.264 **Main**, `yuv420p`, **no B-frames**, 24 fps
- AAC stereo 44.1 kHz, language `eng`, ~152–164 kb/s
- `+faststart` (`moov` in the first 128 KB)
- Mean VO level −28.1 to −23.1 dBFS; peaks −10.7 to −9.2 dBFS (audible, not silent)

CTA stills in `google-ads/cta/`: `cta-9x16.png` 720×1280, `cta-1x1.png` 960×960, `cta-16x9.png` 1280×720. Last-frame hashes cluster by ratio (same native card). Jewelry last frames differ by a few KB of encoder noise; wording is still the locked Shopify copy.

**720p vs Google’s 1080p recommendation:** Seedance 2.5 maxes at 720p. Uploads are HD, not Full HD. Google may still serve them; ad strength / YouTube quality is weaker than 1920×1080 / 1080×1080 / 1080×1920.

## CTA / branding

- End card is **Ready to Get Started?** + locked service list + **Get Your Free Consultation** + organizinglifeservices.com + PROFESSIONAL - RELIABLE - TRUSTED.
- Original 9:16 masters still end on **Call Today for an Offer**. Those masters were never remade into keepers. Do **not** upload the old 9:16 files to fill the vertical slot unless ffmpeg has replaced the last 3s with `cta-9x16.png` (`--with-vertical`).

## What this agent could not verify in Google Ads

Confirm in the UI (or add `GOOGLE_ADS_*` secrets and a read-only GAQL audit later):

1. Each service asset group has only the keepers still in `google-ads/{service}/`.
2. The five deleted files are absent.
3. After any further pulls, each group still has at least one video (liquidation currently has a single square clip).
4. Videos are eligible (YouTube processing complete, not limited).
5. Google has not auto-generated extra videos from images; if it has, review or remove them.
6. Final URLs / headlines still match the service landing pages.

## Recommended next actions (operator)

1. **Do not upload original 9:16 masters** until the last 3s are the new CTA. Then add one vertical per group so Google is less likely to crop 16:9 into Shorts.
2. Regeneration of already-removed 16:9s (liquidation, listing-prep-01, cleanouts-01) needs a Seedance retry **and** a prompt that boxes stay unlabeled / no printed text — or shoot real footage. This agent did not spend Seevio credits. Do not regenerate `downsizing-01-16x9` or `cleanouts-02-16x9` unless asked; those stay.
3. Wire Ads API read-only credentials if future audits should confirm the live account instead of local files only.
