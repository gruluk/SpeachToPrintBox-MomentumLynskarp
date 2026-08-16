import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/admin/',
  build: { outDir: '../server/static/admin-app', emptyOutDir: true },
  server: {
    port: 5174,
    proxy: {
      '/admin/api': 'http://localhost:8000',
      '/e': 'http://localhost:8000',
    },
  },
})
