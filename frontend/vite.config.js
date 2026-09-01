import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss()
  ],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
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
})
