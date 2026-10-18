import test from 'node:test';
import assert from 'node:assert/strict';
import { projectWorkflow } from './workflowView.js';

const receipt = { id: 'EV-01', tool: 'inspect_payment', data: { status: 'captured', receipt: 'PAY-1', charge_count: 1, captured_cents: 49800, refunded_cents: 0 } };
const stock = { id: 'EV-02', tool: 'inspect_inventory', data: { version: 7, available: 2, incoming_days: 1, reserved_quantity: 0 } };
const newStock = { id: 'EV-03', tool: 'inspect_inventory', data: { version: 8, available: 0, incoming_days: 1, reserved_quantity: 0 } };
const finalStock = { id: 'EV-04', tool: 'inspect_inventory', data: { version: 9, available: 0, incoming_days: 1, reserved_quantity: 2 } };
const run = { status: 'completed', checks: [{ status: 'pass' }], state: { outcome: 'recovered', evidence: [receipt, stock, newStock, finalStock], effects: [{ receipt: 'ACT-01', action: 'commit_order' }] }, events: [
  { kind: 'decision', action: 'inspect_payment' },
  { kind: 'evidence', evidence_id: 'EV-01', data: receipt.data },
  { kind: 'evidence', evidence_id: 'EV-02', data: stock.data },
  { kind: 'guard', code: 'STALE_STOCK' },
  { kind: 'decision', action: 'inspect_inventory' },
  { kind: 'evidence', evidence_id: 'EV-03', data: newStock.data },
  { kind: 'action', receipt: 'ACT-01' },
  { kind: 'verification' },
] };
test('an unopened incident stays unverified', () => {
  const view = projectWorkflow(null);
  assert.equal(view.phase, 'idle'); assert.equal(view.aligned, false);
  assert.ok(view.nodes.every(n => n.status === 'waiting' && !n.evidenceId));
});
test('replay never shows evidence or success from the future', () => {
  const view = projectWorkflow(run, 0);
  assert.equal(view.nodes[0].evidenceId, null); assert.equal(view.nodes[1].value, 'Reservation expired');
  assert.equal(view.aligned, false);
});
test('a reached receipt is inspectable', () => {
  const view = projectWorkflow(run, 1);
  assert.equal(view.nodes[0].evidenceId, 'EV-01'); assert.equal(view.nodes[0].value, 'Captured once');
});
test('stock conflict persists until a fresh observation arrives', () => {
  assert.equal(projectWorkflow(run, 3).nodes[1].status, 'blocked');
  assert.equal(projectWorkflow(run, 4).phase, 'replanning');
  assert.equal(projectWorkflow(run, 4).nodes[1].evidenceId, 'EV-02');
  assert.equal(projectWorkflow(run, 5).nodes[1].value, '0 original units available');
});
test('an executed order is not yet a verified outcome', () => {
  const view = projectWorkflow(run, 6);
  assert.equal(view.phase, 'verifying'); assert.equal(view.aligned, false);
});
test('only the final passing verification aligns the scene', () => {
  const view = projectWorkflow(run);
  assert.equal(view.aligned, true); assert.equal(view.nodes[1].evidenceId, 'EV-04');
  assert.equal(view.nodes[2].value, 'Order recovery verified');
});
test('review or failed checks never produce a green scene', () => {
  assert.equal(projectWorkflow({ ...run, status: 'review' }).phase, 'review');
  assert.equal(projectWorkflow({ ...run, status: 'failed', checks: [{ status: 'fail' }] }).aligned, false);
  assert.equal(projectWorkflow({ ...run, checks: [] }).aligned, false);
});
test('payment uncertainty remains uncertainty', () => {
  const unknown = { id: 'EV-U', tool: 'inspect_payment', data: { status: 'unknown' } };
  const view = projectWorkflow({ status: 'running', state: { evidence: [unknown] }, events: [{ kind: 'evidence', evidence_id: 'EV-U', data: unknown.data }] });
  assert.equal(view.nodes[0].status, 'review'); assert.equal(view.nodes[0].value, 'Payment unknown');
});
