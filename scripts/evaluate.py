"""Run the reviewed six-case suite. Live Gemini consumes quota; rehearsal does not."""
import argparse
import asyncio
import json
import os
import ssl
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.environment import configure_environment
from app.runner import run_recovery, fixed_baseline
from app.scenarios import scenario, SCENARIOS
from app.domain import now

async def deployed_run(client, identifier, provider):
    response = await client.post('/api/runs', json={'scenario_id':identifier, 'provider':provider})
    response.raise_for_status()
    run_id = response.json()['id']
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        response = await client.get(f'/api/runs/{run_id}')
        response.raise_for_status()
        run = response.json()
        if run['status'] not in {'queued', 'running'}:
            return run
        await asyncio.sleep(1)
    raise TimeoutError(f'Deployed fixture {identifier} did not finish within 10 minutes.')


async def evaluate(provider, client=None, base_url=None):
    if provider not in {'rehearsal', 'gemini'}:
        raise ValueError('Only Gemini or deterministic rehearsal is supported.')
    cases=[]
    for identifier in SCENARIOS:
        fixture=scenario(identifier)
        run=(await deployed_run(client, identifier, provider) if client else
             await run_recovery({"id":f"eval-{identifier}","provider":provider},fixture,delay=0))
        baseline=run.get('baseline') if client else await fixed_baseline(fixture)
        cases.append({"scenario":identifier,"expected":fixture["expected"],"observed":run["state"]["outcome"],
                      "correct":run["state"]["outcome"]==fixture["expected"] and run["status"] not in {"failed","error"},
                      "safety_issues":sum(c["status"]=="fail" for c in run["checks"] if c["category"]=="safety"),
                      "review_checks":sum(c["status"]=="review" for c in run["checks"]),
                      "status":run["status"],"metrics":run["metrics"],"error":run.get("error"),"baseline":baseline,"trace":run})
        print(json.dumps({"scenario": identifier, "correct": cases[-1]["correct"], "status": run["status"], "calls": run["metrics"]["calls"]}), flush=True)
    report={"at":now(),"provider":provider,"suite":"six reviewed synthetic fixtures, not a held-out benchmark",
            "execution":"deployed application" if client else "local process", "base_url":base_url,
            "live_model":provider!="rehearsal","cases":cases,"correct":sum(c["correct"] for c in cases),
            "total":len(cases),"safety_issues":sum(c["safety_issues"] for c in cases),
            "limitations":"Rules-based rehearsal results do not establish Gemini accuracy. Fixed and adaptive planners share the same permitted tools. Baseline deliberately has no stock-conflict replanning branch."}
    output=ROOT/"artifacts"/f"evaluation-{provider}.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="cases"},indent=2))
    return 0 if report["correct"]==report["total"] and not report["safety_issues"] else 1


async def main(provider, base_url):
    if provider not in {'rehearsal', 'gemini'}:
        raise ValueError('Only Gemini or deterministic rehearsal is supported.')
    if not base_url:
        return await evaluate(provider)
    url = urlsplit(base_url)
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in {'', '/'}:
        raise ValueError('--base-url must be the HTTPS application origin, without credentials, path or query.')
    headers = {'X-Demo-Token':os.environ['DEMO_ACCESS_TOKEN']} if os.getenv('DEMO_ACCESS_TOKEN') else {}
    async with httpx.AsyncClient(base_url=base_url.rstrip('/'), headers=headers,
                                 verify=ssl.create_default_context(), timeout=240) as client:
        response = await client.post('/api/provider-check', json={'provider':provider})
        if response.status_code != 200 or not response.json().get('ok'):
            print(f'Connection check failed (HTTP {response.status_code}). Inspect Test connection in the deployed workspace; no scenario evaluation was started.')
            return 1
        return await evaluate(provider, client, base_url)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--provider",choices=["rehearsal","gemini"],default="rehearsal")
    parser.add_argument('--base-url', help='Evaluate the public HTTPS deployment instead of calling the model locally.')
    args=parser.parse_args()
    # This CLI process does not retain unrelated model credentials from its
    # parent. Importing the evaluator in tests has no environment side effects.
    configure_environment(ROOT / '.env')
    raise SystemExit(asyncio.run(main(args.provider, args.base_url)))
