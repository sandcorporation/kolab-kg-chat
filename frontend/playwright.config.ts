import { defineConfig } from "@playwright/test";

// 전제: 스택이 AGENT_FAKE=1로 떠 있어야 결정적으로 통과한다.
//   AGENT_FAKE=1 docker compose up -d db source-db api nginx
//   docker compose run --rm api python seed_demo.py
//   npm run e2e
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:80",
    trace: "on-first-retry",
  },
});
