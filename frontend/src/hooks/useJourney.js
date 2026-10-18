import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';

export const CHAPTERS = [
  { id: 'experience', label: 'Home', short: 'Home' },
  { id: 'recovery', label: 'Workspace', short: 'Recover' },
  { id: 'view-history', label: 'History', short: 'Review' },
  { id: 'view-design', label: 'How it works', short: 'Understand' },
];

// Native scrolling keeps long audit records, keyboard navigation and browser history usable.
export function useJourney(reduced, loaded) {
  const [active, setActive] = useState('experience');
  const meter = useRef(null);
  const restored = useRef(false);
  const reload = useRef(performance.getEntriesByType('navigation')[0]?.type === 'reload');
  const go = useCallback((id, remember = true, instant = false) => {
    const target = document.getElementById(id);
    if (!target) return;
    if (remember && window.location.hash !== `#${id}`) window.history.pushState(null, '', `#${id}`);
    target.tabIndex = -1;
    target.focus({ preventScroll: true });
    target.scrollIntoView({ behavior: reduced || instant ? 'instant' : 'smooth', block: 'start' });
  }, [reduced]);

  useLayoutEffect(() => {
    const previous = window.history.scrollRestoration;
    window.history.scrollRestoration = 'manual';
    // Reload is a fresh entrance. A deliberately opened section link still works.
    if (reload.current) {
      window.history.replaceState(null, '', window.location.pathname + window.location.search);
      window.scrollTo({ top: 0, behavior: 'instant' });
    }
    return () => { window.history.scrollRestoration = previous; };
  }, []);

  useEffect(() => {
    let frame = 0;
    const update = () => {
      frame = 0;
      const distance = document.documentElement.scrollHeight - window.innerHeight;
      const progress = Math.max(0, Math.min(1, window.scrollY / Math.max(1, distance)));
      if (meter.current) {
        meter.current.style.transform = `scaleX(${progress})`;
        meter.current.parentElement.setAttribute('aria-valuenow', String(Math.round(progress * 100)));
      }
      let current = CHAPTERS[0].id;
      for (const chapter of CHAPTERS) {
        if (document.getElementById(chapter.id)?.getBoundingClientRect().top <= Math.min(260, window.innerHeight * .32)) current = chapter.id;
      }
      setActive(current);
    };
    const scroll = () => { if (!frame) frame = requestAnimationFrame(update); };
    window.addEventListener('scroll', scroll, { passive: true });
    window.addEventListener('resize', scroll);
    const resized = new ResizeObserver(scroll);
    resized.observe(document.getElementById('main'));
    update();
    return () => { window.removeEventListener('scroll', scroll); window.removeEventListener('resize', scroll); resized.disconnect(); cancelAnimationFrame(frame); };
  }, []);

  useEffect(() => {
    const restore = () => {
      const id = window.location.hash.slice(1);
      if (CHAPTERS.some(c => c.id === id)) go(id, false);
      else if (!id) go('experience', false);
    };
    window.addEventListener('popstate', restore);
    window.addEventListener('hashchange', restore);
    if (loaded && !restored.current) {
      restored.current = true;
      const id = window.location.hash.slice(1);
      go(!reload.current && CHAPTERS.some(c => c.id === id) ? id : 'experience', false, true);
    }
    return () => { window.removeEventListener('popstate', restore); window.removeEventListener('hashchange', restore); };
  }, [go, loaded]);

  useEffect(() => {
    const elements = [...document.querySelectorAll('.section-heading, .workspace-shell, .chapter-divider, .history-list, .architecture-step, .design-notes > article, .closing-note')];
    if (reduced || !window.IntersectionObserver) {
      elements.forEach(el => el.classList.remove('reveal-ready'));
      return;
    }
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) { entry.target.classList.add('in-view'); observer.unobserve(entry.target); }
    }), { threshold: 0, rootMargin: '0px 0px -30px 0px' });
    // Revealing content already in view can change the browser's scroll anchor.
    // Keep the current reading position still; animate only sections ahead of it.
    elements.forEach(el => {
      if (el.getBoundingClientRect().top < window.innerHeight) el.classList.add('in-view');
      el.classList.add('reveal-ready');
      if (!el.classList.contains('in-view')) observer.observe(el);
    });
    const focused = event => event.target.closest('.reveal-ready')?.classList.add('in-view');
    document.addEventListener('focusin', focused);
    return () => { observer.disconnect(); document.removeEventListener('focusin', focused); elements.forEach(el => el.classList.remove('reveal-ready')); };
  }, [reduced, loaded]);
  return { active, go, meter };
}
