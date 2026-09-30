import { useEffect } from 'react';
import { motion, useReducedMotion } from 'framer-motion';

export default function SplashIntro({ onComplete }) {
  const reduced = useReducedMotion();
  useEffect(() => {
    const timer = setTimeout(onComplete, reduced ? 450 : 3300);
    return () => clearTimeout(timer);
  }, [onComplete, reduced]);

  return (
    <motion.div className="splash" exit={{ opacity: 0 }} transition={{ duration: reduced ? 0.15 : 1 }}>
      <motion.div className="splash-wordmark" initial={{ opacity: 0, filter: reduced ? 'none' : 'blur(12px)', letterSpacing: '-0.035em' }}
        animate={{ opacity: 1, filter: 'blur(0px)', letterSpacing: '0.035em' }} transition={{ duration: reduced ? 0.1 : 1.5, ease: [0.22, 1, 0.36, 1] }}>
        Aphrodite<span className="brand-ai">.ai</span>
      </motion.div>
      <motion.p className="eyebrow mt-7" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: reduced ? 0 : 0.8, duration: 1 }}>YOUR SOURCES. CONNECTED BY CONTEXT.</motion.p>
      <button className="skip-intro" onClick={onComplete}>Skip introduction <span aria-hidden="true">↗</span></button>
    </motion.div>
  );
}
