"""Regenerate deterministic cross-runtime evidence from the primary Python app.

No model requests, secrets or network access. Run from the repository root.
"""
import asyncio
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.domain import World, Decision
from app.scenarios import SCENARIOS
from app.incidents import IncidentInput
from app.runner import run_recovery, fixed_baseline


def normalize(value):
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()
                if key not in {'at', 'finished_at', 'elapsed_ms'}}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


async def main():
    fixtures = list(SCENARIOS.values())
    rng = random.Random(1042)
    for index in range(48):
        fixtures.append(IncidentInput(
            available=rng.randrange(5), incoming_available=rng.randrange(5),
            alternative_available=rng.randrange(5), incoming_days=rng.randrange(5),
            max_delay_days=rng.randrange(4), allow_delay=rng.choice([True, False]),
            allow_substitution=rng.choice([True, False]), cancel_requested=index % 7 == 0,
            payment_unknown=index % 11 == 0, shipped=index % 13 == 0,
            race=rng.choice([True, False]),
        ).fixture())
    cases = []
    for index, fixture in enumerate(fixtures):
        for provider in ('rehearsal', 'baseline'):
            record = await run_recovery({'id': f'parity-{index}', 'provider': provider}, fixture, delay=0)
            cases.append({'fixture': fixture, 'provider': provider, 'id': record['id'], 'expected': normalize(record)})
    guards = []
    def guard(label, scenario_id='straight-recovery', reads=3, action='reserve_original', changes=None, decision_changes=None, before=None):
        w = World(SCENARIOS[scenario_id])
        tools = ('inspect_payment', 'inspect_inventory', 'inspect_dispatch')
        for t in tools[:reads]: w.observe(t)
        if changes:
            for container, key, value in changes:
                getattr(w, container)[key] = value
        def d(a, overrides=None):
            return Decision(**{**{'action': a, 'explanation': 'Parity guard proposal',
                'evidence_ids': [e['id'] for e in w.evidence],
                'expected_version': w.inventory['version'] if a.startswith('reserve_') else None}, **(overrides or {})})
        steps = []
        for a, key in before or []:
            proposal = d(a)
            result = w.execute(proposal, key)
            steps.append({'decision': proposal.model_dump(), 'key': key, 'result': normalize(result)})
        proposal = d(action, decision_changes)
        result = w.execute(proposal, 'test')
        steps.append({'decision': proposal.model_dump(), 'key': 'test', 'result': normalize(result)})
        guards.append({'label': label, 'fixture': SCENARIOS[scenario_id], 'reads': reads,
            'changes': changes or [], 'steps': steps, 'state': normalize(w.snapshot()), 'checks': w.verify()})
    guard('substitution forbidden', action='reserve_alternative')
    guard('delay forbidden', scenario_id='approved-substitute', action='reserve_incoming')
    guard('cancel revokes fulfillment', scenario_id='cancel-order')
    guard('refund authority', action='refund_payment')
    guard('unknown payment', scenario_id='unknown-payment')
    guard('shipped', scenario_id='already-dispatched', action='refund_payment')
    guard('stale stock', changes=[('inventory', 'version', 8)], decision_changes={'expected_version': 7})
    guard('guessed version', changes=[('inventory', 'version', 8)])
    guard('commit precondition', action='commit_order')
    guard('invented evidence', decision_changes={'evidence_ids':['EV-FAKE']})
    guard('missing authority', reads=1)
    guard('missing citations', decision_changes={'evidence_ids':['EV-01']})
    guard('empty citations', decision_changes={'evidence_ids':[]})
    guard('cancel without refund', scenario_id='cancel-order', action='cancel_order')
    guard('insufficient stock', changes=[('inventory', 'available', 0)])
    guard('stock and ledger corruption', action='verify', changes=[('inventory','available',50),('payment','charge_count',2),('inventory','reservation_sku','WRONG')])
    guard('duplicate reserve', before=[('reserve_original','test')])
    guard('idempotency conflict', action='refund_payment', before=[('reserve_original','test')])
    guard('duplicate refund different key', scenario_id='cancel-order', action='refund_payment', before=[('refund_payment','prior')])
    guard('closed run', before=[('reserve_original','reserve'),('commit_order','commit')])
    output={'cases': cases, 'guards': guards, 'baseline': await fixed_baseline(SCENARIOS['stock-race'])}
    (ROOT/'starter/parity-fixtures.json').write_text(json.dumps(output, ensure_ascii=False, separators=(',',':')), encoding='utf-8')
    print(f'Generated {len(cases)} recovery records and {len(guards)} guard traces from Python; no model calls.')


asyncio.run(main())
