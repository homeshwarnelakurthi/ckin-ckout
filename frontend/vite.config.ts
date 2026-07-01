import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The API base is read at runtime from VITE_API_BASE (see .env.example).
// In dev we proxy /api to the backend so no CORS juggling is needed.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
