import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from "path"

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) {
            return
          }

          if (id.includes('react-pdf') || id.includes('pdfjs-dist')) {
            return 'pdf'
          }

          if (id.includes('katex') || id.includes('dompurify')) {
            return 'reader'
          }

          if (id.includes('i18next') || id.includes('react-i18next')) {
            return 'i18n'
          }

          if (id.includes('@radix-ui')) {
            return 'radix'
          }

          if (id.includes('framer-motion')) {
            return 'motion'
          }

          if (id.includes('lucide-react')) {
            return 'icons'
          }

          return 'vendor'
        },
      },
    },
  },
})
