import { defineConfig } from 'vite'

// Vite config with a simple proxy for /api and websocket upgrades to the
// local backend on port 8000. This lets the frontend use relative URLs.
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
      }
    }
  }
})
