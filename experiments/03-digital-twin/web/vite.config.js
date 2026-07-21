import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { resolve } from 'node:path';

const coiHeaders = {
  'Cross-Origin-Opener-Policy': 'same-origin',
  'Cross-Origin-Embedder-Policy': 'require-corp',
};

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    headers: coiHeaders,
  },
  preview: {
    headers: coiHeaders,
  },
  build: {
    rollupOptions: {
      input: {
        main: resolve(import.meta.dirname, 'index.html'),
        'arm-lab': resolve(import.meta.dirname, 'arm-lab.html'),
        'generalization-lab': resolve(import.meta.dirname, 'generalization-lab.html'),
      },
      external: [/^https:\/\/cdn\.jsdelivr\.net\//],
    },
  },
  resolve: {
    alias: {
      '@': new URL('./src', import.meta.url).pathname,
    },
  },
});
