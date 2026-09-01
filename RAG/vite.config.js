import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The dev backend listens on 8010 (see .claude/launch.json); production runs on
// 8000 behind nginx. Override with VITE_API_PROXY when it lives somewhere else.
const API_PROXY = process.env.VITE_API_PROXY || 'http://127.0.0.1:8010'

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  plugins: [react()],
  server: {
    proxy: {
      // forward API calls to the FastAPI backend (server_deploy/app.py) during dev
      '/api': API_PROXY,
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
