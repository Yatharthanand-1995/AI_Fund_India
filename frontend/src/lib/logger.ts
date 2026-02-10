/**
 * Logger utility - conditionally logs only in development mode
 * In production builds, terser strips console.* calls via drop_console: true
 * This logger also works at runtime for any non-terser build paths.
 */

const isDev = import.meta.env.DEV;

export const logger = {
  log: (...args: unknown[]) => { if (isDev) console.log(...args); },
  error: (...args: unknown[]) => { if (isDev) console.error(...args); },
  warn: (...args: unknown[]) => { if (isDev) console.warn(...args); },
  debug: (...args: unknown[]) => { if (isDev) console.debug(...args); },
};
