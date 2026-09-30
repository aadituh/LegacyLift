import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  // GitHub Pages hosts this repository below /LegacyLift/.
  base: process.env.GITHUB_PAGES === 'true' ? '/LegacyLift/' : '/',
  server: {
    proxy: {
      // Keep frontend and FastAPI in sync during local development.
      '/api': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
  preview: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
})
