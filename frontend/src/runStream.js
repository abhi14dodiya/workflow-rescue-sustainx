// Parse complete SSE records; a dropped connection must not look successful.
export async function readRunStream(response, onRecord) {
  if (!response.ok) {
    let body;
    try { body = await response.json(); } catch { /* keep the HTTP status */ }
    throw new Error(body?.error?.message || (typeof body?.detail === 'string' && body.detail) || `Request failed (HTTP ${response.status}).`);
  }
  if (!response.headers.get('content-type')?.includes('text/event-stream') || !response.body) {
    throw new Error('The server did not provide a live recovery stream. Reload the application and try again.');
  }
  const reader = response.body.getReader(), decoder = new TextDecoder();
  let buffer = '', terminal = false;
  const consume = () => {
    let boundary;
    while ((boundary = buffer.indexOf('\n\n')) !== -1) {
      const frame = buffer.slice(0, boundary); buffer = buffer.slice(boundary + 2);
      const data = frame.split('\n').filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n');
      if (!data) continue;
      const record = JSON.parse(data);
      if (!record?.id || !['queued', 'running', 'completed', 'review', 'failed', 'error'].includes(record.status)) throw new Error('The server returned an invalid recovery record.');
      terminal = !['queued', 'running'].includes(record.status);
      onRecord(record);
    }
  };
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      buffer = buffer.replaceAll('\r\n', '\n');
      consume();
      if (buffer.length > 4_000_000) throw new Error('The recovery stream exceeded its response limit.');
      if (done) break;
    }
    if (!terminal) throw new Error('The connection ended before recovery finished. Review the latest evidence before starting again.');
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
