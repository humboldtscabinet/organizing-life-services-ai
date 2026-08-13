# seedance-ads

TypeScript foundation for generating **Google Ads / Performance Max** video creatives with ByteDance **Seedance**.

Default provider is **[Seevio](https://seevio.ai)** (formerly seedance2.ai), which is where OLS already has a `sk_live_` API key. BytePlus ModelArk remains available via `SEEDANCE_PROVIDER=bytedance`.

Every generation automatically appends the correct framing instruction for `9:16`, `1:1`, or `16:9`. You only write the creative brief.

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

Create or rotate keys at [seevio.ai/dashboard/user/api-keys](https://seevio.ai/dashboard/user/api-keys). Docs: [seevio.ai/api-docs](https://seevio.ai/api-docs).

**Do not paste the key in chat.** For Cloud Agents, add `SEEDANCE_API_KEY` as a **Runtime Secret** at [cursor.com/dashboard/cloud-agents](https://cursor.com/dashboard/cloud-agents), then restart the agent.

Default model: `seedance-2-5`. Other Seevio IDs: `seedance-2-0`, `seedance-2-0-fast`, `seedance-2-0-mini`.

## Framing rules (applied automatically)

Do **not** paste these into `--prompt`. `buildPrompt()` appends them.

**9:16 (Vertical)**  
Frame vertically for 9:16 mobile. Keep the subject and any action centered in the middle third. Prefer tighter shots. Leave room above and below for the end card. End on the uploaded CTA card filling the full 9:16 frame for the final 3 seconds.

**1:1 (Square)**  
Frame for a 1:1 square. Center the composition. Use medium shots with balanced headroom. End on the uploaded CTA card filling the full 1:1 frame for the final 3 seconds.

**16:9 (Horizontal)**  
Frame cinematically for 16:9 widescreen. Prefer wider establishing shots. Place the subject slightly off-center with clean negative space. End on the uploaded CTA card filling the full 16:9 frame for the final 3 seconds.

Confirm locally without spending credits:

```bash
npx tsx scripts/generate-ad.ts --prompt "Warm kitchen, organizer folding linens." --all --dry-run
```

## Usage

### Single ratio

```bash
npx tsx scripts/generate-ad.ts \
  --prompt "Estate-sale specialist walking a bright Tampa home, calm and trustworthy." \
  --ratio 9:16 \
  --duration 8
```

### Full Performance Max set

```bash
npx tsx scripts/generate-ad.ts \
  --prompt "Estate-sale specialist walking a bright Tampa home, calm and trustworthy." \
  --all \
  --duration 8
```

### Image-to-video

Seevio requires **public HTTP(S) URLs** (not local files). Image-to-video inherits the source image ratio; framing for the requested ratio is still appended.

```bash
npx tsx scripts/generate-ad.ts \
  --prompt "Gentle camera push-in, natural motion, premium service feel." \
  --ratio 9:16 \
  --image https://example.com/first-frame-9x16.png \
  --last-frame https://example.com/cta-9x16.png
```

## Project structure

```
seedance-ads/
├── src/
│   ├── seevio.ts             Seevio HTTP client (default)
│   ├── client.ts             SeedanceClient + prepareGeneration()
│   ├── framing.ts            Canonical Google Ads framing rules
│   └── ...
└── scripts/generate-ad.ts
```

## Scripts

| Command | Purpose |
| --- | --- |
| `npm test` | Framing + Seevio payload tests (no API key) |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run generate -- --prompt "..." --ratio 9:16` | Live generation |

Videos download to `./output/`. Seevio result URLs expire; keep the local files.
