import { defineConfig, devices } from "@playwright/test";
import dotenv from "dotenv";
import path from "node:path";

dotenv.config({ path: path.resolve(__dirname, ".env.e2e") });

const FRONTEND_URL = process.env.E2E_FRONTEND_URL ?? "http://localhost:3000";
const ADMIN_URL = process.env.E2E_ADMIN_URL ?? "http://localhost:3800";
const CI = Boolean(process.env.CI);

export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  forbidOnly: CI,
  retries: CI ? 1 : 0,
  workers: CI ? 2 : undefined,
  reporter: [
    ["list"],
    ["html", { open: "never", outputFolder: "playwright-report" }],
  ],
  use: {
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "setup:user",
      testMatch: /tests\/setup\/user-auth\.setup\.ts/,
    },
    {
      name: "setup:admin",
      testMatch: /tests\/setup\/admin-auth\.setup\.ts/,
    },
    {
      name: "user-smoke",
      testMatch: /tests\/user\/.*\.spec\.ts/,
      dependencies: ["setup:user"],
      use: {
        ...devices["Desktop Chrome"],
        baseURL: FRONTEND_URL,
        storageState: "playwright/.auth/user.json",
      },
    },
    {
      name: "admin-smoke",
      testMatch: /tests\/admin\/.*\.spec\.ts/,
      dependencies: ["setup:admin"],
      use: {
        ...devices["Desktop Chrome"],
        baseURL: ADMIN_URL,
        storageState: "playwright/.auth/admin.json",
      },
    },
    {
      name: "cross-app",
      testMatch: /tests\/cross-app\/.*\.spec\.ts/,
      dependencies: ["setup:user", "setup:admin"],
      use: {
        ...devices["Desktop Chrome"],
        baseURL: ADMIN_URL,
        storageState: "playwright/.auth/admin.json",
      },
    },
  ],
});
