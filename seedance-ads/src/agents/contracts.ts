/**
 * Contracts for the multi-agent layer this project will grow into.
 *
 * Nothing here is wired yet. New agents should implement these interfaces
 * and compose with SeedanceClient / generateSingleAd / generateFullAdSet
 * instead of calling @ai-sdk/bytedance directly (that would skip framing).
 */

import type {
  AspectRatio,
  GenerateAdOptions,
  GenerateAdResult,
} from "../types.ts";

/** Rewrites a creative brief before framing is appended. */
export interface PromptEngineer {
  refine(
    prompt: string,
    context: { aspectRatio?: AspectRatio; brandNotes?: string },
  ): Promise<string> | string;
}

export type QaVerdict = {
  pass: boolean;
  notes: string[];
  aspectRatio: AspectRatio;
};

/** Reviews a generated clip (duration, CTA hold, framing compliance). */
export interface QaAgent {
  review(result: GenerateAdResult): Promise<QaVerdict> | QaVerdict;
}

/** Spins a base brief into prompt / scene variants. */
export interface VariantFactory {
  variants(
    base: GenerateAdOptions,
    count: number,
  ): Promise<GenerateAdOptions[]> | GenerateAdOptions[];
}

export type StoredAsset = {
  id: string;
  aspectRatio: AspectRatio;
  path?: string;
  url?: string;
};

/** Persists finished creatives (local disk, Drive, GCS, Ads asset library). */
export interface AssetManager {
  store(result: GenerateAdResult): Promise<StoredAsset> | StoredAsset;
}
