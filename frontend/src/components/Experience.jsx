import { lazy, Suspense, useEffect, useMemo, useRef, useState, Component } from 'react';
import { ArrowDown, ArrowUpRight, Check, CreditCard, Box, FileCheck2, MoveUpRight, Sparkles, Play, Pause, RotateCcw, Radio, LoaderCircle, ShieldCheck } from 'lucide-react';

import { projectWorkflow } from '../workflowView.js';

const CrystalScene = lazy(() => import('./CrystalScene.jsx'));
const domains = [
  { label: 'Payment', Icon: CreditCard, heading: 'Find the truth in the receipt.', description: 'A timeout is not proof of a failed payment. Check the authority before taking another action.' },
  { label: 'Inventory', Icon: Box, heading: 'Adapt when the world changes.', description: 'Stock can change between a read and a reservation. Fresh evidence means a better next step.' },
  { label: 'Order', Icon: FileCheck2, heading: 'Keep the original promise.', description: 'The customer’s instructions stay in control. Verify that the final order, money and stock agree.' },
];

class SceneBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch() { this.props.onUnavailable(); }
  render() { return this.state.failed ? null : this.props.children; }
}

export function StaticCrystal({ workflow, onSelect }) {
  return <svg className="static-crystal" viewBox="0 0 700 620" role="group" aria-label="Interactive service map around customer intent">
    <defs>
      <linearGradient id="glass-face" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#c9bfff" stopOpacity=".95" /><stop offset=".5" stopColor="#8b70d7" stopOpacity=".4" /><stop offset="1" stopColor="#2d2469" stopOpacity=".95" /></linearGradient>
      <linearGradient id="glass-edge"><stop stopColor="#e3dbff" /><stop offset="1" stopColor="#9279db" /></linearGradient>
      <linearGradient id="core-gradient" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#9682ee" /><stop offset="1" stopColor="#302366" /></linearGradient>
      <radialGradient id="ground"><stop stopColor="#a98bff" stopOpacity=".14" /><stop offset="1" stopColor="#a98bff" stopOpacity="0" /></radialGradient>
    </defs>
    <ellipse cx="355" cy="514" rx="210" ry="43" fill="url(#ground)" />
    <ellipse cx="350" cy="345" rx="240" ry="82" fill="none" stroke="#978ada" strokeWidth="1.5" transform="rotate(-15 350 345)" />
    <ellipse cx="350" cy="345" rx="251" ry="83" fill="none" stroke="#5ed9e8" strokeWidth="1" transform="rotate(-15 350 345)" />
    <path d="M350 327 232 207M350 327 519 275M350 327 337 459" stroke="#6a81c0" strokeWidth="1.4" />
    <path d="m350 267 62 58-32 75-74-26-16-58Z" fill="url(#core-gradient)" stroke="#9c88e2" /><path d="m350 267-7 86 37 47m-37-47 69-28m-69 28-53-37" stroke="#d1bbff" strokeOpacity=".5" fill="none" />
    {[[149, 127, 0], [455, 178, 1], [255, 396, 2]].map(([x, y, i]) => <g key={i} className="static-module" data-status={workflow.nodes[i].status} role="button" tabIndex={0} aria-label={`Inspect ${workflow.nodes[i].label}`} onClick={() => onSelect(i)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(i); } }} transform={`translate(${x} ${y}) rotate(${i === 1 ? 12 : -12} 70 60)`}>
      <path d="m0 25 37-25 116 14-29 25Z" fill="#dbceff" stroke="#b7a1df" /><path d="m124 39 29-25-3 142-26 21Z" fill="#4b3d81" stroke="#ab92d2" />
      <path d="m0 25 124 14v138L0 160Z" fill="url(#glass-face)" stroke="url(#glass-edge)" strokeWidth="2" />
      <rect x="21" y="56" width="80" height="86" rx="8" fill="#352977" opacity=".7" />
      {i === 0 ? <><circle cx="61" cy="98" r="23" fill="#71def1" /><path d="M62 81v33m9-25c-16-13-26 9-10 10s12 19-7 9" stroke="#225368" strokeWidth="3" fill="none" /></> : i === 1 ? <g fill="#b1a1ff"><rect x="38" y="76" width="20" height="20" rx="3" /><rect x="64" y="76" width="20" height="20" rx="3" /><rect x="38" y="102" width="20" height="20" rx="3" /><rect x="64" y="102" width="20" height="20" rx="3" fill="#71def1" /></g> : <path d="M39 83h45M39 98h45M39 113h26" stroke="#baefff" strokeWidth="6" strokeLinecap="round" />}
      <circle cx="17" cy="43" r="3" fill="#c5bdff" />
    </g>)}
  </svg>;
}

export default function Experience({ reduced, onEnter, recovery, onEvidence }) {
  const section = useRef(null);
  const labels = useRef([]);
  const [progress, setProgress] = useState(0);
  const [selected, setSelected] = useState(0);
  const [ready, setReady] = useState(false);
  const [unavailable, setUnavailable] = useState(false);
  const [cursor, setCursor] = useState(null);
  const [playing, setPlaying] = useState(false);
  const { run, busy, checking, scenario, provider, config, error } = recovery;
  const historicalProvider = run?.provider && !['gemini', 'rehearsal'].includes(run.provider);
  const finished = run && !['running', 'queued'].includes(run.status);
  const workflow = useMemo(() => projectWorkflow(run, cursor), [run, cursor]);
  const node = workflow.nodes[selected];
  const fallback = reduced || unavailable;
  const replayable = finished && workflow.total > 0;
  useEffect(() => { setCursor(null); setPlaying(false); }, [run?.id]);
  useEffect(() => {
    if (workflow.active >= 0) setSelected(workflow.active);
  }, [workflow.event?.id, workflow.active]);
  useEffect(() => {
    if (!playing || !replayable) return;
    if (cursor >= workflow.total - 1) { setPlaying(false); return; }
    const timer = setTimeout(() => setCursor(value => Math.min((value ?? -1) + 1, workflow.total - 1)), 1100);
    return () => clearTimeout(timer);
  }, [playing, cursor, replayable, workflow.total]);
  useEffect(() => {
    let frame = 0;
    const update = () => {
      frame = 0; const rect = section.current?.getBoundingClientRect();
      if (rect) setProgress(Math.max(0, Math.min(1, -rect.top / Math.max(1, rect.height - window.innerHeight + 90))));
    };
    const scroll = () => { if (!frame) frame = requestAnimationFrame(update); };
    window.addEventListener('scroll', scroll, { passive: true }); window.addEventListener('resize', scroll); update();
    return () => { window.removeEventListener('scroll', scroll); window.removeEventListener('resize', scroll); cancelAnimationFrame(frame); };
  }, []);
  const positionLabels = positions => positions.forEach(({ x, y }, i) => {
    if (labels.current[i]) labels.current[i].style.transform = `translate(${x}px, ${y}px) translate(-50%, -50%)`;
  });
  const replay = () => { setCursor(-1); setPlaying(true); };
  const select = index => { setSelected(index); if (playing) setPlaying(false); };
  const chapter = ['verified', 'verifying', 'review', 'error'].includes(workflow.phase) ? 2 : ['recovering', 'replanning'].includes(workflow.phase) ? 1 : 0;
  return <section className="experience-section" id="experience" ref={section} aria-labelledby="hero-title">
    <div className="experience-sticky">
      <div className="hero-copy">
        <div className="eyebrow"><span className="tiny-spark" /> A sustAInX PROJECT · BUILT WITH INTENT</div>
        <h1 id="hero-title">Every promise.<br />Back in<br /><span>alignment.</span></h1>
        <p className="hero-description">For operations teams recovering interrupted orders. Reconcile payment, stock and the customer’s request—with evidence at every step.</p>
        <div className="hero-actions"><button id="watch-recovery" className="button primary hero-cta" onClick={recovery.start} disabled={busy || checking || !config || !scenario}>{busy ? <LoaderCircle className="spin" size={17} /> : <Play size={16} fill="currentColor" />} {busy ? 'Recovery in progress' : run ? 'Start a new recovery' : 'Watch recovery'} <ArrowUpRight size={18} /></button><button className="button text hero-desk-link" onClick={onEnter}>Open recovery desk <ArrowUpRight size={15} /></button></div>
        <div className="hero-scenario"><span className="scenario-caption">CURRENT INCIDENT</span><strong>{scenario?.name || 'Loading the workspace…'}</strong><span>{historicalProvider ? `${run.provider} · historical audit record` : provider === 'rehearsal' ? 'Rehearsal · deterministic planner · no AI calls' : 'Gemini · live model proposals'}</span></div>
        {error && <p role="alert" className="hero-error">{error}</p>}
        <div className="hero-signature"><span className="signature-icon"><Sparkles size={16} /></span><span>{historicalProvider ? 'Inspect the recorded evidence.' : provider === 'rehearsal' ? 'Built for Gemini.' : 'Reason with Gemini.'}<br /><strong>Verify with code.</strong></span><span className="signature-rule" /><span className="signature-note">Three services.<br />One customer promise.</span></div>
      </div>
      <div className="sculpture-panel" data-renderer={fallback ? 'static' : ready ? 'webgl' : 'loading'} data-phase={workflow.phase} data-aligned={workflow.aligned}>
        <div className="scene-topline"><span><Radio size={12} /> THE RECOVERY CORE</span><span>{fallback ? 'SELECT A SERVICE' : 'CLICK A CRYSTAL · DRAG TO ROTATE'} <MoveUpRight size={11} /></span></div>
        <div className="scene-viewport">
          <div className="scene-grid" aria-hidden="true" /><div className="scene-glow" aria-hidden="true" />
          <div className="scene-area">
            {(!ready || fallback) && <StaticCrystal workflow={workflow} onSelect={select} />}
            {!fallback && <SceneBoundary onUnavailable={() => setUnavailable(true)}><Suspense fallback={null}><CrystalScene progress={progress} selected={selected} workflow={workflow} onSelect={select} onPositions={positionLabels} onReady={() => setReady(true)} onUnavailable={() => setUnavailable(true)} /></Suspense></SceneBoundary>}
            {ready && !fallback && <div className="node-labels">{workflow.nodes.map((n, i) => <button key={n.label} ref={el => { labels.current[i] = el; }} className={`node-hotspot ${n.status} ${selected === i ? 'selected' : ''}`} onClick={() => select(i)} aria-label={`Inspect ${n.label} crystal`} aria-pressed={selected === i}><span />{n.label}<ArrowUpRight size={9} /></button>)}</div>}
          </div>
          <div className="intent-tag"><span className="intent-mark"><ShieldCheck size={12} /></span> Customer intent <span>AT THE CORE</span></div>
        </div>
        <div className="core-console">
          <div className={`phase-strip ${workflow.phase}`} role="status"><span className="phase-dot" /><strong id="core-phase">{busy && !run ? 'Starting recovery…' : workflow.phaseLabel}</strong><span>{workflow.isReplay ? 'REPLAY' : busy ? 'RUNNING' : run ? 'THIS RUN' : 'READY'}</span></div>
          <div className="domain-selector" aria-label="Explore a service">{domains.map(({ label, Icon }, i) => <button key={label} className={`domain-chip ${selected === i ? 'selected' : ''}`} data-status={workflow.nodes[i].status} aria-pressed={selected === i} onClick={() => select(i)}><Icon size={14} /><span>{label}</span><small>0{i + 1}</small></button>)}</div>
          <div className="service-inspector" data-service={node.label} data-status={node.status}>
            <div className="inspector-heading"><span>{node.label.toUpperCase()} / OBSERVED STATE</span><span className={`node-status ${node.status}`}>{node.status === 'blocked' ? 'Needs fresh evidence' : node.status}</span></div>
            <strong id="service-value">{node.value}</strong><p>{node.detail}</p>
            <div className="inspector-footer"><div className="inspector-facts">{node.facts.length ? node.facts.map(([label, value]) => <span key={label}>{label} <b>{value}</b></span>) : <span>Start a recovery to collect evidence.</span>}</div>{node.evidenceId && <button className="evidence-link" onClick={() => { setPlaying(false); onEvidence(node.evidenceId); }}>Open {node.evidenceId} <ArrowUpRight size={12} /></button>}</div>
            {node.actionReceipt && <span className="action-receipt">Execution receipt · {node.actionReceipt}</span>}
          </div>
          <div className="replay-panel">
            <div className="replay-controls"><button id="replay-run" disabled={!replayable} onClick={playing ? () => setPlaying(false) : cursor !== null && !workflow.atEnd ? () => setPlaying(true) : replay}>{playing ? <Pause size={13} /> : <Play size={13} />} {playing ? 'Pause replay' : cursor !== null && !workflow.atEnd ? 'Resume replay' : 'Replay recovery'}</button>{workflow.isReplay && <button className="latest-button" onClick={() => { setCursor(null); setPlaying(false); }}><RotateCcw size={11} /> Latest</button>}<span>{workflow.isReplay ? 'Recorded events · no model calls' : workflow.total ? `${workflow.total} recorded events` : 'Your recovery will appear here'}</span></div>
            {replayable && <><input id="replay-cursor" aria-label="Recorded recovery event" type="range" min="-1" max={workflow.total - 1} step="1" value={workflow.index} aria-valuetext={workflow.event ? `${workflow.index + 1} of ${workflow.total}: ${workflow.event.title}` : 'Before observations'} onChange={e => { setPlaying(false); setCursor(Number(e.target.value)); }} /><div className={`replay-caption ${workflow.event?.kind || ''}`}><span>{String(workflow.index + 1).padStart(2, '0')} / {String(workflow.total).padStart(2, '0')}</span><p>{workflow.event?.title || 'Before the first observation'}</p></div></>}
          </div>
        </div>
      </div>
      <div className="experience-bottom"><button className="scroll-cue" onClick={onEnter}><ArrowDown size={16} /><span>EXPLORE THE RECOVERY DESK</span></button><div className="chapter-track" aria-label="Recovery stage">{['Observe', 'Adapt', 'Verify'].map((x, i) => <div className={chapter === i ? 'active' : ''} key={x}><span>0{i + 1}</span>{x}<i /></div>)}</div><span className="illustration-note">Synthetic services<br />Every state backed by the audit</span></div>
    </div>
  </section>;
}

