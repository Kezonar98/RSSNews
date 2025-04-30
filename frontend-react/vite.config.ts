import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  // Use root .env directory
  envDir: '../',
  // Only expose variables prefixed with VITE_
  envPrefix: 'VITE_',
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
  },
});