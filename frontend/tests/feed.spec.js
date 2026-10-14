import { test, expect } from '@playwright/test';

const videos = [
  { id: 'python', title: 'Python Data Engineering', description: 'Explore data pipelines.', creators: ['Tech Academy'], topics: ['python', 'airflow'], view_count: 15000 },
  { id: 'music', title: 'Music discovery', description: 'Discover something new.', creators: ['Studio'], topics: ['music'], view_count: 2500 },
];

async function signIn(page) {
  const reactions = {};
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.route('**/api/auth/login', (route) => route.fulfill({ json: { access_token: 'test-token' } }));
  await page.route('**/api/auth/me', (route) => route.fulfill({ json: { username: 'admin', expires_at: Math.floor(Date.now() / 1000) + 1800 } }));
  await page.route('**/api/videos*', (route) => route.fulfill({ json: { videos: (route.request().url().includes('video_id=') ? [videos[1]] : videos).map((video) => ({ ...video, reaction: reactions[video.id] || null })) } }));
  await page.route('**/api/videos/reaction', (route) => {
    const payload = route.request().postDataJSON();
    reactions[payload.video_id] = payload.reaction === 'none' ? null : payload.reaction;
    return route.fulfill({ json: { video_id: payload.video_id, reaction: reactions[payload.video_id] } });
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Enter Aphrodite' }).click();
  await expect(page).toHaveURL(/\/feed$/);
  await expect(page.getByRole('heading', { name: videos[0].title, exact: true })).toBeVisible();
}

test('separate feed route, navigation, similar results, and sign-out', async ({ page }) => {
  await signIn(page);
  await expect(page.locator('.editorial')).toHaveCount(0);
  await page.getByRole('button', { name: 'Next video', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Next video', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Previous video', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Previous video', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: `Find similar videos to ${videos[0].title}`, exact: true }).click();
  await expect(page.locator('.feed-filter')).toContainText(videos[0].title);
  await expect(page.locator('.feed-slide')).toHaveCount(1);
  await page.getByRole('button', { name: 'Back to catalog' }).click();
  await expect(page.locator('.feed-slide')).toHaveCount(2);
  await page.screenshot({ path: 'test-results/feed-desktop.png' });
  await page.locator('.feed-account button').click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading', { name: 'Welcome back.' })).toBeVisible();
});

test('mobile feed fits viewport and catalog errors can be retried', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await signIn(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/feed-mobile.png' });
  await page.route('**/api/videos*', (route) => route.fulfill({ status: 503, json: { detail: 'Catalog temporarily unavailable.' } }));
  await page.getByRole('button', { name: /Find similar videos to/ }).first().click();
  await expect(page.getByRole('alert')).toHaveText('Catalog temporarily unavailable.');
  await page.route('**/api/videos*', (route) => route.fulfill({ json: { videos: [] } }));
  await page.getByRole('button', { name: 'Try again' }).click();
  await expect(page.getByRole('heading', { name: 'Nothing here just yet.' })).toBeVisible();
  await page.getByRole('button', { name: 'Sign out' }).filter({ visible: true }).click();
  await expect(page).toHaveURL(/\/$/);
});

test('direct feed access without a session returns to sign-in', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/feed');
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading', { name: 'Welcome back.' })).toBeVisible();
});

test('like/dislike toggles save, persist across feed loads, and report failures', async ({ page }) => {
  await signIn(page);
  const like = page.getByRole('button', { name: `Like ${videos[0].title}`, exact: true });
  const dislike = page.getByRole('button', { name: `Dislike ${videos[0].title}`, exact: true });
  await like.click();
  await expect(like).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', { name: 'For you' }).click();
  await expect(like).toHaveAttribute('aria-pressed', 'true');
  await dislike.click();
  await expect(dislike).toHaveAttribute('aria-pressed', 'true');
  await expect(like).toHaveAttribute('aria-pressed', 'false');
  await dislike.click();
  await expect(dislike).toHaveAttribute('aria-pressed', 'false');
  await page.route('**/api/videos/reaction', (route) => route.fulfill({ status: 503, json: { detail: 'Could not save feedback.' } }));
  await like.click();
  await expect(page.getByRole('alert')).toHaveText('Could not save feedback.');
  await expect(like).toHaveAttribute('aria-pressed', 'false');
  await page.screenshot({ path: 'test-results/feed-reactions.png' });
});

test('graph playback links mount the active player and stop it on navigation', async ({ page }) => {
  await signIn(page);
  await page.route('https://www.youtube-nocookie.com/**', (route) => route.fulfill({ contentType: 'text/html', body: '<html><body>Embedded player</body></html>' }));
  await page.route('https://example.com/video.mp4', (route) => route.abort());
  await page.route('**/api/videos*', (route) => route.fulfill({ json: { videos: [
    { ...videos[0], playback_url: 'https://youtu.be/1i0hqFR5hKs' },
    { ...videos[1], playback_url: 'https://example.com/video.mp4' },
  ] } }));
  await page.getByRole('button', { name: 'For you' }).click();
  await expect(page.locator('iframe.feed-player')).toHaveAttribute('src', /youtube-nocookie.com\/embed\/1i0hqFR5hKs/);
  await page.getByRole('button', { name: 'Next video', exact: true }).click();
  await expect(page.locator('iframe.feed-player')).toHaveCount(0);
  await expect(page.getByText('This video could not be played here.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Open original video' })).toHaveAttribute('href', 'https://example.com/video.mp4');
});

test('YouTube IDs without links embed automatically with muted autoplay and origin', async ({ page }) => {
  await signIn(page);
  await page.route('https://www.youtube-nocookie.com/**', (route) => route.fulfill({ contentType: 'text/html', body: '<html><body>Embedded player</body></html>' }));
  await page.route('**/api/videos*', (route) => route.fulfill({ json: { videos: [{ ...videos[0], id: '1i0hqFR5hKs' }] } }));
  await page.getByRole('button', { name: 'For you' }).click();
  const player = page.locator('iframe.feed-player');
  await expect(player).toBeVisible();
  await expect(player).toHaveAttribute('src', /autoplay=1&mute=1/);
  await expect(player).toHaveAttribute('src', /origin=http%3A%2F%2F127.0.0.1%3A5173/);
  await expect(player).toHaveAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
  const frame = await player.boundingBox();
  const info = await page.locator('.feed-video-info').boundingBox();
  expect(frame.y + frame.height).toBeLessThanOrEqual(info.y);
  await page.screenshot({ path: 'test-results/feed-youtube.png' });
});

test('polling appends new videos without resetting the active card', async ({ page }) => {
  await signIn(page);
  await page.getByRole('button', { name: 'Next video', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Next video', exact: true })).toBeDisabled();
  await page.route('**/api/videos*', (route) => route.fulfill({ json: { videos: [...videos, { id: 'new-record', title: 'New graph record' }] } }));
  await expect(page.locator('.feed-slide')).toHaveCount(3, { timeout: 20000 });
  await expect(page.locator('.feed-pagination > span')).toContainText('02');
  await expect(page.getByRole('button', { name: 'Next video', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Next video', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'New graph record', exact: true })).toBeVisible();
});
