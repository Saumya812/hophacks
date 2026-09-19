import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite config for the FindMyPal React frontend.
// Proxy /api → FastAPI during local development so the browser stays same-origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
