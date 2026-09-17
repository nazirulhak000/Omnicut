import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import basicSsl from '@vitejs/plugin-basic-ssl'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // scripts/auth.py's api_key_gate requires X-API-Key on every request once
  // OMNICUT_API_KEY is set. Injecting it here, server-side in the dev proxy,
  // authenticates both JS requests and native media tags without exposing the
  // secret to the browser bundle.
  const env = loadEnv(mode, '..', '')
  const apiKey = env.OMNICUT_API_KEY
  return {
  envDir: '..',
  plugins: [
    react(),
    tailwindcss(),
    // Self-signed HTTPS for dev server -- MobileFilmingPage.jsx's
    // navigator.mediaDevices.getUserMedia() is undefined on a plain http://
    // origin on a phone (browsers only expose it in a "secure context":
    // https://, or localhost -- a LAN IP over http never qualifies).
    basicSsl(),
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
