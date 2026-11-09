import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  expect: { timeout: 15000 },
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:3011",
    channel: "chrome",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "node scripts/test-api.mjs",
      url: "http://127.0.0.1:8011/health",
      reuseExistingServer: process.env.PW_REUSE_SERVERS === "1",
      timeout: 60000,
    },
    {
      command: "npm run start -- --hostname 127.0.0.1 --port 3011",
      url: "http://127.0.0.1:3011/sign-in",
      reuseExistingServer: process.env.PW_REUSE_SERVERS === "1",
      timeout: 60000,
    },
  ],
});
