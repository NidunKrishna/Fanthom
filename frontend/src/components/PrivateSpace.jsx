import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { ArrowUpRight, Check, LogOut } from 'lucide-react';

export default function PrivateSpace({ session, onLogout }) {
  const heading = useRef(null);
  useEffect(() => { heading.current?.focus(); }, []);
  return (
    <motion.section className="auth-card success-card" initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }} aria-labelledby="welcome-heading">
      <div className="flex items-center justify-between"><span className="eyebrow">YOUR WORKSPACE</span><Check size={18} strokeWidth={1.3} /></div>
      <div className="success-emblem" aria-hidden="true">A<span>✦</span></div>
      <h2 id="welcome-heading" ref={heading} tabIndex={-1}>You’re in.</h2>
      <p className="success-description">Welcome, {session.username}.<br />Explore the source intelligence concept.</p>
      <div className="session-status"><span className="status-dot" /> Identity verified <ArrowUpRight size={13} /></div>
      <p className="session-note">The vision: ingest sources and surface recommendations.<br />Planned: code security audits and dead-code detection.</p>
      <button className="primary-button" onClick={onLogout}><span>Sign out</span><LogOut size={17} strokeWidth={1.5} /></button>
    </motion.section>
  );
}
