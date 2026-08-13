# seedance-ads

TypeScript foundation for generating **Google Ads / Performance Max** video creatives with ByteDance **Seedance**, via BytePlus ModelArk and the official [`@ai-sdk/bytedance`](https://ai-sdk.dev/providers/ai-sdk-providers/bytedance) provider.

Every generation automatically appends the correct framing instruction for `9:16`, `1:1`, or `16:9`. You only write the creative brief.

This package is designed to grow into a multi-agent pipeline (Prompt Engineer → SeedanceClient → QA → Variant Factory → Asset Manager). Agent contracts live in `src/agents/contracts.ts`. Until those agents exist, all video calls must go through `SeedanceClient` so framing cannot be skipped.

## Setup

```bash
cd seedance-ads
npm install
cp .env.example .env
```

Edit `.env`:

```bash
ARK_API_KEY=your-byteplus-modelark-key
# optional
SEEDANCE_MODEL=dreamina-seedance-2-0-260128
```

Create an API key in the [BytePlus ModelArk console](https://console.byteplus.com/ark/apiKey).

Default model: `dreamina-seedance-2-0-260128` (Seedance 2.0). Fast variant: `dreamina-seedance-2-0-fast-260128`.

## Framing rules (applied automatically)

Do **not** paste these into `--prompt`. `buildPrompt()` appends them.

**9:16 (Vertical)**  
Frame vertically for 9:16 mobile. Keep the subject and any action centered in the middle third. Prefer tighter shots. Leave room above and below for the end card. End on the uploaded CTA card filling the full 9:16 frame for the final 3 seconds.

**1:1 (Square)**  
Frame for a 1:1 square. Center the composition. Use medium shots with balanced headroom. End on the uploaded CTA card filling the full 1:1 frame for the final 3 seconds.

**16:9 (Horizontal)**  
Frame cinematically for 16:9 widescreen. Prefer wider establishing shots. Place the subject slightly off-center with clean negative space. End on the uploaded CTA card filling the full 16:9 frame for the final 3 seconds.

Confirm locally without spending API credits:

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

Equivalent:

```bash
npm run generate -- --prompt "Estate-sale specialist walking a bright Tampa home." --ratio 1:1
```

### Full Performance Max set (all three ratios)

```bash
npx tsx scripts/generate-ad.ts \
  --prompt "Estate-sale specialist walking a bright Tampa home, calm and trustworthy." \
  --all \
  --duration 8
```

### Image-to-video

Seedance 2.x inherits aspect ratio from the first-frame image. Framing for the requested ratio is still appended; provide a source (and CTA card) already in that ratio.

```bash
npx tsx scripts/generate-ad.ts \
  --prompt "Gentle camera push-in, natural motion, premium service feel." \
  --ratio 9:16 \
  --image ./assets/first-frame-9x16.png \
  --last-frame ./assets/cta-9x16.png
```

### Programmatic API

```ts
import { generateFullAdSet, generateSingleAd } from "./src/index.ts";

const one = await generateSingleAd({
  prompt: "Organizer opening a closet, warm daylight, confident smile.",
  aspectRatio: "9:16",
  duration: 8,
});

const set = await generateFullAdSet({
  prompt: "Organizer opening a closet, warm daylight, confident smile.",
  duration: 8,
});
```

`SeedanceClient.generateAllRatios()` is the same full-set path used by `--all`.

## Project structure

```
seedance-ads/
├── package.json
├── tsconfig.json
├── .env.example
├── src/
│   ├── index.ts              Public exports
│   ├── types.ts              AspectRatio, GenerateAdOptions, GenerateAdResult
│   ├── framing.ts            Canonical rules + buildPrompt()
│   ├── client.ts             SeedanceClient + prepareGeneration()
│   ├── generate.ts           generateSingleAd / generateFullAdSet
│   ├── logger.ts
│   ├── agents/contracts.ts   Future Prompt Engineer, QA, Variant Factory, Asset Manager
│   ├── framing.test.ts
│   └── prepare.test.ts       Asserts framing on every prepareGeneration() path
└── scripts/
    └── generate-ad.ts        CLI
```

## Scripts

| Command | Purpose |
| --- | --- |
| `npm install` | Install dependencies |
| `npm test` | Framing + pipeline unit tests (no API key) |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run generate -- --prompt "..." --ratio 9:16` | Live generation |

Outputs download to `./output/` as MP4. ModelArk URLs expire; keep the local files.

## Extending with agents

Implement the interfaces in `src/agents/contracts.ts` and wrap `generateSingleAd` / `generateFullAdSet`. Never call `experimental_generateVideo` from a new agent — that bypasses framing.
