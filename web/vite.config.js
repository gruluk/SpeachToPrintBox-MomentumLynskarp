import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Relative base so the SPA works at /booth/N and /e/{slug}/booth/N
  base: './',
  build: { outDir: '../server/static/web', emptyOutDir: true },
  server: {
    proxy: {
      '/e': 'http://localhost:8000',
      '/validate': 'http://localhost:8000',
      '/generate': 'http://localhost:8000',
      '/publish': 'http://localhost:8000',
      '/face': 'http://localhost:8000',
      '/users': 'http://localhost:8000',
      '/demo-choice': 'http://localhost:8000',
      '/booth-config': 'http://localhost:8000',
      '/presentations': 'http://localhost:8000',
      '/print-label': 'http://localhost:8000',
      '/admin': 'http://localhost:8000',
    }
  }
})
