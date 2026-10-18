import asyncio
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.incidents import IncidentInput
from app.main import app
from app.runner import run_recovery


@pytest.mark.parametrize('settings, expected', [
    ({'available':0, 'incoming_available':0, 'alternative_available':0, 'race':False}, 'escalated'),
    ({'available':0, 'allow_delay':False, 'allow_substitution':True, 'race':False}, 'recovered'),
    ({'payment_unknown':True, 'cancel_requested':True}, 'escalated'),
    ({'shipped':True, 'cancel_requested':True}, 'escalated'),
    ({'cancel_requested':True}, 'cancelled'),
])
def test_custom_evidence_changes_actual_outcome(settings, expected):
    record = asyncio.run(run_recovery({'id':'custom-check', 'provider':'rehearsal'}, IncidentInput(**settings).fixture(), delay=0))
    assert record['state']['outcome'] == expected
    assert not any(c['status']=='fail' for c in record['checks'] if c['category']=='safety')
    assert record['state']['policy']['additional_charge_allowed'] is False


def test_incident_import_cannot_expand_authority_or_supply_an_answer():
    for extra in ({'additional_charge_allowed':True}, {'expected':'recovered'}, {'available':-1}, {'payment_unknown':'false'}):
        with pytest.raises(ValidationError):
            IncidentInput(**extra)


def test_custom_preview_is_read_only_and_validated():
    with TestClient(app) as client:
        template = client.get('/api/incidents/template').json()
        result = client.post('/api/incidents/preview', json=template)
        assert result.status_code == 200
        assert result.json()['scenario']['id'] == 'custom'
        assert client.post('/api/incidents/preview', json={'available':1000}).status_code == 422
        assert client.post('/api/runs', json={'scenario_id':'custom'}).status_code == 422
        assert client.post('/api/runs', json={'custom_incident':template}).status_code == 422
