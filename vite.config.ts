import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    host: '0.0.0.0',
    proxy: {
      '/sound': {
        target: 'https://www.missevan.com',  // 目标 API 地址
        changeOrigin: true,  // 允许代理跨域
        // rewrite: (path) => path.replace(/^\/sound/, ''),  // 移除 /sound 前缀
        rewrite: (path) => path,  // 移除 /sound 前缀
      },
    },
  },
})
