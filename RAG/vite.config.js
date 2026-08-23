import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  plugins: [react()],
  server: {
    proxy: {
      // forward API calls to the FastAPI backend (server_deploy/app.py) during dev
      '/api': 'http://127.0.0.1:8000',
    },
  },
  // production build is served by FastAPI under /static, dev server keeps root
  base: command === 'build' ? '/static/' : '/',
  build: {
    // build straight into the backend's static dir so one FastAPI app serves both
    outDir: '../server_deploy/static',
    emptyOutDir: true,
  },
}))
