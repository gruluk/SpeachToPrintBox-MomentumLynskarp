import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/booth/',
  build: { outDir: '../server/static/web', emptyOutDir: true },
  server: {
    proxy: {
      '/validate': 'http://localhost:8000',
      '/generate': 'http://localhost:8000',
      '/publish': 'http://localhost:8000',
      '/face': 'http://localhost:8000',
      '/registered-users': 'http://localhost:8000',
      '/demo-choice': 'http://localhost:8000',
      '/booth-config': 'http://localhost:8000',
    }
  }
})
