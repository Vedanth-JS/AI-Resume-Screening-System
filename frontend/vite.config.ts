import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    // ─── Chunk Splitting ────────────────────────────────────────────────
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          charts: ['recharts'],
          query: ['@tanstack/react-query'],
          motion: ['framer-motion'],
          ui: ['lucide-react'],
        },
      },
    },
    // ─── Compression (gzip + brotli at build time) ──────────────────────
    target: 'es2020',
    sourcemap: false,
    // ─── Chunk size warning limit ───────────────────────────────────────
    chunkSizeWarningLimit: 800,
  },
  server: {
    port: 8081,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
      },
    },
  },
  // ─── CSS optimization ─────────────────────────────────────────────────
  css: {
    devSourcemap: false,
  },
});
