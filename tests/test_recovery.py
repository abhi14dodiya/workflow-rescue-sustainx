import asyncio
from copy import deepcopy
import pytest
from pydantic import ValidationError
from app.domain import Decision, World
from app.scenarios import scenario, SCENARIOS
from app.runner import run_recovery, fixed_baseline
from app.agent import Planner, ProviderError

def ready(identifier="straight-recovery"):
    world = World(scenario(identifier))
    for tool in ("inspect_payment", "inspect_inventory", "inspect_dispatch"):
        world.observe(tool)
    return world

def decision(world, action, **overrides):
    return Decision(**{**{"action": action, "explanation": "Test proposal", "evidence_ids": [e["id"] for e in world.evidence],
                         "expected_version": world.inventory["version"] if action.startswith("reserve_") else None}, **overrides})

@pytest.mark.parametrize("identifier", SCENARIOS)
def test_scenarios_reach_expected_outcome_and_preserve_safety(identifier):
    fixture = scenario(identifier)
    result = asyncio.run(run_recovery({"id":identifier,"provider":"rehearsal"}, fixture, delay=0))
    assert result["state"]["outcome"] == fixture["expected"]
    assert not [c for c in result["checks"] if c["category"] == "safety" and c["status"] == "fail"]
    assert result["metrics"]["calls"] == 0
    if fixture["expected"] == "escalated":
        assert result["status"] == "review"
        assert result["state"]["effects"] == []

def test_real_stock_race_invalidates_proposal_and_changes_recovery():
    result = asyncio.run(run_recovery({"id":"race","provider":"rehearsal"}, scenario("stock-race"), delay=0))
    actions = [e.get("action") for e in result["events"] if e["kind"] == "decision"]
    assert actions == ["inspect_payment","inspect_inventory","inspect_dispatch","reserve_original","inspect_inventory","reserve_incoming","commit_order"]
    assert result["state"]["order"]["delivery_days"] == 1
    assert result["state"]["order"]["sku"] == "FIELD-KIT"
    assert result["metrics"]["blocked_proposals"] == 1
    assert result["state"]["payment"]["charge_count"] == 1

def test_fixed_baseline_is_safe_and_stops_on_conflict():
    result = asyncio.run(fixed_baseline(scenario("stock-race")))
    assert result["outcome"] == "escalated"
    assert result["safety_issues"] == 0

def test_fixed_baseline_can_complete_non_racing_case():
    assert asyncio.run(fixed_baseline(scenario("straight-recovery")))["outcome"] == "recovered"

def test_prohibited_substitution_is_blocked_without_side_effect():
    w = ready()
    before = deepcopy(w.inventory)
    result = w.execute(decision(w,"reserve_alternative"),"substitution")
    assert result["code"] == "SUBSTITUTION_FORBIDDEN"
    assert w.inventory == before and not w.effects

def test_delay_outside_permission_is_blocked():
    w = ready("approved-substitute")
    assert w.execute(decision(w,"reserve_incoming"),"late")["code"] == "DELAY_FORBIDDEN"
    assert w.inventory["reserved_quantity"] == 0

def test_cancellation_revokes_fulfillment_permission():
    w = ready("cancel-order")
    assert w.execute(decision(w,"reserve_original"),"reservation")["code"] == "CUSTOMER_CANCELLED"

def test_unrequested_refund_is_blocked():
    w = ready()
    assert w.execute(decision(w,"refund_payment"),"refund")["code"] == "REFUND_NOT_AUTHORIZED"
    assert w.payment["refunded_cents"] == 0

def test_unknown_payment_cannot_authorize_writes():
    w = ready("unknown-payment")
    assert w.execute(decision(w,"reserve_original"),"reservation")["code"] == "PAYMENT_UNCERTAIN"
    assert w.snapshot()["payment"]["status"] == "unknown"
    assert "captured_cents" not in w.snapshot()["payment"]

def test_irreversible_shipment_blocks_compensation():
    w = ready("already-dispatched")
    assert w.execute(decision(w,"refund_payment"),"refund")["code"] == "ALREADY_DISPATCHED"
    assert w.payment["refunded_cents"] == 0

def test_duplicate_request_replays_receipt_without_reserving_twice():
    w = ready()
    d = decision(w,"reserve_original")
    first = w.execute(d,"same-key")
    second = w.execute(d,"same-key")
    assert first["ok"] and second["replayed"]
    assert first["receipt"] == second["receipt"]
    assert w.inventory["reserved_quantity"] == 2
    assert w.inventory["available"] == 2
    assert len(w.effects) == 1

def test_idempotency_key_cannot_be_reused_for_different_payload():
    w = ready()
    w.execute(decision(w,"reserve_original"),"key")
    assert w.execute(decision(w,"refund_payment"),"key")["code"] == "IDEMPOTENCY_CONFLICT"

def test_duplicate_refund_with_different_key_is_blocked():
    w = ready("cancel-order")
    assert w.execute(decision(w,"refund_payment"),"first")["ok"]
    assert w.execute(decision(w,"refund_payment"),"second")["code"] == "ALREADY_REFUNDED"
    assert w.payment["refunded_cents"] == 49800

def test_stale_version_causes_no_reservation_even_without_injected_race():
    w = ready()
    w.inventory["version"] += 1
    assert w.execute(decision(w,"reserve_original",expected_version=7),"old")["code"] == "STALE_STOCK"
    assert w.inventory["reserved_quantity"] == 0

def test_model_cannot_guess_unobserved_version_to_bypass_reinspection():
    w = ready()
    w.inventory["version"] += 1
    assert w.execute(decision(w,"reserve_original",expected_version=8),"guess")["code"] == "UNOBSERVED_VERSION"

def test_verifier_detects_stock_creation_and_unapproved_alternative():
    w = ready("approved-substitute")
    w.inventory["available"] += 50
    w.inventory["reservation_sku"] = "A-DIFFERENT-ALTERNATIVE"
    assert {c["id"] for c in w.verify() if c["status"] == "fail"} >= {"inventory","consent"}

def test_verifier_detects_order_disagreement_after_success():
    w = ready()
    w.execute(decision(w,"reserve_original"),"reserve")
    w.execute(decision(w,"commit_order"),"commit")
    w.order["sku"] = "WRONG-ITEM"
    assert next(c for c in w.verify() if c["id"] == "outcome")["status"] == "fail"

def test_commit_requires_actual_reservation():
    w = ready()
    assert w.execute(decision(w,"commit_order"),"commit")["code"] == "COMMIT_PRECONDITION"
    assert w.order["status"] == "interrupted"

def test_fabricated_evidence_cannot_authorize_mutation():
    w = ready()
    assert w.execute(decision(w,"reserve_original",evidence_ids=["EV-FAKE"]),"fake")["code"] == "UNKNOWN_EVIDENCE"

def test_all_authorities_must_be_observed_and_cited():
    w = World(scenario("straight-recovery"))
    w.observe("inspect_payment")
    assert w.execute(decision(w,"reserve_original"),"incomplete")["code"] == "MISSING_OBSERVATION"
    w = ready()
    assert w.execute(decision(w,"reserve_original",evidence_ids=["EV-01"]),"missing-citation")["code"] == "INCOMPLETE_CITATIONS"

def test_terminal_state_cannot_be_mutated():
    w = ready()
    w.execute(decision(w,"reserve_original"),"reserve")
    w.execute(decision(w,"commit_order"),"commit")
    assert w.execute(decision(w,"reserve_original"),"again")["code"] == "TERMINAL_STATE"

def test_schema_rejects_tools_outside_allowlist_and_extra_fields():
    with pytest.raises(ValidationError):
        Decision(action="charge_customer",explanation="Unsafe",evidence_ids=[],expected_version=None)
    with pytest.raises(ValidationError):
        Decision(action="verify",explanation="Unsafe",evidence_ids=[],expected_version=None,shell="run arbitrary code")

def test_verifier_detects_corrupted_ledger_and_forbidden_substitution():
    w = ready()
    w.payment["charge_count"] = 2
    w.inventory["reservation_sku"] = "UNAPPROVED-SKU"
    assert {c["id"] for c in w.verify() if c["status"] == "fail"} >= {"one-charge","consent"}

def test_expected_outcome_and_fault_switches_are_hidden_from_planner():
    w = ready("stock-race")
    context = w.agent_context()
    assert "fixture" not in context and "expected" not in context and "race" not in context

def test_live_provider_failure_does_not_fall_back_or_claim_success(monkeypatch):
    async def failure(self,world):
        raise ProviderError("HTTP_401","Credential rejected")
    monkeypatch.setattr(Planner,"next",failure)
    result = asyncio.run(run_recovery({"id":"bad-key","provider":"gemini"},scenario("stock-race"),delay=0))
    assert result["status"] == "error"
    assert result["error"]["code"] == "HTTP_401"
    assert result["state"]["effects"] == []
    assert result["state"]["outcome"] == "escalated"

def test_endless_planning_stops_at_bounded_step_limit(monkeypatch):
    async def looping(self,world):
        return Decision(action="inspect_payment",explanation="Read again",evidence_ids=[],expected_version=None)
    monkeypatch.setattr(Planner,"next",looping)
    result = asyncio.run(run_recovery({"id":"loop","provider":"gemini"},scenario("stock-race"),delay=0))
    assert result["status"] == "review" and result["metrics"]["steps"] == 12
    assert not result["state"]["effects"]

