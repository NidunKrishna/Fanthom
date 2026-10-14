import { useState } from 'react';

/** Mount only the visible feed player; unmounting stops offscreen playback. */
export default function VideoPlayer({ media, title }) {
  const [failed, setFailed] = useState(false);
  if (failed) return <div className="feed-playback-error"><p>This video could not be played here.</p><a href={media.original || media.url} target="_blank" rel="noopener noreferrer">Open original video</a></div>;
  if (media.type === 'youtube') {
    const source = new URL(media.url);
    source.searchParams.set('origin', window.location.origin);
    return <iframe className="feed-player" title={`Play ${title}`} src={source.href} allow="autoplay; encrypted-media; gyroscope; picture-in-picture; fullscreen" allowFullScreen referrerPolicy="strict-origin-when-cross-origin" onError={() => setFailed(true)} />;
  }
  return <video className="feed-player" src={media.url} controls autoPlay muted playsInline preload="metadata" onError={() => setFailed(true)} />;
}
