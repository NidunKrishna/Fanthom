import { useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { ArrowUpRight, Eye, EyeOff, LoaderCircle, LockKeyhole } from 'lucide-react';
import { getProfile, login } from '../lib/api';

const showDemo = import.meta.env.VITE_SHOW_DEMO_CREDENTIALS !== 'false';

export default function LoginCard({ onAuthenticated, notice }) {
  const [username, setUsername] = useState(showDemo ? 'admin' : '');
  const [password, setPassword] = useState(showDemo ? 'root' : '');
  const [visible, setVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const reduced = useReducedMotion();

  async function submit(event) {
    event.preventDefault();
    if (loading) return;
    setLoading(true);
    setError('');
    try {
      const result = await login(username, password);
      const profile = await getProfile(result.access_token);
      onAuthenticated({ token: result.access_token, ...profile });
    } catch (failure) {
      setError(failure.message);
      setAttempt((value) => value + 1);
    } finally {
      setLoading(false);
    }
  }

  return (
    <motion.section className="auth-card" aria-labelledby="login-heading" exit={{ opacity: 0, y: reduced ? 0 : -16 }}>
      <div className="flex items-center justify-between"><span className="eyebrow">YOUR WORKSPACE</span><span className="card-index">01 / ACCESS</span></div>
      <div className="card-heading"><h2 id="login-heading">Welcome back.</h2><p>Sign in to explore the source intelligence concept.</p></div>
      <motion.form key={attempt} onSubmit={submit} animate={{ x: error && !reduced ? [0, -5, 5, -3, 3, 0] : 0 }} transition={{ duration: 0.35 }} aria-busy={loading}>
        <div className="field"><input id="username" name="username" autoComplete="username" placeholder=" " value={username} onChange={(event) => setUsername(event.target.value)} maxLength={128} required disabled={loading} aria-describedby={error ? 'login-error' : undefined} /><label htmlFor="username">Username</label></div>
        <div className="field password-field"><input id="password" name="password" type={visible ? 'text' : 'password'} autoComplete="current-password" placeholder=" " value={password} onChange={(event) => setPassword(event.target.value)} maxLength={1024} required disabled={loading} aria-describedby={error ? 'login-error' : undefined} /><label htmlFor="password">Password</label><button className="password-toggle" type="button" onClick={() => setVisible(!visible)} aria-label={visible ? 'Hide password' : 'Show password'} aria-pressed={visible}>{visible ? <EyeOff size={17} /> : <Eye size={17} />}</button></div>
        <div className="feedback" aria-live="polite">{error ? <p id="login-error" role="alert">{error}</p> : notice ? <p>{notice}</p> : <span className="flex items-center gap-2"><LockKeyhole size={11} /> Your workspace starts with a secure sign-in.</span>}</div>
        <button className="primary-button" type="submit" disabled={loading}><span>{loading ? 'Entering your workspace' : 'Enter Aphrodite'}</span>{loading ? <LoaderCircle size={18} className="spinner" /> : <ArrowUpRight size={20} strokeWidth={1.5} />}</button>
      </motion.form>
      {showDemo && <div className="demo-credentials"><span className="demo-label">EXPLORE THE DEMO</span><span>username <code>admin</code><span className="demo-divider">/</span>password <code>root</code></span></div>}
      <div className="card-foot"><span className="tiny-diamond" /> From scattered sources to informed next steps.</div>
    </motion.section>
  );
}
