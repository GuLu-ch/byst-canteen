import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        // vue / vue-router 固定打进同一个 vendor chunk：
        // 否则懒加载页面 chunk 可能各自拿到一份 vue-router，
        // 两边的 provide/inject symbol 对不上，useRoute()/useRouter() 会返回 undefined。
        // rolldown（vite 8）只接受函数形式
        manualChunks(id) {
          const file = id.replace(/\\/g, '/')
          if (file.includes('node_modules/vue-router') || file.includes('node_modules/vue/') || file.includes('node_modules/@vue/')) {
            return 'vue-vendor'
          }
          return undefined
        },
      },
    },
  },
})
