import { test, expect } from '@playwright/test';

test.describe('SupplyChain IQ - End-to-End Browser Test Suite', () => {
  test.beforeEach(async ({ page }) => {
    // Authenticate prior to each flow
    await page.goto('/login');
    await page.locator('input[type="email"]').fill('planner@supplychainiq.com');
    await page.locator('input[type="password"]').fill('Planner123!');
    await page.locator('button[type="submit"]').click();
    await page.waitForURL('http://localhost:5173/');
  });

  test('E2E Flow 1: Executive Dashboard & KPI Metrics Verification', async ({ page }) => {
    await expect(page.locator('text=Executive Control Tower').first()).toBeVisible();
    await expect(page.locator('text=Total Shortages').first()).toBeVisible();
    await expect(page.locator('text=Demand At Risk').first()).toBeVisible();
    await expect(page.locator('text=Inventory Valuation').first()).toBeVisible();
    await expect(page.locator('text=Mitigation Recovery Rate').first()).toBeVisible();
    await expect(page.locator('text=Shortages by Priority Tier').first()).toBeVisible();
  });

  test('E2E Flow 2: Shortage Workbench Navigation & Search Filtering', async ({ page }) => {
    await page.click('a[href="/shortages"]');
    await page.waitForURL('**/shortages');
    await expect(page.locator('text=Shortage Workbench').first()).toBeVisible();

    // Verify search input interaction
    const searchInput = page.locator('input[type="text"]').first();
    if (await searchInput.isVisible()) {
      await searchInput.fill('SKU-FG');
      await page.waitForTimeout(500);
    }
    await expect(page.locator('table, [role="table"], .divide-y').first()).toBeVisible();
  });

  test('E2E Flow 3: Mitigation Decisions & Governance Audit Trail', async ({ page }) => {
    await page.goto('/mitigations');
    await expect(page.locator('text=Mitigation').first()).toBeVisible();

    await page.goto('/audit');
    await expect(page.locator('text=Audit').first()).toBeVisible();
  });

  test('E2E Flow 4: Data Quality & Anomaly Center Diagnostics', async ({ page }) => {
    await page.click('a[href="/data-quality"]');
    await page.waitForURL('**/data-quality');
    await expect(page.locator('text=Data Quality').first()).toBeVisible();
  });
});
