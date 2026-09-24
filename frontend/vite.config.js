import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import basicSsl from '@vitejs/plugin-basic-ssl'
import fs from 'node:fs'
import path from 'node:path'

function localFontAssets() {
  const routePrefix = '/api/media/02_Assets/Fonts/'
  const fontsRoot = path.resolve(process.cwd(), '..', '02_Assets', 'Fonts')
  return {
    name: 'omnicut-local-font-assets',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const pathname = new URL(req.url || '/', 'http://127.0.0.1').pathname
        if (!pathname.startsWith(routePrefix)) return next()
        const filename = decodeURIComponent(pathname.slice(routePrefix.length))
        if (!filename || path.basename(filename) !== filename || !/\.(ttf|otf)$/i.test(filename)) {
          res.statusCode = 400
          res.end('Invalid font path')
          return
        }
        const target = path.resolve(fontsRoot, filename)
        if (path.dirname(target) !== fontsRoot || !fs.existsSync(target)) {
          res.statusCode = 404
          res.end('Font not found')
          return
        }
        res.setHeader('Content-Type', filename.toLowerCase().endsWith('.otf') ? 'font/otf' : 'font/ttf')
        res.setHeader('Cache-Control', 'public, max-age=3600')
        fs.createReadStream(target).pipe(res)
      })
    },
  }
}

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
    localFontAssets(),
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
    // The live Preview-vs-Render parity fixture serves a deterministic source
    // and real overlay assets through Vite's /@fs route. Keep the allow-list
    // scoped to this project root; production media still uses /api/media.
    fs: {
      allow: [path.resolve(process.cwd(), '..')],
    },
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
