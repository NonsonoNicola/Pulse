import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The frontend talks to the onboard API through /api. Keeping every API call
// under one prefix means SPA routes such as /crew or /ground never collide with
// backend paths, so a page refresh or a deep link always serves index.html.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: path => path.replace(/^\/api/, ''),
      },
    },
  },
});
