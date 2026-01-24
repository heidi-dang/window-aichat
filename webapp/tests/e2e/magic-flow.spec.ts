import { test, expect } from '@playwright/test';

test.describe('EvolveAI Magic Feature User Flow', () => {
  test('new user discovers and uses EvolveAI predictive evolution', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('.sidebar-area')).toBeVisible({ timeout: 10_000 });

    const evolveButton = page.locator('button:has-text("🧬 EvolveAI")');
    await expect(evolveButton).toBeVisible();
    await evolveButton.click();
    
    await expect(page.locator('.evolve-modal')).toBeVisible({ timeout: 10_000 });
    
    await expect(
      page.getByRole('heading', { name: /EvolveAI - Predictive Code Evolution/ }).first()
    ).toBeVisible();
    await expect(
      page.locator('text=AI-powered insights to proactively improve your codebase')
    ).toBeVisible();
    
    const refreshButton = page.locator('button:has-text("Refresh Analysis")');
    await expect(refreshButton).toBeVisible();
    
    await page.locator('.evolve-modal .close-btn').click();
    await expect(page.locator('.evolve-modal')).not.toBeVisible();
    
    const docsButton = page.locator('button:has-text("📚 Living Docs")');
    await docsButton.click();
    
    await expect(page.locator('.docs-modal')).toBeVisible({ timeout: 10_000 });
    
    await expect(page.locator('button:has-text("Sync Now")')).toBeVisible();
    await page.locator('button:has-text("Sync Now")').first().click();
  });
});
