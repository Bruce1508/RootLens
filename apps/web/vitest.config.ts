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
  },
});
