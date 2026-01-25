import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory.
  const env = loadEnv(mode, process.cwd(), '')

  // IMPORTANT: This is only used for the dev server proxy
  // Production builds use environment variables directly (no proxy)
  // REQUIRED: VITE_API_URL must be set in .env file for development
  if (!env.VITE_API_URL) {
    console.warn('⚠️  VITE_API_URL is not set. Dev proxy will not work. Please set it in your .env file.')
  }
  const apiUrl = env.VITE_API_URL

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server: {
      host: true, // Expose to network
      port: 5173,
      // Development proxy - only used when running `npm run dev`
      // This allows development without CORS issues
      proxy: {
        '/api': {
          target: apiUrl,
          changeOrigin: true,
          secure: false,
          rewrite: (path) => path,
        },
      },
    },
  }
})