import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // O Tailwind já está sendo carregado via postcss.config.js, não precisa aqui
  ],
  server: {
    proxy: {
      // Redireciona chamadas da API para o Python
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        secure: false,
      },
      // Redireciona imagens estáticas para o Python
      '/static': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        secure: false,
      }
    }
  }
})