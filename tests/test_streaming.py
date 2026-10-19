import asyncio
import json

from fastapi.testclient import TestClient
from app import main
from app.streaming import RunStreamResponse


def test_recovery_stream_finishes_only_after_audit_save(monkeypatch):
    async def save(record):
        assert record['status'] == 'completed'
        await asyncio.sleep(0.45)
        return {'saved': True, 'backend': 'firestore'}
    monkeypatch.setattr(main.audit_store, 'save_audit', save)
    with TestClient(main.app) as client:
        assert client.get('/api/config').json()['run_transport'] == 'stream'
        response = client.post('/api/runs', json={'provider': 'rehearsal', 'scenario_id': 'straight-recovery'}, headers={'Accept': 'text/event-stream'})
        assert response.status_code == 200
        assert response.headers['content-type'].startswith('text/event-stream')
        assert 'content-encoding' not in response.headers
        frames = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
        assert any(r.get('phase') == 'Saving audit' and r['status'] == 'running' for r in frames)
        assert frames[-1]['status'] == 'completed'
        assert frames[-1]['persistence']['saved'] is True
        assert frames[-1]['state']['outcome'] == 'recovered'
        assert main.ACTIVE == 0


def test_disconnect_cancels_recovery_and_releases_slot():
    async def exercise():
        started, disconnected = asyncio.Event(), asyncio.Event()
        result = {'released': 0, 'cancelled': False}
        record = {'id': 'test', 'status': 'running'}
        async def work():
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                result['cancelled'] = True
        def release():
            result['released'] += 1
        async def receive():
            await disconnected.wait()
            return {'type': 'http.disconnect'}
        async def send(message):
            if message['type'] == 'http.response.body':
                await started.wait()
                disconnected.set()
        response = RunStreamResponse(record, work, release)
        await response({'type': 'http', 'asgi': {'spec_version': '2.0'}}, receive, send)
        assert result == {'released': 1, 'cancelled': True}
        assert record['status'] == 'error'
        assert record['error']['code'] == 'RUN_INTERRUPTED'
    asyncio.run(exercise())
