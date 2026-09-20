import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxy API so a single public tunnel can reach the app (same-origin).
const apiProxy = {
  target: 'http://127.0.0.1:8000',
  changeOrigin: true,
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    // Cloudflare quick tunnels send Host: *.trycloudflare.com
    allowedHosts: true,
    proxy: {
      '/api': {
        ...apiProxy,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/persons': apiProxy,
      '/health': apiProxy,
      '/search': apiProxy,
      '/lookup': apiProxy,
      '/faces': apiProxy,
      '/analytics': apiProxy,
      '/live': apiProxy,
      '/audio': apiProxy,
      '/alerts': apiProxy,
      '/memory': apiProxy,
      '/geo': apiProxy,
      '/docs': apiProxy,
      '/openapi.json': apiProxy,
      '/redoc': apiProxy,
    },
  },
})
