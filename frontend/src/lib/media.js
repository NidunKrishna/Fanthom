/** Classify graph-supplied HTTPS links without turning arbitrary URLs into embeds. */
export function videoSource(value, videoId) {
  if (!value && /^[a-zA-Z0-9_-]{11}$/.test(String(videoId || ''))) value = `https://www.youtube.com/watch?v=${videoId}`;
  if (!value) return null;
  try {
    const normalized = String(value).trim();
    const url = new URL(/^(www\.)?(youtube\.com|youtu\.be)\//i.test(normalized) ? `https://${normalized}` : normalized);
    if (url.protocol !== 'https:') return null;
    const host = url.hostname.toLowerCase();
    let id;
    if (host === 'youtu.be') id = url.pathname.split('/')[1];
    if (['youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtube-nocookie.com', 'www.youtube-nocookie.com'].includes(host)) {
      id = url.searchParams.get('v') || (/^\/(shorts|embed)\//.test(url.pathname) ? url.pathname.split('/')[2] : null);
    }
    if (id && /^[a-zA-Z0-9_-]{11}$/.test(id)) return { type: 'youtube', url: `https://www.youtube-nocookie.com/embed/${id}?playsinline=1&autoplay=1&mute=1&controls=1&rel=0`, original: url.href };
    if (/\.(mp4|webm|ogg|mov)$/i.test(url.pathname)) return { type: 'file', url: url.href };
    return { type: 'external', url: url.href };
  } catch { return null; }
}
