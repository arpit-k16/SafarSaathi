import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

// During `npm run dev`, /api/* is proxied to the local Python backend so the
// console uses a same-origin base URL exactly as it does in production.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: { '/api': { target: process.env.SAFARSAATHI_BACKEND || 'http://127.0.0.1:8000', changeOrigin: true } },
  },
  build: { outDir: 'dist', emptyOutDir: true, chunkSizeWarningLimit: 900 },
});
