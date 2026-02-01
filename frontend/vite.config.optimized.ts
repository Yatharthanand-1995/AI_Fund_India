import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    // Enable code splitting
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor chunks
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'chart-vendor': ['recharts'],
          'utils-vendor': ['axios', 'zustand', 'clsx', 'tailwind-merge'],

          // Feature chunks
          'charts': [
            './src/components/charts/StockPriceChart',
            './src/components/charts/AgentScoresRadar',
            './src/components/charts/AgentScoresBar',
            './src/components/charts/MarketRegimeTimeline',
            './src/components/charts/RecommendationPie',
            './src/components/charts/CompositeScoreTrend',
            './src/components/charts/PortfolioPerformance',
            './src/components/charts/SectorHeatmap',
          ],
        },
      },
    },

    // Optimize chunk size
    chunkSizeWarningLimit: 1000,

    // Source maps for production debugging (optional)
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

  // Development optimizations
  server: {
    port: 3000,
    // Enable HMR
    hmr: true,
  },

  // Performance hints
  optimizeDeps: {
    include: ['react', 'react-dom', 'react-router-dom', 'recharts', 'axios', 'zustand'],
  },
});
