import { test, expect } from '@playwright/test';

test('intro, failed login, real authenticated session, and logout', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Skip introduction' })).toBeVisible();
  await page.getByRole('button', { name: 'Skip introduction' }).click();
  await expect(page.getByRole('heading', { name: 'Welcome back.' })).toBeVisible();
  await page.getByLabel('Password', { exact: true }).fill('wrong-password');
  await page.getByRole('button', { name: 'Enter Aphrodite' }).click();
  await expect(page.getByRole('alert')).toContainText("Those credentials don't quite match");
  await page.getByLabel('Password', { exact: true }).fill('root');
  await page.getByRole('button', { name: 'Show password' }).click();
  await expect(page.getByLabel('Password', { exact: true })).toHaveAttribute('type', 'text');
  await page.getByRole('button', { name: 'Enter Aphrodite' }).click();
  await expect(page).toHaveURL(/\/feed$/);
  await expect(page.getByRole('heading', { name: 'Video recommendations', exact: false })).toBeVisible();
  await expect(page.locator('.feed-video-info h2').first()).toBeVisible();
  const selectedTitle = await page.locator('.feed-video-info h2').first().textContent();
  const similarResponse = page.waitForResponse((response) => response.url().includes('/api/videos?video_id=') && response.status() === 200);
  await page.getByRole('button', { name: /Find similar videos to/ }).first().click();
  await similarResponse;
  await expect(page.locator('.feed-filter')).toContainText(selectedTitle);
  await expect(page.getByRole('heading', { name: selectedTitle, exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Sign out', exact: true }).filter({ visible: true }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading', { name: 'Welcome back.' })).toBeVisible();
  await expect(page.getByText('You have been signed out. Until next time.')).toBeVisible();
});

test('mobile layout, reduced motion, and network failure', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Skip introduction' })).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Welcome back.' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.route('**/api/auth/login', (route) => route.abort());
  await page.getByRole('button', { name: 'Enter Aphrodite' }).click();
  await expect(page.getByRole('alert')).toContainText('connection was interrupted');
  await page.screenshot({ path: 'test-results/mobile.png', fullPage: true });
});

test('cinematic intro completes automatically and desktop has no overflow', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Skip introduction' })).toHaveCount(0, { timeout: 7000 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/desktop.png', fullPage: true });
  await page.getByRole('button', { name: 'Replay the intro' }).click();
  await expect(page.getByRole('button', { name: 'Skip introduction' })).toBeVisible();
});
