import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    // e2e/ holds @playwright/test specs (a different runner, different
    // `test()` signature) — excluded so vitest doesn't try to collect them.
    exclude: ["**/node_modules/**", "**/e2e/**"],
    coverage: {
      // Without an explicit include, v8 only reports on files a test
      // imported — which reads as high coverage of a very small app.
      // Name the real source tree so untested files count against us.
      include: ["app/**/*.{ts,tsx}", "components/**/*.tsx", "lib/**/*.ts"],
      exclude: ["**/__tests__/**"],
      // Text only: the default reporters also write a coverage/ HTML
      // bundle whose vendored JS then trips `npm run lint`.
      reporter: ["text"],
    },
  },
});
