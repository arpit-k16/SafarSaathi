import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  cacheDir: process.env.SAFARSAATHI_VITE_CACHE || 'node_modules/.vite',
  build: {
    outDir: process.env.SAFARSAATHI_VITE_OUT || 'dist',
    emptyOutDir: false,
  },
})
