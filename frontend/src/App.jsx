import { useCallback, useEffect, useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import { ArrowUpRight } from 'lucide-react';
import SplashIntro from './components/SplashIntro';
import LoginCard from './components/LoginCard';
import VideoFeed from './components/VideoFeed';

export default function App() {
  const [intro, setIntro] = useState(true);
  const [session, setSession] = useState(null);
  const [notice, setNotice] = useState('');
  const [path, setPath] = useState(window.location.pathname);
  const navigate = useCallback((next, replace = false) => {
    window.history[replace ? 'replaceState' : 'pushState']({}, '', next);
    setPath(next);
  }, []);
  useEffect(() => {
    const update = () => setPath(window.location.pathname);
    window.addEventListener('popstate', update);
    return () => window.removeEventListener('popstate', update);
  }, []);
  useEffect(() => {
    if (!session && path === '/feed') navigate('/', true);
    if (session && path !== '/feed') navigate('/feed', true);
  }, [session, path, navigate]);
  const finishIntro = useCallback(() => setIntro(false), []);

  useEffect(() => {
    if (!session) return;
    const expire = () => {
      setSession(null);
      setNotice('Your session has ended. Please sign in again.');
    };
    const timer = setTimeout(expire, Math.max(0, session.expires_at * 1000 - Date.now()));
    const check = () => { if (Date.now() >= session.expires_at * 1000) expire(); };
    document.addEventListener('visibilitychange', check);
    return () => { clearTimeout(timer); document.removeEventListener('visibilitychange', check); };
  }, [session]);

  if (session) return <VideoFeed session={session} onLogout={() => { setSession(null); setNotice('You have been signed out. Until next time.'); navigate('/', true); }} />;

  return (
    <>
      <div className="site-shell" inert={intro ? true : undefined} aria-hidden={intro || undefined}>
        <header className="site-header"><a className="wordmark" href="/" aria-label="Aphrodite.ai home">Aphrodite<span className="brand-ai">.ai</span></a><span className="header-note">FROM SOURCE DATA TO RECOMMENDATIONS</span><span className="header-edition">EST. 2026 <span className="small-star">✦</span></span></header>
        <main className="main-grid">
          <section className="editorial" aria-labelledby="editorial-heading">
            <div className="eyebrow editorial-kicker"><span className="short-line" /> SOURCE INGESTION. CONTEXTUAL INSIGHT.</div>
            <h1 id="editorial-heading">Your data.<br /><span className="italic-line">In context.</span><br /><span className="last-line">With clarity.<span className="heading-star" aria-hidden="true">✦</span></span></h1>
            <p className="editorial-description">A workspace designed to ingest codebases, documents, and data,<br />and turn your sources into contextual recommendations.</p>
            <p className="editorial-description roadmap-caption"><span className="eyebrow">ON THE ROADMAP</span><br />Code security audits and dead-code detection.</p>
            <div className="editorial-bottom"><span className="edition-number">N° 001</span><span className="eyebrow">INGEST. UNDERSTAND. RECOMMEND.</span><ArrowUpRight size={18} strokeWidth={1} /></div>
            <div className="orbit-art" aria-hidden="true"><i /><i /><i /><span>✦</span></div>
          </section>
          <div className="auth-column"><div className="auth-caption"><span className="status-dot" /> YOUR SOURCE INTELLIGENCE WORKSPACE</div><AnimatePresence mode="wait"><LoginCard key="login" notice={notice} onAuthenticated={(value) => { setNotice(''); setIntro(false); setSession(value); navigate('/feed'); }} /></AnimatePresence><p className="below-card">MORE CONTEXT. BETTER RECOMMENDATIONS.</p></div>
        </main>
        <footer className="site-footer"><span>© {new Date().getFullYear()} APHRODITE.AI</span><button onClick={() => setIntro(true)}>REPLAY THE INTRO <ArrowUpRight size={12} /></button><span className="footer-motto">CODEBASES. DOCUMENTS. DATA.</span></footer>
      </div>
      <AnimatePresence>{intro && <SplashIntro onComplete={finishIntro} />}</AnimatePresence>
    </>
  );
}
