import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // 前端路径与后端路由完全一致（/health、/ready、/api/v1/*），纯转发即可
      "/api": { target: "http://127.0.0.1:8787" },
      "/health": { target: "http://127.0.0.1:8787" },
      "/ready": { target: "http://127.0.0.1:8787" },
    },
  },
});
