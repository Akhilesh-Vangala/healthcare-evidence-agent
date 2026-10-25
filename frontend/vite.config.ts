import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the console talks to `hea-serve` on :8000; in production Vercel rewrites /api to the API project.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
});
