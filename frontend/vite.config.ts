import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const API_TARGET = env.VITE_BACKEND_URL || 'http://localhost:8010';

  return {
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  build: {
    // Optimize bundle splitting
    rollupOptions: {
      output: {
        manualChunks: {
          // React core libraries
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          // Chart library (usually large)
          'vendor-charts': ['recharts'],
          // UI utilities
          'vendor-ui': ['lucide-react', 'clsx', 'tailwind-merge'],
          // State management
          'vendor-state': ['zustand'],
          // Network library
          'vendor-http': ['axios'],
        },
      },
    },
    // Increase chunk size warning limit (some chunks will be larger due to charts)
    chunkSizeWarningLimit: 1000,
    // Enable source maps for production debugging (optional, increases build size)
    sourcemap: false,
    // Minification
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.logs in production
        drop_debugger: true,
      },
    },
  },
  optimizeDeps: {
    // Pre-bundle these dependencies for faster dev server startup
    include: ['recharts', 'react', 'react-dom', 'react-router-dom', 'zustand', 'axios'],
  },
  }
})
