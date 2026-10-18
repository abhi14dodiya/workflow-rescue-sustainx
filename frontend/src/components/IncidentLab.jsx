import { useState } from 'react';
import { FlaskConical, Upload, ArrowDownToLine } from 'lucide-react';
import './incident-lab.css';

const initial = {
  customer_note: 'Keep the original items and price. A delay of up to two days is approved. Do not charge again.',
  available: 2, incoming_available: 10, alternative_available: 6, incoming_days: 1,
  max_delay_days: 2, allow_delay: true, allow_substitution: false,
  cancel_requested: false, payment_unknown: false, shipped: false, race: true,
};

export default function IncidentLab({ recovery }) {
  const [values, setValues] = useState(initial);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const update = (key, value) => setValues(previous => ({ ...previous, [key]: value }));
  const upload = async event => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      if (file.size > 12000) throw new Error('Choose an incident JSON file smaller than 12 KB.');
      const data = JSON.parse(await file.text());
      if (!data || Array.isArray(data) || typeof data !== 'object') throw new Error('The file must contain one incident object.');
      const preview = await recovery.previewIncident(data);
      setValues(preview.input); setError('');
    } catch (e) { setError(e.message); }
    event.target.value = '';
  };
  const apply = async event => {
    event.preventDefault(); setLoading(true); setError('');
    try { await recovery.applyIncident(values); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };
  return <details className="incident-lab" id="incident-lab">
    <summary><FlaskConical size={17} /><span>Create or import an incident<small>Change the evidence. Challenge the recovery.</small></span></summary>
    <form onSubmit={apply}>
      <p>Build a new simulation for the same two-kit, $498 order. These settings represent simulated service evidence and explicit demo permissions. Use synthetic data only.</p>
      <fieldset disabled={recovery.busy || loading}>
        <label className="lab-note" htmlFor="lab-note">Customer note<textarea id="lab-note" value={values.customer_note} maxLength={1000} required onChange={e => update('customer_note', e.target.value)} /></label>
        <div className="lab-fields">{[
          ['available', 'Original units available', 100], ['incoming_available', 'Incoming original units', 100],
          ['alternative_available', 'Alternative units available', 100], ['incoming_days', 'Incoming stock in days', 30],
          ['max_delay_days', 'Maximum approved delay', 30],
        ].map(([key, label, max]) => <label key={key} htmlFor={`lab-${key}`}>{label}<input id={`lab-${key}`} type="number" min="0" max={max} required value={values[key]} onChange={e => update(key, e.target.value === '' ? '' : Number(e.target.value))} /></label>)}</div>
        <div className="lab-checks">{[
          ['allow_delay', 'Customer approves a delay'], ['allow_substitution', 'Customer approves Field Kit Plus at the same price'],
          ['cancel_requested', 'Customer requests cancellation'], ['payment_unknown', 'Payment authority is unavailable'],
          ['shipped', 'Order has already shipped'], ['race', 'Stock changes during reservation'],
        ].map(([key, label]) => <label key={key}><input id={`lab-${key}`} type="checkbox" checked={values[key]} onChange={e => update(key, e.target.checked)} />{label}</label>)}</div>
        <p className="lab-boundary">The checkboxes define demo permissions. The note cannot authorize another charge or override the execution checks.</p>
        <div className="lab-actions"><button className="button primary small" id="apply-incident" type="submit">{loading ? 'Validating…' : 'Use this incident'}</button><a href="/api/incidents/template" download="workflow-rescue-incident.json"><ArrowDownToLine size={14} />JSON template</a><label className="lab-upload"><Upload size={14} /> Import JSON<input type="file" accept=".json,application/json" aria-label="Import incident JSON" onChange={upload} /></label></div>
      </fieldset>
      {error && <p role="alert" className="error-banner">{error}</p>}
      {recovery.scenarioId === 'custom' && <p className="lab-ready" role="status">Custom incident selected. Review the mandate below, then start a fresh recovery.</p>}
    </form>
  </details>;
}
