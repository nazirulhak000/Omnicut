import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // scripts/auth.py's api_key_gate requires X-API-Key on every request once
  // OMNICUT_API_KEY is set. api.js's axios interceptor covers every JS-driven
  // call, but a native <video>/<audio>/<img src> load -- used all over the
  // app for /api/media/... streaming and thumbnails -- cannot attach a
  // custom header at all, so those 401 the moment a key is configured.
  // Injecting the header here, server-side in the dev proxy that every
  // request (JS-driven or a bare browser tag) already passes through,
  // fixes every such call site in one place instead of needing each of the
  // ~10 components that build a raw /api/media/ URL to remember a query
  // param. Covers mobile-LAN preview too, since that also goes through this
  // same dev server rather than hitting :8000 directly.
  const env = loadEnv(mode, process.cwd(), '')
  const apiKey = env.VITE_API_KEY
  return {
  plugins: [
    react(),
    tailwindcss()
  ],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        timeout: 600000,
        proxyTimeout: 600000,
        configure: (proxy) => {
          if (!apiKey) return
          proxy.on('proxyReq', (proxyReq) => {
            proxyReq.setHeader('X-API-Key', apiKey)
          })
        },
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('react') || id.includes('react-dom')) {
              return 'vendor-react';
            }
            if (id.includes('lucide-react')) {
              return 'vendor-icons';
            }
            if (id.includes('@dnd-kit')) {
              return 'vendor-dnd';
            }
            if (id.includes('axios') || id.includes('clsx') || id.includes('tailwind-merge') || id.includes('qrcode.react')) {
              return 'vendor-utils';
            }
            return 'vendor-misc';
          }
        }
      }
    },
    chunkSizeWarningLimit: 600
  }
  }
})
