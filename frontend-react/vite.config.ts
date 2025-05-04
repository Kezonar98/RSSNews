import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  envDir: '../',
  envPrefix: 'VITE_',
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    // optional: proxy API calls to backend to avoid CORS in development
    proxy: {
      '/news': {
        target: process.env.VITE_NEWS_API_URL,
        changeOrigin: true,
      },
      '/categories': {
        target: process.env.VITE_CATEGORIES_API_URL,
        changeOrigin: true,
      },
    },
  },
});
