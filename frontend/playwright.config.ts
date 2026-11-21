import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e', testMatch: '**/*.pw.ts', fullyParallel: true, workers: 2, timeout: 60_000, forbidOnly: Boolean(process.env.CI), retries: 0, reporter: 'list',
  use: { baseURL: 'http://127.0.0.1:4173', trace: 'retain-on-failure', ...devices['Desktop Chrome'] },
});
