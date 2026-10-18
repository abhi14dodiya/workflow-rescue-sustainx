import { useCallback, useEffect, useRef, useState } from 'react';

function readHistory() {
  try {
    const data = JSON.parse(sessionStorage.getItem('workflow-rescue-history') || '[]');
    return Array.isArray(data) ? data.filter(x => x && typeof x.id === 'string').slice(0, 25) : [];
  } catch { return []; }
}

export function useRecovery() {
  const [config, setConfig] = useState(null);
  const [scenarios, setScenarios] = useState([]);
  const [scenarioId, setScenarioId] = useState('stock-race');
  const [customIncident, setCustomIncident] = useState(null);
  const [editing, setEditing] = useState(false);
  const [provider, setProvider] = useState('rehearsal');
  const [run, setRun] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [history, setHistory] = useState(readHistory);
  const [connection, setConnection] = useState(null);
  const [checking, setChecking] = useState(false);
  const token = useRef('');
  const generation = useRef(0);
  const timer = useRef(null);
  const mounted = useRef(true);

  const request = useCallback(async (path, options = {}) => {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (token.current) headers['X-Demo-Token'] = token.current;
    const response = await fetch(path, { ...options, headers });
    let data;
    try { data = await response.json(); }
    catch { throw new Error(`The application returned HTTP ${response.status} without a readable response.`); }
    if (!response.ok) throw new Error(data.error ? `${data.error.code}: ${data.error.message}` : typeof data.detail === 'string' ? data.detail : `Request failed (HTTP ${response.status}).`);
    return data;
  }, []);

  useEffect(() => {
    mounted.current = true;
    const controller = new AbortController();
    Promise.all([request('/api/config', { signal: controller.signal }), request('/api/scenarios', { signal: controller.signal })])
      .then(([configuration, fixtures]) => { setConfig(configuration); setScenarios(fixtures); setProvider(configuration.default_provider || 'rehearsal'); })
      .catch(e => { if (e.name !== 'AbortError') setError(`Unable to load the workspace: ${e.message}`); });
    return () => { mounted.current = false; controller.abort(); generation.current++; clearTimeout(timer.current); };
  }, [request]);

  const remember = useCallback(record => {
    const { id, scenario_id, provider, status, created_at } = record;
    setHistory(previous => {
      const next = [{ id, scenario_id, provider, status, created_at }, ...previous.filter(x => x.id !== id)].slice(0, 25);
      try { sessionStorage.setItem('workflow-rescue-history', JSON.stringify(next)); } catch { /* in-memory history remains available */ }
      return next;
    });
  }, []);

  const poll = useCallback(async (id, epoch) => {
    try {
      const record = await request(`/api/runs/${encodeURIComponent(id)}`);
      if (generation.current !== epoch || !mounted.current) return;
      setRun(record); remember(record);
      if (['queued', 'running'].includes(record.status)) timer.current = setTimeout(() => poll(id, epoch), 450);
      else setBusy(false);
    } catch (e) {
      if (generation.current !== epoch || !mounted.current) return;
      setError(e.message); setBusy(false);
    }
  }, [request, remember]);

  const reset = useCallback(() => {
    generation.current++; clearTimeout(timer.current);
    setRun(null); setError(''); setConnection(null);
  }, []);
  const changeScenario = value => { if (!busy && !editing) { reset(); setScenarioId(value); } };
  const changeProvider = value => { if (!busy && !checking && !editing) { reset(); setProvider(value); } };
  const previewIncident = data => request('/api/incidents/preview', { method: 'POST', body: JSON.stringify(data) });
  const applyIncident = async data => {
    if (busy || checking || editing) throw new Error('Wait for the current request to finish.');
    setEditing(true);
    try {
      reset();
      const epoch = generation.current;
      const preview = await previewIncident(data);
      if (generation.current !== epoch || !mounted.current) return;
      setScenarios(previous => [...previous.filter(s => s.id !== 'custom'), preview.scenario]);
      setCustomIncident(preview.input); setScenarioId('custom');
    } finally { setEditing(false); }
  };

  const start = async () => {
    if (busy || checking || editing || !config) return;
    reset(); setBusy(true);
    const epoch = generation.current;
    try {
      const created = await request('/api/runs', { method: 'POST', body: JSON.stringify({ scenario_id: scenarioId, provider, ...(scenarioId === 'custom' ? { custom_incident: customIncident } : {}) }) });
      if (generation.current !== epoch || !mounted.current) return;
      setRun({ ...created, provider, events: [], checks: [], metrics: {} });
      await poll(created.id, epoch);
    } catch (e) {
      if (generation.current !== epoch || !mounted.current) return;
      setError(e.message); setBusy(false);
    }
  };

  const openHistory = async id => {
    if (busy) { setError('Wait for the current recovery to finish before opening another run.'); return false; }
    const epoch = ++generation.current;
    clearTimeout(timer.current);
    try {
      const record = await request(`/api/runs/${encodeURIComponent(id)}`);
      // A new incident/provider selection supersedes an older history fetch.
      if (generation.current !== epoch || !mounted.current) return false;
      reset();
      if (record.scenario_id === 'custom' && record.incident && record.custom_incident) {
        setScenarios(previous => [...previous.filter(s => s.id !== 'custom'), record.incident]);
        setCustomIncident(record.custom_incident);
      }
      setScenarioId(record.scenario_id); setProvider(record.provider); setRun(record);
      if (['queued', 'running'].includes(record.status)) { setBusy(true); await poll(id, generation.current); }
      return true;
    } catch (e) { if (generation.current === epoch && mounted.current) setError(e.message); return false; }
  };

  const testConnection = async () => {
    if (checking || busy) return;
    setChecking(true); setConnection(null);
    try {
      const result = await request('/api/provider-check', { method: 'POST', body: JSON.stringify({ provider }) });
      setConnection({ ok: true, message: result.message });
    } catch (e) { setConnection({ ok: false, message: e.message }); }
    finally { setChecking(false); }
  };

  return { config, scenarios, scenarioId, scenario: scenarios.find(s => s.id === scenarioId), provider, run, busy, error, history,
    checking, editing, connection, changeScenario, changeProvider, start, openHistory, testConnection, previewIncident, applyIncident, setToken: value => { token.current = value; },
    exportAudit: () => { if (run?.id) window.location.assign(`/api/runs/${encodeURIComponent(run.id)}/export`); } };
}
