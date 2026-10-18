import time
import re
from fastapi.testclient import TestClient
from app.main import app

def test_health_and_static_app():
    with TestClient(app) as client:
        assert client.get("/healthz").json()["status"] == "ok"
        home = client.get("/")
        assert home.status_code == 200 and "Every order is a promise." in home.text
        assert "frame-ancestors 'none'" in home.headers["content-security-policy"]
        scripts = re.findall(r'<script[^>]+src="([^"]+)"', home.text)
        assert scripts and all(client.get(src).status_code == 200 for src in scripts)
        script = client.get(scripts[0], headers={"Accept-Encoding": "gzip"})
        assert script.headers["content-encoding"] == "gzip"
        assert "immutable" in script.headers["cache-control"]

def test_invalid_scenario_and_unknown_run():
    with TestClient(app) as client:
        assert client.post("/api/runs",json={"scenario_id":"missing"}).status_code == 404
        assert client.get("/api/runs/missing").status_code == 404
        assert client.post("/api/runs",json={"provider":"arbitrary"}).status_code == 422

def test_provider_config_never_contains_credential(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY","test-secret-do-not-return")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY","azure-secret-do-not-return")
    with TestClient(app) as client:
        r = client.get("/api/config")
        assert "test-secret-do-not-return" not in r.text
        assert "azure-secret-do-not-return" not in r.text
        assert next(p for p in r.json()["providers"] if p["id"] == "gemini")["configured"]

def test_default_planner_requires_complete_configuration_and_never_starts_a_run(monkeypatch):
    monkeypatch.setenv('DEFAULT_PROVIDER','azure')
    monkeypatch.setenv('AZURE_OPENAI_API_KEY','test-only')
    monkeypatch.setenv('AZURE_OPENAI_DEPLOYMENT','test-deployment')
    monkeypatch.delenv('AZURE_OPENAI_BASE_URL',raising=False)
    with TestClient(app) as client:
        assert client.get('/api/config').json()['default_provider'] == 'rehearsal'
        monkeypatch.setenv('AZURE_OPENAI_BASE_URL','https://test.openai.azure.com/openai/v1')
        assert client.get('/api/config').json()['default_provider'] == 'azure'

def test_live_token_gate_and_unconfigured_provider(monkeypatch):
    monkeypatch.setenv("DEMO_ACCESS_TOKEN","local-demo-gate")
    monkeypatch.delenv("GEMINI_API_KEY",raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY",raising=False)
    with TestClient(app) as client:
        assert client.post("/api/runs",json={"provider":"gemini"}).status_code == 403
        assert client.post("/api/runs",json={"provider":"gemini"},headers={"X-Demo-Token":"local-demo-gate"}).status_code == 409

def test_run_endpoint_produces_exportable_real_trace():
    with TestClient(app) as client:
        start = client.post("/api/runs",json={"scenario_id":"stock-race","provider":"rehearsal"})
        assert start.status_code == 202
        identifier = start.json()["id"]
        for _ in range(60):
            run = client.get(f"/api/runs/{identifier}").json()
            if run["status"] not in ("queued","running"):
                break
            time.sleep(.06)
        assert run["status"] == "completed"
        assert run["state"]["outcome"] == "recovered"
        exported = client.get(f"/api/runs/{identifier}/export")
        assert exported.json()["services"] == "synthetic simulation"
        assert exported.json()["report"]["provider"] == "rehearsal"
        assert "attachment" in exported.headers["content-disposition"]


def test_audit_save_finishes_before_run_is_presented_as_terminal(monkeypatch):
    import asyncio
    from app import main
    async def delayed_save(record):
        assert record['status'] == 'completed'
        await asyncio.sleep(.3)
        return {'saved':True, 'backend':'firestore'}
    monkeypatch.setattr(main.audit_store, 'save_audit', delayed_save)
    with TestClient(app) as client:
        started = client.post('/api/runs', json={'scenario_id':'straight-recovery', 'provider':'rehearsal'})
        identifier = started.json()['id']
        saw_saving = False
        for _ in range(100):
            record = client.get('/api/runs/' + identifier).json()
            if record.get('phase') == 'Saving audit':
                saw_saving = True
                assert record['status'] == 'running'
            if record['status'] not in {'queued', 'running'}:
                break
            time.sleep(.035)
        assert saw_saving
        assert record['status'] == 'completed'
        assert record['persistence']['saved'] is True
