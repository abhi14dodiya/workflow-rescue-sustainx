import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '/assets/',
  build: {
    // This is the application's generated static directory, not the source tree.
    outDir: '../web', emptyOutDir: true, assetsDir: 'bundle', assetsInlineLimit: 0,
    rollupOptions: { output: { manualChunks: { 'three-scene': ['three'] } } },
    chunkSizeWarningLimit: 650,
  },
  server: { proxy: { '/api': 'http://127.0.0.1:8080', '/healthz': 'http://127.0.0.1:8080' } },
});
