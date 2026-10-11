/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // No Docker sobre Windows o volume nao avisa mudancas de arquivo; sem polling o HMR nao dispara.
  server: { watch: { usePolling: true } },
  test: { environment: 'jsdom' },
})
