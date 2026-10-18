// A read-only projection of the recorded audit. No model calls and no mutations.
const TOOLS = ['inspect_payment', 'inspect_inventory', 'inspect_dispatch'];
export const PHASE_LABELS = { idle: 'Awaiting evidence', investigating: 'Inspecting the services', replanning: 'Stock changed · replanning', recovering: 'Applying the recovery', verifying: 'Checking the outcome', verified: 'Outcome verified', review: 'Operator review required', error: 'Recovery stopped' };

function serviceFor(action = '') {
  if (action.includes('payment')) return 0;
  if (action.includes('inventory') || action.startsWith('reserve_')) return 1;
  return 2;
}

export function projectWorkflow(run, cursor = null) {
  const all = run?.events || [];
  const end = cursor === null ? all.length - 1 : Math.max(-1, Math.min(cursor, all.length - 1));
  const events = all.slice(0, end + 1);
  const evidence = run?.state?.evidence || [];
  const nodes = [
    { label: 'Payment', status: 'waiting', value: 'Unverified', detail: 'The payment request timed out. Inspect the authoritative receipt before taking another action.', evidenceId: null, facts: [] },
    { label: 'Inventory', status: 'waiting', value: 'Reservation expired', detail: 'The original reservation expired. Inspect stock and the current version before reserving again.', evidenceId: null, facts: [] },
    { label: 'Order', status: 'waiting', value: 'Interrupted', detail: 'The order is incomplete. Check dispatch and preserve the customer’s approved instructions.', evidenceId: null, facts: [] },
  ];
  let phase = events.length ? 'investigating' : 'idle', active = -1, stale = false;
  const applyObservation = (obs, data) => {
    const index = TOOLS.indexOf(obs?.tool);
    if (index < 0) return;
    const node = nodes[index];
    node.evidenceId = obs.id; node.status = data.status === 'unknown' ? 'review' : 'observed';
    if (index === 0) {
      node.value = data.status === 'unknown' ? 'Payment unknown' : data.status === 'refunded' ? 'Refund confirmed' : 'Captured once';
      node.detail = data.status === 'unknown' ? 'The payment authority is unavailable. Unknown does not mean failed; a second charge is not permitted.' : data.status === 'refunded' ? 'The original charge has been refunded. Verify the cancellation and released reservation before closing the incident.' : `${data.receipt} confirms ${data.charge_count} charge. Reuse the existing payment; do not charge again.`;
      node.facts = data.status === 'unknown' ? [['Authority', 'Unavailable']] : [['Captured', `$${(data.captured_cents / 100).toFixed(2)}`], ['Refunded', `$${(data.refunded_cents / 100).toFixed(2)}`]];
    } else if (index === 1) {
      node.value = data.reserved_quantity ? `${data.reserved_quantity} units reserved` : `${data.available} original units available`;
      node.detail = data.reserved_quantity ? 'A permitted reservation now backs the order. Check the receipt and the independently verified outcome.' : `Inventory version ${data.version}. Confirmed incoming stock arrives in ${data.incoming_days} day(s); the customer’s permission determines whether that is acceptable.`;
      node.facts = [['Stock version', String(data.version)], ['Reserved', String(data.reserved_quantity)]];
      stale = false;
    } else {
      node.value = data.status === 'shipped' ? 'Already dispatched' : 'Not yet dispatched';
      node.detail = data.status === 'shipped' ? 'Shipment is irreversible in this prototype. An operator must arrange a return before a refund.' : 'Dispatch has not happened. Recovery still needs a permitted reservation or confirmed cancellation.';
      node.status = data.status === 'shipped' ? 'review' : 'observed';
      node.facts = [['Dispatch', data.status.replaceAll('_', ' ')]];
    }
  };
  for (const event of events) {
    if (event.kind === 'decision') {
      active = serviceFor(event.action);
      phase = event.action?.startsWith('inspect_') ? stale ? 'replanning' : 'investigating' : event.action === 'verify' ? 'verifying' : 'recovering';
    } else if (event.kind === 'evidence') {
      const obs = evidence.find(e => e.id === event.evidence_id);
      applyObservation(obs, event.data || obs?.data || {});
    } else if (event.kind === 'guard' || event.kind === 'change') {
      if (event.code === 'STALE_STOCK' || event.kind === 'change') {
        stale = true; active = 1; phase = 'replanning';
        nodes[1].status = 'blocked'; nodes[1].value = 'Stock snapshot is stale';
        nodes[1].detail = 'The controller rejected the reservation because stock changed after the read. Obtain fresh evidence before choosing a new recovery.';
      } else {
        phase = 'recovering';
        if (active >= 0) { nodes[active].status = 'blocked'; nodes[active].detail = event.detail; }
      }
    } else if (event.kind === 'action') {
      // The receipt can only affect this projection after its execution event is reached.
      const effect = run?.state?.effects?.find(e => e.receipt === event.receipt);
      const action = effect?.action;
      if (action?.startsWith('reserve_')) { nodes[1].value = 'Reservation confirmed'; nodes[1].detail = event.detail; nodes[1].status = 'observed'; nodes[1].actionReceipt = event.receipt; }
      if (action === 'refund_payment') { nodes[0].value = 'Refund executed'; nodes[0].detail = event.detail; nodes[0].status = 'observed'; nodes[0].actionReceipt = event.receipt; nodes[0].facts = [['Execution receipt', event.receipt]]; }
      if (action === 'commit_order' || action === 'cancel_order') { nodes[2].value = action === 'commit_order' ? 'Order confirmed' : 'Order cancelled'; nodes[2].detail = 'The action executed. Independent final verification is still required.'; nodes[2].actionReceipt = event.receipt; phase = 'verifying'; }
    } else if (event.kind === 'review') {
      phase = 'review'; active = -1; nodes[2].status = 'review'; nodes[2].value = 'Operator review'; nodes[2].detail = event.detail;
    } else if (event.kind === 'error') {
      phase = 'error'; active = -1; nodes[2].status = 'error'; nodes[2].value = 'Recovery stopped'; nodes[2].detail = event.detail;
    }
  }
  const last = events.at(-1);
  const atEnd = end === all.length - 1;
  // Never borrow the final snapshot while replaying an earlier observation or proposal.
  if (atEnd && last?.kind === 'verification' && ['completed', 'review', 'failed'].includes(run?.status)) {
    for (const tool of TOOLS) {
      const obs = evidence.findLast(e => e.tool === tool);
      if (obs) applyObservation(obs, obs.data);
    }
    active = -1;
    if (run.status === 'completed' && run.checks?.length && run.checks.every(c => c.status === 'pass')) {
      phase = 'verified'; nodes.forEach(n => { n.status = 'verified'; });
      nodes[2].value = run.state.outcome === 'cancelled' ? 'Cancellation verified' : 'Order recovery verified';
      nodes[2].detail = 'Independent checks confirm that the order, payment, stock and customer permissions agree.';
      if (run.state.outcome === 'cancelled') { nodes[1].value = 'Reservation released'; nodes[1].detail = 'The cancelled order no longer holds inventory. The final check confirms the reservation was released.'; }
    } else {
      phase = run.status === 'failed' ? 'error' : 'review';
      nodes[2].status = phase; nodes[2].value = phase === 'error' ? 'Verification failed' : 'Operator review';
      nodes[2].detail = run.state?.escalation_reason || 'The final checks do not establish a completed recovery.';
    }
  }
  if (active >= 0 && !['blocked', 'review', 'error'].includes(nodes[active].status) && last?.kind === 'decision') nodes[active].status = 'active';
  return { phase, phaseLabel: PHASE_LABELS[phase], nodes, active, event: last || null, index: end, total: all.length,
    aligned: phase === 'verified', isReplay: cursor !== null, atEnd };
}
