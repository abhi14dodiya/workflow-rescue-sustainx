from __future__ import annotations
import asyncio
import time
from .agent import Planner, ProviderError
from .domain import World, now

async def run_recovery(record: dict, fixture: dict, delay: float = 0.25) -> dict:
    world, planner = World(fixture), Planner(record["provider"])
    started = time.perf_counter()
    record.update(status="running", events=[], state=world.snapshot(), checks=[], metrics={})
    def event(kind, title, detail, **extra):
        item = {"id": len(record["events"])+1, "at": now(), "kind": kind, "title": title, "detail": detail, **extra}
        record["events"].append(item)
    def waiting(seconds):
        record['phase'] = 'Waiting for Gemini quota' if seconds else ('Investigating' if len(world.evidence) < 3 else 'Recovering')
        if seconds:
            event('wait', 'Respecting Gemini free-tier limits',
                  f'Waiting about {max(1, round(seconds))} seconds before the next model request. No business action is executed during this wait.')
    planner.on_wait = waiting
    event("incident", "Payment timed out. The order stopped.", "The original stock reservation expired. Recovery starts by checking what actually happened.")
    try:
        if record['provider'] not in {'rehearsal', 'baseline'}:
            # These three reads are mandatory before any mutation. Code gathers
            # them once; reserve scarce model calls for recovery and replanning.
            event('preflight', 'Gathering the required service evidence',
                  'The controller reads payment, inventory and dispatch. Gemini will choose the recovery action from these observations.')
            for tool in ('inspect_payment', 'inspect_inventory', 'inspect_dispatch'):
                obs = world.observe(tool)
                event('evidence', obs['source'], observation_summary(obs), evidence_id=obs['id'], data=obs['data'])
            record['state'] = world.snapshot()
            planner.metrics['preflight_reads'] = 3
        for step in range(12):
            record["phase"] = "Investigating" if len(world.evidence) < 3 else "Recovering"
            decision = await planner.next(world)
            event("decision", decision.action.replace("_", " ").capitalize(), decision.explanation,
                  evidence_ids=decision.evidence_ids, action=decision.action)
            await asyncio.sleep(delay)
            result = world.execute(decision, f"{record['id']}:{step}:{decision.action}")
            if "observation" in result:
                obs = result["observation"]
                event("evidence", obs["source"], observation_summary(obs), evidence_id=obs["id"], data=obs["data"])
            elif not result["ok"]:
                event("guard", "Plan paused · " + result["code"].replace("_", " ").lower(), result["detail"], code=result["code"])
                if result.get("external_change"):
                    event("change", "Another order took the remaining stock", "Inventory moved from version 7 to 8 between observation and reservation. This run must obtain a new snapshot.")
            elif decision.action == "escalate":
                event("review", "Handed to an operator", result["detail"])
            elif decision.action == "verify":
                event("verification", "Intermediate state inspected", "Independent checks ran; an unfinished business operation still requires recovery or escalation.")
            else:
                event("action", "Executed · " + decision.action.replace("_", " "), result["detail"], receipt=result.get("receipt"))
            record["state"] = world.snapshot()
            record["metrics"] = {**planner.metrics, "steps": step+1, "elapsed_ms": round((time.perf_counter()-started)*1000)}
            if world.outcome:
                break
        if not world.outcome:
            world.outcome, world.escalation_reason = "escalated", "The bounded planner reached its 12-step limit. An operator must review the unresolved state."
            event("review", "Step limit reached", world.escalation_reason)
        record["phase"] = "Verifying"
        for tool in ("inspect_payment", "inspect_inventory", "inspect_dispatch"):
            world.observe(tool)
        record["checks"] = world.verify()
        safety_failures = [c for c in record["checks"] if c["category"] == "safety" and c["status"] == "fail"]
        failures = [c for c in record["checks"] if c["status"] == "fail"]
        record["status"] = "failed" if failures else ("review" if world.outcome == "escalated" else "completed")
        event("verification", "Independent verification complete", f"{sum(c['status']=='pass' for c in record['checks'])} passed · {sum(c['status']=='review' for c in record['checks'])} need review · {len(safety_failures)} safety issues.")
    except ProviderError as e:
        record.update(status="error", error={"code": e.code, "message": e.message})
        event("error", "Model connection stopped", e.message, code=e.code)
        world.outcome, world.escalation_reason = "escalated", "Live planner stopped. Review any completed actions before retrying."
        record["checks"] = world.verify()
    except Exception:
        record.update(status="error", error={"code": "INTERNAL_ERROR", "message": "The run stopped on an internal error. Review the audit trail before retrying."})
        event("error", "Recovery stopped", record["error"]["message"])
        # No raw provider exception or credentials enter the public audit trail.
        world.outcome, world.escalation_reason = "escalated", "Internal execution error; operator review required."
        record["checks"] = world.verify()
    finally:
        record["state"] = world.snapshot()
        record["metrics"] = {**planner.metrics, "steps": sum(e["kind"] == "decision" for e in record["events"]),
                             "elapsed_ms": round((time.perf_counter()-started)*1000), "blocked_proposals": len(world.blocked)}
        record["phase"] = "Finished"
        record["finished_at"] = now()
    return record

def observation_summary(obs: dict) -> str:
    data = obs["data"]
    if obs["tool"] == "inspect_payment":
        if data["status"] == "unknown":
            return "No authoritative receipt. Payment is unknown, not failed."
        return f"{data['charge_count']} charge · ${data['captured_cents']/100:.2f} captured · ${data['refunded_cents']/100:.2f} refunded · {data['receipt']}"
    if obs["tool"] == "inspect_inventory":
        return f"Version {data['version']} · {data['available']} original units now · next stock in {data['incoming_days']} day(s) · {data['reserved_quantity']} reserved"
    return "Dispatch status: " + data["status"].replace("_", " ")

async def fixed_baseline(fixture: dict) -> dict:
    record = {"id": "baseline", "provider": "baseline"}
    await run_recovery(record, fixture, delay=0)
    return {"label": "Fixed workflow with guards", "scope": "Reads all authorities and uses the same permitted actions. Stops for review after a stock-version conflict; has no adaptive replanning branch.",
            "status": record["status"], "outcome": record["state"]["outcome"], "steps": record["metrics"]["steps"],
            "safety_issues": sum(c["status"] == "fail" for c in record["checks"] if c["category"] == "safety"),
            "note": "A broader rules engine can also solve these fixtures. This comparison alone does not establish AI superiority."}

