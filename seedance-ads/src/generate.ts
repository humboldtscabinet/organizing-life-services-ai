import { SeedanceClient } from "./client.ts";
import type {
  GenerateAdOptions,
  GenerateAdResult,
  GenerateAllRatiosResult,
  SeedanceClientConfig,
} from "./types.ts";

let defaultClient: SeedanceClient | undefined;

/**
 * Shared client for high-level helpers. Future agents (Variant Factory,
 * Asset Manager) should prefer injecting their own SeedanceClient so
 * retries, output dirs, and model overrides stay isolated.
 */
export function getDefaultClient(config?: SeedanceClientConfig): SeedanceClient {
  if (config) {
    return new SeedanceClient(config);
  }
  defaultClient ??= new SeedanceClient();
  return defaultClient;
}

/** Generate a single-ratio Google Ads video. Framing is applied automatically. */
export async function generateSingleAd(
  options: GenerateAdOptions,
  client?: SeedanceClient,
): Promise<GenerateAdResult> {
  return (client ?? getDefaultClient()).generate(options);
}

/**
 * Generate the full Performance Max set (9:16, 1:1, 16:9).
 * Each ratio gets its own framing instruction.
 */
export async function generateFullAdSet(
  options: Omit<GenerateAdOptions, "aspectRatio">,
  client?: SeedanceClient,
  extras?: { parallel?: boolean },
): Promise<GenerateAllRatiosResult> {
  return (client ?? getDefaultClient()).generateAllRatios(options, extras);
}
