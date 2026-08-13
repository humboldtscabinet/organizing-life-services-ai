/**
 * Small structured logger. Swap this later for pino/winston without
 * touching generation code — Asset Manager and QA agents can hook here.
 */
const PREFIX = "seedance-ads";

function stamp(): string {
  return new Date().toISOString();
}

export const logger = {
  info(message: string, extra?: Record<string, unknown>): void {
    if (extra) {
      console.log(`[${stamp()}] [${PREFIX}] ${message}`, extra);
    } else {
      console.log(`[${stamp()}] [${PREFIX}] ${message}`);
    }
  },
  warn(message: string, extra?: Record<string, unknown>): void {
    if (extra) {
      console.warn(`[${stamp()}] [${PREFIX}] ${message}`, extra);
    } else {
      console.warn(`[${stamp()}] [${PREFIX}] ${message}`);
    }
  },
  error(message: string, extra?: Record<string, unknown>): void {
    if (extra) {
      console.error(`[${stamp()}] [${PREFIX}] ${message}`, extra);
    } else {
      console.error(`[${stamp()}] [${PREFIX}] ${message}`);
    }
  },
};
