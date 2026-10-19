import test from 'node:test';
import assert from 'node:assert/strict';
import { readRunStream } from './runStream.js';

function response(text, width = 7) {
  const bytes = new TextEncoder().encode(text);
  return new Response(new ReadableStream({ start(controller) {
    for (let i = 0; i < bytes.length; i += width) controller.enqueue(bytes.slice(i, i + width));
    controller.close();
  } }), { headers: { 'content-type': 'text/event-stream' } });
}

test('live records survive split UTF-8, frame boundaries and heartbeats', async () => {
  const records = [];
  await readRunStream(response('data: {"id":"one","status":"running","phase":"Checking ₹498"}\r\n\r\n: waiting\r\n\r\ndata: {"id":"one","status":"completed","persistence":{"saved":true}}\r\n\r\n'), r => records.push(r));
  assert.equal(records.length, 2);
  assert.equal(records[0].phase, 'Checking ₹498');
  assert.equal(records[1].persistence.saved, true);
});

test('an interrupted stream cannot be presented as completed', async () => {
  await assert.rejects(readRunStream(response('data: {"id":"one","status":"running"}\n\n'), () => {}), /before recovery finished/);
});

test('HTTP and invalid transport errors remain visible', async () => {
  await assert.rejects(readRunStream(new Response('{"detail":"Demo is busy"}', { status: 429 }), () => {}), /Demo is busy/);
  await assert.rejects(readRunStream(new Response('<html>Waking up</html>'), () => {}), /live recovery stream/);
});
