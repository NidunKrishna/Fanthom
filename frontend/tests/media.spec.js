import { test, expect } from '@playwright/test';
import { videoSource } from '../src/lib/media.js';

test('graph links support YouTube, direct media, external pages, and reject unsafe schemes', () => {
  expect(videoSource('https://youtu.be/1i0hqFR5hKs').type).toBe('youtube');
  expect(videoSource('https://www.youtube.com/watch?v=1i0hqFR5hKs').url).toContain('youtube-nocookie.com/embed/1i0hqFR5hKs');
  expect(videoSource('https://youtube.com/shorts/1i0hqFR5hKs').type).toBe('youtube');
  expect(videoSource('https://example.com/movie.mp4?token=abc').type).toBe('file');
  expect(videoSource('https://example.com/watch/123').type).toBe('external');
  expect(videoSource('https://youtube.com.attacker.test/watch?v=1i0hqFR5hKs').type).toBe('external');
  expect(videoSource('javascript:alert(1)')).toBeNull();
  expect(videoSource('http://example.com/movie.mp4')).toBeNull();
  expect(videoSource(null, '1i0hqFR5hKs').type).toBe('youtube');
  expect(videoSource(null, 'abc123')).toBeNull();
  expect(videoSource('www.youtube.com/watch?v=1i0hqFR5hKs').type).toBe('youtube');
  expect(videoSource(null, '1i0hqFR5hKs').url).toContain('autoplay=1&mute=1');
});
