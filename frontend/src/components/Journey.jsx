import { ArrowDown, ArrowUpRight, Check, Fingerprint, History, Layers3 } from 'lucide-react';
import { CHAPTERS } from '../hooks/useJourney.js';

export function JourneyRail({ active, onGo }) {
  const index = CHAPTERS.findIndex(c => c.id === active);
  return <nav className="journey-rail" aria-label="Page chapters"><span className="rail-heading">YOUR JOURNEY</span>{CHAPTERS.map((chapter, i) => <button key={chapter.id} className={active === chapter.id ? 'active' : i < index ? 'visited' : ''} onClick={() => onGo(chapter.id)} aria-label={`Go to ${chapter.label}`} aria-current={active === chapter.id ? 'location' : undefined}><span>{i < index ? <Check size={9} /> : `0${i + 1}`}</span><b>{chapter.short}</b></button>)}</nav>;
}

export function ChapterDivider({ history = false, onContinue }) {
  const Icon = history ? History : Layers3;
  return <div className={`chapter-divider ${history ? 'to-history' : 'to-design'}`}>
    <div className="chapter-thread" aria-hidden="true"><span /><ArrowDown size={15} /><span /></div>
    <div className="chapter-divider-content"><span className="chapter-symbol"><Icon size={26} strokeWidth={1.2} /></span><div><span className="eyebrow">{history ? '02 / FOLLOW THE EVIDENCE' : '03 / UNDERSTAND THE SYSTEM'}</span><h2>{history ? 'A recovery becomes a record.' : 'Behind every action, a boundary.'}</h2><p>{history ? 'Continue into the history of decisions, receipts and outcomes.' : 'See how customer intent, AI proposals and independent checks work together.'}</p></div><button className="button text" onClick={onContinue}>{history ? 'Review the history' : 'Explore the design'} <ArrowUpRight size={16} /></button></div>
  </div>;
}
