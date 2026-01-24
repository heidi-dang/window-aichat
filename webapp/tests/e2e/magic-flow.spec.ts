import { test, expect } from '@playwright/test';

test.describe('EvolveAI Magic Feature User Flow', () => {
  test('new user discovers and uses EvolveAI predictive evolution', async ({ page }) => {
    // Start timer for performance measurement
    const startTime = Date.now();
    
    // Navigate to the application
    await page.goto('http://localhost:5173');
    
    // Verify the app loads within 2 seconds (realistic for dev environment)
    const loadTime = Date.now() - startTime;
    expect(loadTime).toBeLessThan(2000);
    
    // Wait for the sidebar to be visible
    await expect(page.locator('.sidebar')).toBeVisible({ timeout: 2000 });
    
    // Click on EvolveAI button (should be instant)
    const evolveButton = page.locator('button:has-text("🧬 EvolveAI")');
    await expect(evolveButton).toBeVisible();
    await evolveButton.click();
    
    // Verify EvolveAI modal appears within 500ms
    const modalStartTime = Date.now();
    await expect(page.locator('.evolve-modal')).toBeVisible({ timeout: 500 });
    const modalLoadTime = Date.now() - modalStartTime;
    expect(modalLoadTime).toBeLessThan(500);
    
    // Verify predictive insights are displayed
    await expect(page.locator('h2:has-text("EvolveAI - Predictive Code Evolution")')).toBeVisible();
    await expect(page.locator('text=AI-powered insights to proactively improve your codebase')).toBeVisible();
    
    // Test interaction with refresh button
    const refreshButton = page.locator('button:has-text("Refresh Analysis")');
    await expect(refreshButton).toBeVisible();
    
    // Close modal
    await page.locator('.close-btn').click();
    await expect(page.locator('.evolve-modal')).not.toBeVisible();
    
    // Test Living Documentation
    const docsButton = page.locator('button:has-text("📚 Living Docs")');
    await docsButton.click();
    
    // Verify docs modal loads quickly
    const docsStartTime = Date.now();
    await expect(page.locator('.docs-modal')).toBeVisible({ timeout: 500 });
    const docsLoadTime = Date.now() - docsStartTime;
    expect(docsLoadTime).toBeLessThan(500);
    
    // Verify sync functionality
    await expect(page.locator('button:has-text("Sync Now")')).toBeVisible();
    await page.locator('button:has-text("Sync Now")').first().click();
    
    // Total test time should be under 3 seconds (realistic for comprehensive flow)
    const totalTime = Date.now() - startTime;
    expect(totalTime).toBeLessThan(3000);
    
    console.log(`✅ EvolveAI User Flow completed in ${totalTime}ms`);
  });
});
