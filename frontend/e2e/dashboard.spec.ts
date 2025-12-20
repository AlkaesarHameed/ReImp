/**
 * Dashboard E2E Tests.
 * Source: Phase 6 Implementation Document
 *
 * Tests for dashboard functionality and navigation.
 */
import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Setup: Login first (using test fixtures in production)
    await page.goto('/auth/login');
    await page.getByLabel(/email/i).fill('admin@example.com');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /sign in/i }).click();
    await page.waitForURL(/.*dashboard/);
  });

  test('should display dashboard with KPI cards', async ({ page }) => {
    // Check for dashboard elements
    await expect(page.getByRole('heading', { name: /claims dashboard/i })).toBeVisible();

    // Check KPI cards are present
    await expect(page.getByText(/claims today/i)).toBeVisible();
    await expect(page.getByText(/approved/i)).toBeVisible();
    await expect(page.getByText(/pending review/i)).toBeVisible();
  });

  test('should display charts', async ({ page }) => {
    // Check for chart containers
    await expect(page.getByText(/claims status distribution/i)).toBeVisible();
    await expect(page.getByText(/claims trend/i)).toBeVisible();
  });

  test('should have working quick action buttons', async ({ page }) => {
    // Click New Claim button
    await page.getByRole('button', { name: /new claim/i }).click();
    await expect(page).toHaveURL(/.*claims\/new/);

    // Go back to dashboard
    await page.goto('/dashboard');

    // Click Reports button
    await page.getByRole('button', { name: /reports/i }).click();
    await expect(page).toHaveURL(/.*reports/);
  });

  test('should display activity feed', async ({ page }) => {
    // Check for recent activity section
    await expect(page.getByText(/recent activity/i)).toBeVisible();

    // Check for activity items
    const activityItems = page.locator('.activity-item');
    await expect(activityItems.first()).toBeVisible();
  });

  test('should display system status indicators', async ({ page }) => {
    // Check for system status section
    await expect(page.getByText(/api server/i)).toBeVisible();
    await expect(page.getByText(/database/i)).toBeVisible();
    await expect(page.getByText(/websocket/i)).toBeVisible();
  });
});
