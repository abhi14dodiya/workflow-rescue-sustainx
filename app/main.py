from __future__ import annotations
import asyncio
import hmac
import os
import secrets
from collections import OrderedDict
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, ConfigDict
from .agent import Planner, ProviderError, provider_options
from .domain import now
from .runner import fixed_baseline, run_recovery
from .scenarios import SCENARIOS, public_scenarios, scenario
from .incidents import IncidentInput
from . import audit_store

ROOT = Path(__file__).resolve().parents[1]
app = FastAPI(title="Workflow Rescue", version="0.1.0", docs_url="/api/docs", redoc_url=None)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.mount("/assets", StaticFiles(directory=ROOT / "web"), name="assets")
RUNS: OrderedDict[str, dict] = OrderedDict()
TASKS: set[asyncio.Task] = set()
ACTIVE = 0

class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str = "stock-race"
    provider: Literal["rehearsal", "gemini", "vertex", "openai", "azure"] = "rehearsal"
    custom_incident: IncidentInput | None = None

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
    response.headers["Cache-Control"] = ("no-store" if request.url.path.startswith("/api") else
                                         "public, max-age=31536000, immutable" if request.url.path.startswith("/assets/bundle/") else "no-cache")
    return response

@app.get("/")
def home():
    return FileResponse(ROOT / "web" / "index.html")

@app.get("/healthz")
def health():
    return {"status": "ok", "service": "workflow-rescue", "version": "0.1.0"}

@app.get("/api/config")
def config():
    providers = provider_options()
    preferred = os.getenv("DEFAULT_PROVIDER", "rehearsal")
    default = next((p["id"] for p in providers if p["id"] == preferred and p["configured"]), "rehearsal")
    return {"providers": providers, "default_provider": default, "simulated_services": True,
            "live_token_required": bool(os.getenv("DEMO_ACCESS_TOKEN")), "max_steps": 12,
            "storage": "Firestore stores completed audits; active runs remain in one process." if audit_store.configured() else "Ephemeral single-process demo; reports can be exported.",
            "audit_persistence": audit_store.configured()}

@app.get("/api/scenarios")
def scenarios():
    return public_scenarios()


@app.get('/api/incidents/template')
def incident_template():
    return IncidentInput().model_dump()


@app.post('/api/incidents/preview')
def preview_incident(body: IncidentInput):
    return {'scenario':body.public(), 'input':body.model_dump(), 'simulated_services':True}

def check_live_access(request: Request, provider: str):
    if provider == "rehearsal":
        return
    token = os.getenv("DEMO_ACCESS_TOKEN")
    if token and not hmac.compare_digest(request.headers.get("X-Demo-Token", ""), token):
        raise HTTPException(403, "The configured demo access token is required for live model calls.")
    if not next(p["configured"] for p in provider_options() if p["id"] == provider):
        raise HTTPException(409, "This provider is not configured on the server.")

@app.post("/api/provider-check")
async def provider_check(body: RunRequest, request: Request):
    global ACTIVE
    check_live_access(request, body.provider)
    if body.provider == "rehearsal":
        return {"ok": True, "provider": "rehearsal", "message": "Rehearsal is available. It uses no AI model."}
    if ACTIVE >= int(os.getenv("MAX_ACTIVE_RUNS", "2")):
        raise HTTPException(429, "The demo is busy. Try again after an active run finishes.")
    ACTIVE += 1
    try:
        planner = Planner(body.provider)
        await planner.generate({"task": "Connectivity check only. Return action verify, a brief greeting, empty evidence_ids and expected_version null. There is no business transaction to execute."})
        return {"ok": True, "provider": body.provider, "message": "Live structured model response received and validated.", "metrics": planner.metrics}
    except ProviderError as e:
        return JSONResponse(status_code=502, content={"ok": False, "error": {"code": e.code, "message": e.message}})
    finally:
        ACTIVE -= 1

@app.post("/api/runs", status_code=202)
async def start_run(body: RunRequest, request: Request):
    global ACTIVE
    if body.scenario_id == 'custom' and body.custom_incident is None:
        raise HTTPException(422, 'Provide a validated custom incident before starting.')
    if body.scenario_id != 'custom' and body.custom_incident is not None:
        raise HTTPException(422, 'Custom incident data requires scenario_id custom.')
    if body.scenario_id not in SCENARIOS and body.scenario_id != 'custom':
        raise HTTPException(404, "Scenario not found.")
    check_live_access(request, body.provider)
    if ACTIVE >= int(os.getenv("MAX_ACTIVE_RUNS", "2")):
        raise HTTPException(429, "The demo is busy. Try again after an active run finishes.")
    ACTIVE += 1
    identifier = secrets.token_urlsafe(18)
    record = {"id": identifier, "provider": body.provider, "scenario_id": body.scenario_id,
              "created_at": now(), "status": "queued", "events": [], "checks": [], "metrics": {},
              "model": next(p["model"] for p in provider_options() if p["id"] == body.provider)}
    fixture = body.custom_incident.fixture() if body.custom_incident else scenario(body.scenario_id)
    if body.custom_incident:
        record['custom_incident'] = body.custom_incident.model_dump()
        record['incident'] = body.custom_incident.public()
    while len(RUNS) >= 100:
        inactive = next((k for k, v in RUNS.items() if v["status"] not in {"queued", "running"}), None)
        if inactive is None:
            ACTIVE -= 1
            raise HTTPException(429, "The demo's run capacity has been reached.")
        del RUNS[inactive]
    RUNS[identifier] = record
    async def work():
        global ACTIVE
        try:
            record["baseline"] = await fixed_baseline(fixture)
            await run_recovery(record, fixture)
            terminal_status = record['status']
            stored_record = dict(record)
            record.update(status='running', phase='Saving audit')
            try:
                record['persistence'] = await audit_store.save_audit(stored_record)
            finally:
                record.update(status=terminal_status, phase='Finished')
        finally:
            ACTIVE -= 1
    task = asyncio.create_task(work())
    TASKS.add(task)
    task.add_done_callback(TASKS.discard)
    return {"id": identifier, "status": "queued"}

@app.get("/api/runs/{identifier}")
async def get_run(identifier: str):
    if identifier not in RUNS:
        try:
            stored = await audit_store.load_audit(identifier)
        except audit_store.AuditStoreError as error:
            raise HTTPException(503, str(error)) from None
        if stored is not None:
            return stored
        raise HTTPException(404, "Run not found or expired. Start a new run.")
    return RUNS[identifier]

@app.get("/api/runs/{identifier}/export")
async def export_run(identifier: str):
    return JSONResponse(content={"application": "Workflow Rescue", "team": "sustAInX", "services": "synthetic simulation", "report": await get_run(identifier)},
                        headers={"Content-Disposition": 'attachment; filename="workflow-rescue-audit.json"'})
