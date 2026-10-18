import { useEffect, useRef, useState } from 'react';
import IncidentLab from './IncidentLab.jsx';
import { Activity, ArrowDownToLine, ArrowRight, ArrowUpRight, BadgeCheck, Ban, Box, Check, ChevronDown, ChevronRight, CircleHelp, Clock3, CreditCard, FileCheck2, Fingerprint, Layers3, LoaderCircle, LockKeyhole, MessageSquareText, ReceiptText, RotateCcw, Search, ShieldCheck, Sparkles, TriangleAlert, Undo2, X } from 'lucide-react';

const human = value => String(value || '').replaceAll('_', ' ');
const serviceIcons = { inspect_payment: CreditCard, inspect_inventory: Box, inspect_dispatch: FileCheck2 };
const eventIcons = { wait: Clock3, preflight: Search, incident: Activity, decision: Sparkles, evidence: Search, guard: ShieldCheck, change: RotateCcw, review: CircleHelp, action: Check, verification: BadgeCheck, error: X };
const terminal = run => run && !['running', 'queued'].includes(run.status);

function Status({ run, busy }) {
  const label = { queued: 'Starting', running: run?.phase || 'Running', completed: 'Verified', review: 'Needs review', error: 'Connection error', failed: 'Issue detected' }[run?.status] || (busy ? 'Starting' : 'Ready');
  return <span className={`status-pill ${run?.status || 'neutral'}`} id="run-status"><span />{label}</span>;
}

function ServiceMap({ run }) {
  const state = run?.state;
  const observed = state?.evidence || [];
  const activeTool = run?.events?.filter(x => x.kind === 'decision').at(-1)?.action;
  const completed = run?.status === 'completed';
  const nodes = [
    { key: 'payment', Icon: CreditCard, title: 'Payment', value: { captured: 'Captured once', refunded: 'Refunded', unknown: 'Unknown' }[state?.payment?.status] || 'Unverified', detail: state?.payment?.receipt || 'Find the receipt', tool: 'inspect_payment' },
    { key: 'stock', Icon: Box, title: 'Inventory', value: state?.inventory?.reserved_quantity ? `${state.inventory.reserved_quantity} units reserved` : state?.outcome === 'cancelled' ? 'Released' : 'Not reserved', detail: state?.inventory?.reservation_source === 'incoming_available' ? `Original item · ${state.order.delivery_days} day delay` : state ? `Stock version ${state.inventory.version}` : 'Check the stock', tool: 'inspect_inventory' },
    { key: 'outcome', Icon: FileCheck2, title: 'Order', value: run?.status === 'error' ? 'Run stopped' : run?.status === 'failed' ? 'Issue detected' : { recovered: 'Order recovered', cancelled: 'Order cancelled', escalated: 'Operator review' }[state?.outcome] || 'Interrupted', detail: completed ? 'Verified against the ledgers' : state?.outcome === 'escalated' ? 'A person decides what’s next' : 'Preserve the promise', tool: 'inspect_dispatch' },
  ];
  return <div className={`service-map ${completed ? 'aligned' : ''}`} aria-label="Observed business states">
    {nodes.map(({ key, Icon, title, value, detail, tool }, i) => <div key={key} className={`service-node ${observed.some(e => e.tool === tool) ? 'observed' : ''} ${run?.status === 'running' && activeTool === tool ? 'active' : ''}`}>
      <div className="service-top"><span className="service-symbol"><Icon size={19} strokeWidth={1.6} /></span><span>{title}</span><small>0{i + 1}</small></div>
      <strong id={`metric-${key === 'outcome' ? 'outcome' : key}`}>{value}</strong><p>{detail}</p>
      {i !== 2 && <span className="service-connector" aria-hidden="true"><ArrowRight size={12} /></span>}
    </div>)}
  </div>;
}

function CustomerCard({ scenario }) {
  const p = scenario.policy;
  const chips = p.cancel_requested ? [[Undo2, 'Cancel & refund', true], [Ban, 'Do not dispatch', true]] : [
    [p.allow_substitution ? Check : Ban, p.allow_substitution ? 'Field Kit Plus approved' : 'No substitutions', !p.allow_substitution],
    [Clock3, p.allow_delay ? `Up to ${p.max_delay_days} days late` : 'No delivery delay', !p.allow_delay],
  ];
  chips.push([LockKeyhole, 'No additional charge', false]);
  return <section className="card customer-card"><div className="card-heading"><h3>The promise to preserve</h3><MessageSquareText size={17} /></div>
    <div className="customer"><span className="customer-avatar">{scenario.customer.split(' ').map(x => x[0]).join('')}</span><div><strong>{scenario.customer}</strong><span>{scenario.company}</span></div><span className="tiny-label">ORDER NOTE</span></div>
    <blockquote>{scenario.message}</blockquote>
    <div className="mandate"><div className="mandate-heading"><span>Approved customer mandate</span><ShieldCheck size={14} /></div><div className="policy-chips">{chips.map(([Icon, label, restriction]) => <span className={`policy-chip ${restriction ? 'restrict' : ''}`} key={label}><Icon size={12} />{label}</span>)}</div><p>Reviewed scenario permissions. Enforced outside the model.</p></div>
  </section>;
}

function Evidence({ records, focus }) {
  const [filter, setFilter] = useState('all');
  useEffect(() => { if (focus) { setFilter('all'); requestAnimationFrame(() => { const node = document.getElementById(`evidence-${focus.id}`); if (node) { node.open = true; node.querySelector('summary')?.focus({ preventScroll: true }); node.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); } }); } }, [focus]);
  const visible = filter === 'all' ? records : records.filter(e => e.tool === filter);
  return <section className="card evidence-card"><div className="card-heading"><h3>Evidence, not assumptions</h3><span id="evidence-count" className="count-pill">{records.length}</span></div>
    {records.length > 0 && <div className="evidence-filters" aria-label="Filter service evidence">{[['all', 'All'], ['inspect_payment', 'Payment'], ['inspect_inventory', 'Stock'], ['inspect_dispatch', 'Dispatch']].map(([key, name]) => <button className={filter === key ? 'active' : ''} key={key} aria-pressed={filter === key} onClick={() => setFilter(key)}>{name}</button>)}</div>}
    <div className="evidence-list" id="evidence-list">{!records.length ? <div className="empty-evidence"><ReceiptText size={22} strokeWidth={1.3} /><div><strong>Start with what you can prove.</strong><p>Authoritative receipts appear here during recovery.</p></div></div> : visible.map(e => {
      const Icon = serviceIcons[e.tool] || FileCheck2;
      const data = e.data;
      const summary = e.tool === 'inspect_payment' ? data.status === 'unknown' ? 'Unknown · no authoritative receipt' : `${data.receipt} · ${human(data.status)} · ${data.charge_count} charge` : e.tool === 'inspect_inventory' ? `v${data.version} · ${data.available} available · ${data.reserved_quantity} reserved` : human(data.status);
      return <details className="evidence-item" key={e.id} id={`evidence-${e.id}`}><summary><span className="evidence-symbol"><Icon size={16} /></span><div><strong>{e.source.split(' · ')[0]}</strong><small>{summary}</small></div><span className="evidence-id">{e.id}</span><ChevronDown size={12} /></summary><pre>{JSON.stringify(data, null, 2)}</pre></details>;
    })}</div>
  </section>;
}

function Trail({ run, onEvidence }) {
  const ref = useRef(null);
  const previousCount = useRef(0);
  useEffect(() => {
    const node = ref.current;
    if (node && (run?.events?.length || 0) !== previousCount.current) {
      if (node.scrollHeight - node.scrollTop - node.clientHeight < 240 || previousCount.current === 0) node.scrollTo({ top: node.scrollHeight, behavior: 'smooth' });
      previousCount.current = run?.events?.length || 0;
    }
  }, [run?.events?.length]);
  const events = run?.events || [];
  return <div className="trail" id="trail" ref={ref} role="log" aria-label="Recovery activity" aria-live="polite" aria-relevant="additions">
    {!events.length ? <div className="trail-empty"><div className="empty-core"><Layers3 size={31} strokeWidth={1.1} /><span /><span /></div><h3>Bring the pieces back together.</h3><p>Inspect what happened, adapt to what changed,<br />and verify the promise is kept.</p><div className="three-steps"><span><i>01</i> Observe</span><ChevronRight size={12} /><span><i>02</i> Adapt</span><ChevronRight size={12} /><span><i>03</i> Verify</span></div></div> : events.map(e => {
      const Icon = eventIcons[e.kind] || Activity;
      const ids = e.evidence_ids || (e.evidence_id ? [e.evidence_id] : []);
      return <article className={`trail-event ${e.kind}`} key={e.id}><span className="event-icon"><Icon size={13} /></span><div className="event-content"><div className="event-title"><strong>{e.title}</strong><time>{new Date(e.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</time></div><p>{e.detail}</p>{ids.length > 0 && <div className="event-refs">{ids.map(id => <button className="event-ref" key={id} onClick={() => onEvidence(id)}>{id}<ArrowUpRight size={9} /></button>)}</div>}</div></article>;
    })}
  </div>;
}

function Results({ run, exportAudit }) {
  const completed = run.status === 'completed';
  const recovered = completed && run.state?.outcome === 'recovered';
  const cancelled = completed && run.state?.outcome === 'cancelled';
  const title = recovered ? 'The promise is intact.' : cancelled ? 'Cancellation, reconciled.' : run.status === 'failed' ? 'An issue needs your attention.' : run.status === 'error' ? 'The model stopped. Review the state.' : 'Knowing when to stop matters.';
  const description = recovered ? 'The existing payment, permitted reservation and confirmed order agree. The checks below read the service state directly.' : cancelled ? 'The payment is refunded, the order is cancelled, and no inventory remains reserved.' : 'The evidence does not establish a completed recovery. An operator must review the remaining uncertainty.';
  const baseline = run.baseline;
  return <section id="results" className={`results-card ${completed ? 'success' : 'needs-attention'}`} aria-labelledby="result-title">
    <div className="results-heading"><div className="result-heading-copy"><span className="result-seal">{completed ? <BadgeCheck size={25} /> : <CircleHelp size={25} />}</span><div><div className="eyebrow">INDEPENDENT VERIFICATION</div><h3 id="result-title">{title}</h3></div></div><button className="button secondary small" id="export-result" onClick={exportAudit}><ArrowDownToLine size={14} /> Export audit</button></div>
    <p className="result-description">{description}</p>
    <div className="checks-grid" id="checks">{run.checks?.map(c => <div className={`check ${c.status}`} key={c.id}><div className="check-heading">{c.status === 'pass' ? <Check size={15} /> : c.status === 'fail' ? <X size={15} /> : <TriangleAlert size={15} />}<strong>{c.label}</strong></div><p>{c.detail}</p><span className="sr-only">Status: {c.status}</span></div>)}</div>
    <div className="comparison"><div><span className="tiny-label">FIXED WORKFLOW WITH GUARDS</span><strong id="baseline-outcome">{human(baseline?.outcome) || 'Not available'}</strong><p>{baseline?.steps || 0} steps · {baseline?.safety_issues || 0} safety issues</p></div><div><span className="tiny-label">{run.provider === 'rehearsal' ? 'ADAPTIVE REHEARSAL · NO AI' : `${run.provider.toUpperCase()} · THIS RUN`}</span><strong id="current-outcome">{run.status === 'error' ? 'Model unavailable' : run.status === 'failed' ? 'Verification failed' : human(run.state?.outcome)}</strong><p id="current-detail">{run.metrics?.steps || 0} steps · {run.metrics?.blocked_proposals || 0} blocked proposal(s) · {run.metrics?.calls || 0} model call(s).</p></div><p className="comparison-note">Same fixture. Same execution rules.<br />A broader rules engine can also solve these examples. Live AI benefit still needs measurement.</p></div>
    <div className="run-metrics"><span>{run.model}</span><span><Clock3 size={11} />{((run.metrics?.elapsed_ms || 0) / 1000).toFixed(1)}s elapsed</span><span>{run.metrics?.input_tokens || 0} input / {run.metrics?.output_tokens || 0} output tokens</span><span>Simulated business services</span></div>
  </section>;
}

export default function RecoveryDesk({ recovery, focus, onEvidence }) {
  const { scenario, config, scenarios, provider, run, busy, checking, error, connection } = recovery;
  const selectedProvider = config?.providers.find(p => p.id === provider);
  if (!scenario) return <section id="recovery" className="desk-section"><p role="status">{error || 'Preparing the recovery workspace…'}</p></section>;
  return <section id="recovery" className="desk-section" aria-labelledby="desk-title">
    <div className="section-heading"><div><div className="eyebrow"><span className="section-index">01</span> THE RECOVERY DESK</div><h2 id="desk-title">A real workflow.<br className="mobile-break" /> A better next step.</h2><p>Every order is a promise. Let’s recover this one.</p></div><span className="environment-label"><span className="status-dot amber" /> Simulated business services</span></div>
    <ol className="workspace-guide" aria-label="Recovery guide"><li><span>1</span><div><strong>Choose an incident</strong><small>Read the customer’s request</small></div></li><li><span>2</span><div><strong>Investigate & recover</strong><small>Follow the evidence and decisions</small></div></li><li><span>3</span><div><strong>Verify the outcome</strong><small>Inspect, replay or export the audit</small></div></li></ol>
    <IncidentLab recovery={recovery} />
    <div className="workspace-shell">
      <div className="workspace-toolbar"><div className="workspace-identity"><span className="workspace-emblem">N</span><div><strong>Northstar</strong><span>Operations workspace</span></div><ChevronRight size={15} /><span className="incident-id">ORD-1042</span></div><button className="button secondary small" id="export-top" disabled={!terminal(run)} onClick={recovery.exportAudit}><ArrowDownToLine size={13} /> Export audit</button></div>
      <div className="case-selector"><label htmlFor="scenario-select">Choose an incident</label><div className="select-wrap"><select id="scenario-select" value={recovery.scenarioId} disabled={busy || recovery.editing} onChange={e => recovery.changeScenario(e.target.value)}>{scenarios.map(s => <option value={s.id} key={s.id}>{s.name}</option>)}</select><ChevronDown size={14} /></div><span className="scenario-tag">{scenario.tag}</span></div>
      <div className="incident-heading"><div><span className="incident-kicker"><span /> {run?.status === 'completed' ? 'RESOLVED IN THIS RUN' : 'INTERRUPTED WORKFLOW'}</span><h3>{scenario.name}</h3><p>{scenario.summary}</p></div><div className="order-value"><span>ORIGINAL ORDER</span><strong>$498<small>.00</small></strong><p>2 × Field Kit</p></div></div>
      <ServiceMap run={run} />
      {error && <div id="error-banner" className="error-banner" role="alert"><TriangleAlert size={17} /><p>{error}</p></div>}
      <div className="work-grid"><div className="context-column"><CustomerCard scenario={scenario} /><Evidence records={run?.state?.evidence || []} focus={focus} /></div>
        <section className="card recovery-card"><div className="card-heading"><h3><span className="small-spark"><Sparkles size={15} /></span> Recovery trail</h3><Status run={run} busy={busy} /></div>
          <div className="provider-bar"><div><Sparkles size={15} /><div className="select-wrap"><label className="sr-only" htmlFor="provider-select">Recovery planner</label><select id="provider-select" value={provider} disabled={busy || checking || recovery.editing} onChange={e => recovery.changeProvider(e.target.value)}>{config.providers.map(p => <option key={p.id} value={p.id} disabled={!p.configured}>{p.label}{p.configured ? '' : ' · setup needed'}</option>)}</select><ChevronDown size={12} /></div></div><button className="text-button" id="connection-test" disabled={busy || checking || recovery.editing} onClick={recovery.testConnection}>{checking ? <><LoaderCircle className="spin" size={12} /> Checking</> : <>Test connection <ArrowUpRight size={11} /></>}</button></div>
          <p className="provider-notice" id="provider-notice">{provider === 'rehearsal' ? 'Rehearsal uses a deterministic planner. No AI model is called.' : ['openai', 'azure'].includes(provider) ? `${selectedProvider?.label} · ${selectedProvider?.model}. Live development run; Google AI validation is separate.` : `${selectedProvider?.model} · live proposals; independent execution checks.`}</p>
          {connection && <div className={`connection-result ${connection.ok ? '' : 'bad'}`} role="status">{connection.message}</div>}
          <Trail run={run} onEvidence={onEvidence} />
          <div className="run-controls"><button id="start-run" className="button primary" disabled={busy || checking || recovery.editing} onClick={recovery.start}><span>{busy ? 'Recovering the workflow…' : run ? 'Run a fresh simulation' : 'Investigate & recover'}</span>{busy ? <LoaderCircle size={16} className="spin" /> : run ? <RotateCcw size={16} /> : <ArrowUpRight size={17} />}</button><p><Fingerprint size={11} /> A fresh, isolated simulation starts with every run.</p></div>
        </section>
      </div>
      {terminal(run) && <Results run={run} exportAudit={recovery.exportAudit} />}
    </div>
  </section>;
}
