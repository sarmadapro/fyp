import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteStaticCopy } from 'vite-plugin-static-copy'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    viteStaticCopy({
      targets: [
        {
          // Silero VAD ONNX models
          src: 'node_modules/@ricky0123/vad-web/dist/*.onnx',
          dest: './',
        },
        {
          // VAD worklet bundle
          src: 'node_modules/@ricky0123/vad-web/dist/vad.worklet.bundle.min.js',
          dest: './',
        },
        {
          // ONNX Runtime — WASM binaries + MJS loaders (both needed at runtime)
          src: 'node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded*',
          dest: './',
        },
      ],
    }),
  ],
  optimizeDeps: {
    exclude: ['@ricky0123/vad-web', 'onnxruntime-web'],
  },
  worker: {
    format: 'es',
  },
})
