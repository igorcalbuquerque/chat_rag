import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// During local `vite dev`, proxy /api to the backend so the frontend code can
// always call same-origin "/api/...". In production Nginx does the same.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
