import { useEffect, useState } from 'react';

export function useMotion() {
  const [preference, setPreference] = useState(() => {
    try { return localStorage.getItem('wr-motion'); } catch { return null; }
  });
  const [systemReduced, setSystemReduced] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const changed = () => setSystemReduced(query.matches);
    query.addEventListener('change', changed);
    return () => query.removeEventListener('change', changed);
  }, []);
  const reduced = preference === null ? systemReduced : preference === 'off';
  useEffect(() => { document.documentElement.dataset.motion = reduced ? 'off' : 'on'; }, [reduced]);
  return [reduced, () => {
    const next = reduced ? 'on' : 'off'; setPreference(next);
    try { localStorage.setItem('wr-motion', next); } catch { /* preference still works for this page */ }
  }];
}
