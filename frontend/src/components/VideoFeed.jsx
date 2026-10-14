import { useEffect, useRef, useState } from 'react';
import { ArrowDown, ArrowUp, ArrowUpRight, Compass, Film, LogOut, Play, Sparkles, ThumbsUp, ThumbsDown, X } from 'lucide-react';
import { getRecommendations, saveReaction } from '../lib/api';
import { videoSource } from '../lib/media';
import './VideoFeed.css';
import VideoPlayer from './VideoPlayer';

export default function VideoFeed({ session, onLogout }) {
  const [videos, setVideos] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const [active, setActive] = useState(0);
  const [saving, setSaving] = useState(null);
  const [feedbackError, setFeedbackError] = useState('');
  const list = useRef(null);
  const title = useRef(null);
  const savingRef = useRef(false);
  const feedbackVersion = useRef(0);
  useEffect(() => { title.current?.focus(); document.title = 'For you · Aphrodite.ai'; return () => { document.title = 'Aphrodite.ai'; }; }, []);
  useEffect(() => {
    let current = true;
    setLoading(true); setError('');
    getRecommendations(session.token, selected?.id)
      .then((data) => { if (current) { setVideos(data.videos); setActive(0); } })
      .catch((failure) => { if (current) setError(failure.message); })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [session.token, selected, retry]);
  useEffect(() => {
    let current = true;
    let timer;
    async function poll() {
      try {
        if (!document.hidden && !savingRef.current) {
          const version = feedbackVersion.current;
          const data = await getRecommendations(session.token, selected?.id);
          if (current && !savingRef.current && version === feedbackVersion.current) setVideos((previous) => {
            const known = new Map(previous.map((video) => [video.id, video]));
            const incoming = new Map(data.videos.map((video) => [video.id, video]));
            return [...previous.map((video) => incoming.get(video.id) || video), ...data.videos.filter((video) => !known.has(video.id))];
          });
        }
      } catch { /* Keep the current feed on transient errors; retry next interval. */ }
      finally { if (current) timer = setTimeout(poll, 10000); }
    }
    timer = setTimeout(poll, 10000);
    return () => { current = false; clearTimeout(timer); };
  }, [session.token, selected, retry]);
  useEffect(() => {
    if (loading || !list.current) return;
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) if (entry.isIntersecting) setActive(Number(entry.target.dataset.index));
    }, { root: list.current, threshold: 0.6 });
    list.current.querySelectorAll('.feed-slide').forEach((slide) => observer.observe(slide));
    return () => observer.disconnect();
  }, [videos, loading]);
  const move = (direction) => list.current?.children[Math.max(0, Math.min(videos.length - 1, active + direction))]?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'nearest' });
  async function react(video, reaction) {
    if (saving) return;
    feedbackVersion.current += 1;
    savingRef.current = true;
    setSaving(video.id); setFeedbackError('');
    try {
      const result = await saveReaction(session.token, video.id, video.reaction === reaction ? 'none' : reaction);
      setVideos((current) => current.map((item) => item.id === video.id ? { ...item, reaction: result.reaction } : item));
    } catch (failure) { setFeedbackError(failure.message); }
    finally { savingRef.current = false; setSaving(null); }
  }

  return <div className="feed-page">
    <aside className="feed-sidebar">
      <a className="wordmark" href="/feed" onClick={(event) => { event.preventDefault(); setSelected(null); setRetry((value) => value + 1); }}>Aphrodite<span className="brand-ai">.ai</span></a>
      <div className="feed-section-label">A LITTLE MORE YOU.</div>
      <nav aria-label="Feed navigation"><button className={!selected ? 'feed-nav active' : 'feed-nav'} onClick={() => { setSelected(null); setRetry((value) => value + 1); }}><Compass size={21} /> For you <span>01</span></button></nav>
      <div className="feed-sidebar-note"><Sparkles size={19} /><p>Follow your curiosity.</p><span>Recommendations connected by the topics you explore.</span></div>
      <div className="feed-account"><div className="feed-avatar">{(session.name || session.username).slice(0, 1).toUpperCase()}</div><div><strong>{session.name || session.username}</strong><span>Your private feed</span></div><button aria-label="Sign out" title="Sign out" onClick={onLogout}><LogOut size={19} /></button></div>
    </aside>
    <main className="feed-main">
      <header className="feed-header"><div><span className="feed-section-label">YOUR NEXT DISCOVERY</span><h1 ref={title} tabIndex={-1}>Video recommendations<span> / {selected ? 'Similar' : 'For you'}</span></h1></div><button className="feed-mobile-logout" onClick={onLogout} aria-label="Sign out"><LogOut size={20} /></button><span className="feed-live"><i /> CONNECTED TO YOUR CATALOG</span></header>
      {selected && <div className="feed-filter"><Sparkles size={15} /><span>Similar to <strong>{selected.title}</strong></span><button onClick={() => setSelected(null)} aria-label="Back to catalog"><X size={17} /></button></div>}
      {feedbackError && <p className="feed-feedback-error" role="alert">{feedbackError}</p>}
      <div className="feed-stage">
        {loading ? <div className="feed-state" role="status"><div className="feed-loader" /><h2>Finding your next discovery.</h2><p>Connecting the dots in your catalog.</p></div> : error ? <div className="feed-state"><Film size={34} /><h2>Let’s try that again.</h2><p role="alert">{error}</p><button onClick={() => setRetry((value) => value + 1)}>Try again <ArrowUpRight size={17} /></button></div> : !videos.length ? <div className="feed-state"><Film size={34} /><h2>Nothing here just yet.</h2><p>{selected ? 'Try another video from your catalog.' : 'Videos will appear when your catalog has content.'}</p>{selected && <button onClick={() => setSelected(null)}>Back to catalog</button>}</div> : <>
          <div className="feed-scroll" ref={list} tabIndex={0} aria-label="Video feed. Scroll to explore videos." onKeyDown={(event) => { if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); move(event.key === 'ArrowDown' ? 1 : -1); } }}>
            {videos.map((video, index) => {
              const media = videoSource(video.playback_url, video.id);
              return <article key={video.id} className={`feed-slide feed-tone-${index % 4}`} data-index={index} aria-label={video.title}>
                <div className="feed-video-frame">
                  {media && media.type !== 'external' && active === index ? <VideoPlayer key={video.id} media={media} title={video.title} /> : <div className="feed-art" aria-hidden="true"><div className="feed-orbit" /><span className="feed-art-index">{String(index + 1).padStart(2, '0')}</span><div className="feed-art-title">{video.title}</div><Play size={30} strokeWidth={1} /></div>}
                  <div className="feed-card-top"><span><Sparkles size={13} /> {selected ? 'SIMILAR DISCOVERIES' : 'FOR YOUR CURIOSITY'}</span><span>{String(index + 1).padStart(2, '0')} / {String(videos.length).padStart(2, '0')}</span></div>
                  <div className="feed-video-info"><div className="feed-creator"><span className="feed-avatar">{(video.creators?.[0] || 'A').slice(0, 1)}</span><strong>{video.creators?.join(', ') || 'From your catalog'}</strong></div><h2>{video.title}</h2><p>{video.description}</p><div className="feed-tags">{(video.topics || []).slice(0, 4).map((topic) => <span key={topic}>#{topic.replace(/\s+/g, '')}</span>)}</div>{(media?.type === 'external' || media?.type === 'youtube') && <a className="feed-watch-link" href={media.original || media.url} target="_blank" rel="noopener noreferrer">Watch video <ArrowUpRight size={13} /></a>}{!media && <span className="feed-media-note"><Film size={13} /> Catalog preview · playback URL not supplied</span>}</div>
                </div>
                <div className="feed-actions"><button disabled={Boolean(saving)} aria-label={`Like ${video.title}`} aria-pressed={video.reaction === 'like'} onClick={() => react(video, 'like')}><span><ThumbsUp size={22} /></span>{saving === video.id ? 'Saving...' : 'Like'}</button><button disabled={Boolean(saving)} aria-label={`Dislike ${video.title}`} aria-pressed={video.reaction === 'dislike'} onClick={() => react(video, 'dislike')}><span><ThumbsDown size={22} /></span>Dislike</button><button onClick={() => setSelected({ id: video.id, title: video.title })} aria-label={`Find similar videos to ${video.title}`}><span><Sparkles size={23} /></span>Find similar</button><div className="feed-stat"><strong>{new Intl.NumberFormat('en', { notation: 'compact' }).format(video.view_count || 0)}</strong><span>catalog views</span></div></div>
              </article>;
            })}
          </div>
          <div className="feed-pagination"><span>{String(active + 1).padStart(2, '0')}<i />{String(videos.length).padStart(2, '0')}</span><button aria-label="Previous video" disabled={active === 0} onClick={() => move(-1)}><ArrowUp size={20} /></button><button aria-label="Next video" disabled={active === videos.length - 1} onClick={() => move(1)}><ArrowDown size={20} /></button><small>SCROLL TO EXPLORE</small></div>
        </>}
      </div>
      <footer className="feed-footer"><span>LESS SEARCHING. MORE DISCOVERING.</span><span>APHRODITE.AI <Sparkles size={11} /></span></footer>
    </main>
  </div>;
}
