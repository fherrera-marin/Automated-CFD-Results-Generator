import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  // Relative base so the demo build works from any GitHub Pages project
  // path (https://<user>.github.io/<repo>/) without hardcoding the repo
  // name here.
  base: mode === 'demo' ? './' : '/',
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
}))
