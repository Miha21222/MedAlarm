import { copyFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig, loadEnv, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

function spa404Fallback(): Plugin {
  let outDir = "dist";
  let root = process.cwd();
  return {
    name: "spa-404-fallback",
    apply: "build",
    configResolved(config) {
      outDir = config.build.outDir;
      root = config.root;
    },
    closeBundle() {
      const index = resolve(root, outDir, "index.html");
      if (existsSync(index)) copyFileSync(index, resolve(root, outDir, "404.html"));
    },
  };
}

export default defineConfig(({ mode }) => {
  const envDir = resolve(process.cwd(), "..");
  const env = loadEnv(mode, envDir, "");
  return {
    envDir,
    base: env.VITE_BASE_PATH || "/",
    plugins: [react(), spa404Fallback()],
    server: { host: "0.0.0.0", port: Number(process.env.PORT) || 5173 },
  };
});
