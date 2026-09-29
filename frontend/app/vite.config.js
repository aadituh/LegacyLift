import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  // GitHub Pages hosts this repository below /LegacyLift/.
  base: process.env.GITHUB_PAGES === 'true' ? '/LegacyLift/' : '/',
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
