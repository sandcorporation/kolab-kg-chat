import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// 개발 편의: /chat·/openapi.json 등 백엔드 경로는 로컬 nginx(:80)로 프록시.
// 운영 빌드는 nginx 멀티스테이지가 dist를 서빙하므로 이 프록시는 dev 전용.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/chat": { target: "http://localhost:80", changeOrigin: true },
      "/openapi.json": { target: "http://localhost:80", changeOrigin: true },
      "/recommend": { target: "http://localhost:80", changeOrigin: true },
      "/health": { target: "http://localhost:80", changeOrigin: true },
    },
  },
});
