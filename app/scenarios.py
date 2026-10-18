"""Synthetic scenarios. Expected outcomes are test oracles, never agent inputs."""
from copy import deepcopy

SCENARIOS = {
    "stock-race": {
        "id": "stock-race", "name": "The order that fell between systems",
        "tag": "Featured · changing stock", "customer": "Maya Chen", "company": "Northstar Field Operations",
        "summary": "The payment timed out. The money did not. Now the stock is changing.",
        "message": "We need two Field Kits for the site team. The exact model matters: please do not substitute. One or two extra days is fine, but don't charge us again. If that isn't possible, check with me first.",
        "policy": {"allow_delay": True, "max_delay_days": 2, "allow_substitution": False, "cancel_requested": False},
        "available": 2, "incoming_days": 1, "race": True, "payment_unknown": False, "shipped": False,
        "expected": "recovered",
    },
    "straight-recovery": {
        "id": "straight-recovery", "name": "A lost acknowledgement",
        "tag": "Control · stock available", "customer": "Arjun Shah", "company": "Northstar Field Operations",
        "summary": "A timeout hides a successful charge. The original items are still available.",
        "message": "Please complete the original order, same model, same price. We can wait up to two days. Do not make a second payment.",
        "policy": {"allow_delay": True, "max_delay_days": 2, "allow_substitution": False, "cancel_requested": False},
        "available": 4, "incoming_days": 1, "race": False, "payment_unknown": False, "shipped": False,
        "expected": "recovered",
    },
    "cancel-order": {
        "id": "cancel-order", "name": "The customer changed their mind",
        "tag": "Compensation · cancellation", "customer": "Elena Rossi", "company": "Northstar Field Operations",
        "summary": "Payment succeeded, but the customer cancelled before dispatch.",
        "message": "Our site visit is cancelled. Please cancel both kits, release any stock, and return the full payment. Do not dispatch anything.",
        "policy": {"allow_delay": False, "max_delay_days": 0, "allow_substitution": False, "cancel_requested": True},
        "available": 2, "incoming_days": 1, "race": False, "payment_unknown": False, "shipped": False,
        "expected": "cancelled",
    },
    "unknown-payment": {
        "id": "unknown-payment", "name": "When the evidence is missing",
        "tag": "Uncertainty · human review", "customer": "Sam Taylor", "company": "Northstar Field Operations",
        "summary": "The payment authority is unavailable. A timeout is not proof of failure.",
        "message": "Complete the original order if you can confirm the payment. Do not charge again. If you cannot verify what happened, leave it for an operator.",
        "policy": {"allow_delay": True, "max_delay_days": 2, "allow_substitution": False, "cancel_requested": False},
        "available": 2, "incoming_days": 1, "race": False, "payment_unknown": True, "shipped": False,
        "expected": "escalated",
    },
    "approved-substitute": {
        "id": "approved-substitute", "name": "A different promise to keep",
        "tag": "Variation · explicit consent", "customer": "Priya Nair", "company": "Northstar Field Operations",
        "summary": "The original kits are unavailable; the customer explicitly approved an alternative.",
        "message": "We need the kits today. No delay, please. If Field Kit is unavailable, Field Kit Plus is approved, but only at our original total price. Don't charge us again.",
        "policy": {"allow_delay": False, "max_delay_days": 0, "allow_substitution": True, "cancel_requested": False},
        "available": 0, "incoming_days": 3, "race": False, "payment_unknown": False, "shipped": False,
        "expected": "recovered",
    },
    "already-dispatched": {
        "id": "already-dispatched", "name": "A cancellation that needs a person",
        "tag": "Boundary · irreversible action", "customer": "Noah Williams", "company": "Northstar Field Operations",
        "summary": "A cancellation arrives after dispatch. An automated refund could leave the ledgers inconsistent.",
        "message": "Please cancel and refund the order. If it has already shipped, ask an operator to arrange a return first.",
        "policy": {"allow_delay": False, "max_delay_days": 0, "allow_substitution": False, "cancel_requested": True},
        "available": 2, "incoming_days": 1, "race": False, "payment_unknown": False, "shipped": True,
        "expected": "escalated",
    },
}

def scenario(identifier: str) -> dict:
    return deepcopy(SCENARIOS[identifier])

def public_scenarios() -> list[dict]:
    return [{k: deepcopy(v) for k, v in s.items() if k not in {
        "race", "payment_unknown", "shipped", "expected", "available", "incoming_days"
    }} for s in SCENARIOS.values()]

