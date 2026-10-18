"""Exercise the deployed evaluator through the actual application boundary."""
import asyncio
import httpx
import pytest
from app.main import app
from scripts import evaluate


def test_remote_evaluator_observes_a_real_completed_recovery(monkeypatch):
    monkeypatch.delenv('DEMO_ACCESS_TOKEN', raising=False)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='https://testserver') as client:
            return await evaluate.deployed_run(client, 'stock-race', 'rehearsal')
    result = asyncio.run(run())
    assert result['status'] == 'completed'
    assert result['state']['outcome'] == 'recovered'
    assert result['metrics']['calls'] == 0
    assert all(check['status'] == 'pass' for check in result['checks'])
    assert result['baseline']['outcome'] == 'escalated'


def test_failed_deployed_connection_does_not_start_scenarios(monkeypatch):
    requests = []
    def respond(request):
        requests.append(request)
        return httpx.Response(502, json={'ok':False, 'error':{'code':'GATEWAY_403'}})
    original = httpx.AsyncClient
    monkeypatch.setattr(evaluate.httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(respond), **kw))
    assert asyncio.run(evaluate.main('vertex', 'https://example.run.app')) == 1
    assert [request.url.path for request in requests] == ['/api/provider-check']


@pytest.mark.parametrize('origin', ['http://example.run.app', 'https://user:secret@example.run.app', 'https://example.run.app/?token=secret'])
def test_remote_evaluator_rejects_insecure_or_credential_bearing_urls(origin):
    with pytest.raises(ValueError):
        asyncio.run(evaluate.main('vertex', origin))
