/**
 * Reports E2E Tests.
 * Source: Phase 6 Implementation Document
 *
 * Tests for reports dashboard and report generation.
 */
import { test, expect } from '@playwright/test';

test.describe('Reports', () => {
  test.beforeEach(async ({ page }) => {
    // Setup: Login first
    await page.goto('/auth/login');
    await page.getByLabel(/email/i).fill('admin@example.com');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /sign in/i }).click();
    await page.waitForURL(/.*dashboard/);
  });

  test('should display reports dashboard', async ({ page }) => {
    await page.goto('/reports');

    // Check for reports dashboard elements
    await expect(page.getByRole('heading', { name: /reports & analytics/i })).toBeVisible();
  });

  test('should display quick stats', async ({ page }) => {
    await page.goto('/reports');

    // Check for stat cards
    await expect(page.getByText(/total claims/i)).toBeVisible();
    await expect(page.getByText(/approval rate/i)).toBeVisible();
  });

  test('should display available report cards', async ({ page }) => {
    await page.goto('/reports');

    // Check for report type cards
    await expect(page.getByText(/claims status report/i)).toBeVisible();
    await expect(page.getByText(/financial summary/i)).toBeVisible();
  });

  test('should navigate to claims report', async ({ page }) => {
    await page.goto('/reports');

    // Click on claims report card
    await page.getByText(/claims status report/i).click();

    // Should navigate to claims report page
    await expect(page).toHaveURL(/.*reports\/claims/);
    await expect(page.getByText(/claims status report/i)).toBeVisible();
  });

  test('should navigate to financial report', async ({ page }) => {
    await page.goto('/reports');

    // Click on financial report card
    await page.getByText(/financial summary report/i).click();

    // Should navigate to financial report page
    await expect(page).toHaveURL(/.*reports\/financial/);
  });

  test('should display date filter options', async ({ page }) => {
    await page.goto('/reports');

    // Check for date filters
    await expect(page.getByText(/report period/i)).toBeVisible();
    await expect(page.getByText(/start date/i)).toBeVisible();
    await expect(page.getByText(/end date/i)).toBeVisible();
  });

  test('should display charts on reports dashboard', async ({ page }) => {
    await page.goto('/reports');

    // Check for chart sections
    await expect(page.getByText(/claims volume/i)).toBeVisible();
    await expect(page.getByText(/financial overview/i)).toBeVisible();
  });

  test('claims report should display status breakdown', async ({ page }) => {
    await page.goto('/reports/claims');

    // Check for status breakdown section
    await expect(page.getByText(/claims by status/i)).toBeVisible();
    await expect(page.getByText(/claims trend/i)).toBeVisible();
  });

  test('financial report should display payer analysis', async ({ page }) => {
    await page.goto('/reports/financial');

    // Check for financial sections
    await expect(page.getByText(/payer analysis/i)).toBeVisible();
    await expect(page.getByText(/accounts receivable aging/i)).toBeVisible();
  });
});
