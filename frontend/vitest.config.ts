import path from "path"
import { defineConfig } from "vitest/config"
import react from "@vitejs/plugin-react"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
    css: false,
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      include: [
        "src/i18n.ts",
        "src/i18n/**/*.{ts,tsx}",
        "src/components/LanguageSelector.tsx",
        "src/layout.tsx",
        "src/components/app-sidebar.tsx",
      ],
    },
  },
})
