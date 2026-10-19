import asyncio
import json
import httpx
import pytest
from app import agent
from app.agent import Planner, ProviderError

@pytest.fixture(autouse=True)
def isolated_quota_clock(monkeypatch):
    current = [0.0]
    async def sleep(seconds):
        current[0] += seconds
    monkeypatch.setattr(agent, 'GEMINI_PACER', agent.GeminiPacer(clock=lambda: current[0], sleep=sleep))
    monkeypatch.setattr(agent, 'BUDGET', agent.CallBudget())
    return current

def mock_http(monkeypatch, response):
    original = httpx.AsyncClient
    monkeypatch.setattr(agent.httpx,"AsyncClient",lambda **kw: original(transport=httpx.MockTransport(lambda request: response),**kw))

@pytest.mark.parametrize("status,content_type,code", [(401,"application/json","HTTP_401"),(403,"text/html","GATEWAY_403"),(429,"application/json","HTTP_429")])
def test_provider_error_is_sanitized_and_classified(monkeypatch,status,content_type,code):
    monkeypatch.setenv("GEMINI_API_KEY","secret-that-must-not-leak")
    mock_http(monkeypatch,httpx.Response(status,headers={"content-type":content_type},text="secret-that-must-not-leak"))
    with pytest.raises(ProviderError) as caught:
        asyncio.run(Planner("gemini").generate({"test":"request"}))
    assert caught.value.code == code
    assert "secret-that-must-not-leak" not in str(caught.value)

def test_gemini_typed_response_is_validated_and_usage_recorded(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY","test-only")
    proposal = {"action":"inspect_payment","explanation":"Check the receipt.","evidence_ids":[],"expected_version":None}
    mock_http(monkeypatch,httpx.Response(200,json={"candidates":[{"content":{"parts":[{"text":json.dumps(proposal)}]}}],"usageMetadata":{"promptTokenCount":27,"candidatesTokenCount":19}}))
    planner=Planner("gemini")
    d=asyncio.run(planner.generate({"test":"request"}))
    assert d.action == "inspect_payment"
    assert planner.metrics["input_tokens"] == 27 and planner.metrics["calls"] == 1

def test_invalid_model_tool_is_rejected_before_execution(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY","test-only")
    mock_http(monkeypatch,httpx.Response(200,json={"candidates":[{"content":{"parts":[{"text":'{"action":"charge_again"}'}]}}]}))
    with pytest.raises(ProviderError) as caught:
        asyncio.run(Planner("gemini").generate({"test":"request"}))
    assert caught.value.code == "INVALID_MODEL_OUTPUT"

@pytest.mark.parametrize('finish_reason', ['MAX_TOKENS', 'SAFETY', 'RECITATION'])
def test_google_incomplete_or_blocked_response_cannot_propose_action(monkeypatch, finish_reason):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only')
    proposal = {'action':'inspect_payment','explanation':'Inspect.','evidence_ids':[],'expected_version':None}
    mock_http(monkeypatch, httpx.Response(200, json={'candidates':[{
        'finishReason':finish_reason, 'content':{'parts':[{'text':json.dumps(proposal)}]}
    }]}))
    with pytest.raises(ProviderError) as caught:
        asyncio.run(Planner('gemini').generate({'test':'request'}))
    assert caught.value.code == 'INCOMPLETE_MODEL_OUTPUT'

def test_gemini_auth_schema_and_thought_filter(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'gemini-test-only')
    monkeypatch.setenv('GEMINI_MODEL', 'gemini-3.5-flash-lite')
    proposal = {'action':'inspect_payment','explanation':'Inspect the receipt.','evidence_ids':[],'expected_version':None}
    def respond(request):
        assert request.url.host == 'generativelanguage.googleapis.com'
        assert request.headers['x-goog-api-key'] == 'gemini-test-only'
        assert 'authorization' not in request.headers
        assert request.url.path.endswith('/gemini-3.5-flash-lite:generateContent')
        payload = json.loads(request.content)
        assert payload['generationConfig']['responseMimeType'] == 'application/json'
        assert set(payload['generationConfig']['responseJsonSchema']['required']) == set(proposal)
        assert 'temperature' not in payload['generationConfig']
        return httpx.Response(200, json={'candidates':[{'finishReason':'STOP','content':{'parts':[
            {'thought':True,'text':'Non-action text must never enter the action parser.'},
            {'text':json.dumps(proposal)}
        ]}}]})
    original = httpx.AsyncClient
    monkeypatch.setattr(agent.httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(respond), **kw))
    assert asyncio.run(Planner('gemini').generate({'test':'request'})).action == 'inspect_payment'


def test_unrecognized_provider_cannot_make_network_request(monkeypatch):
    def unexpected_client(**kwargs):
        pytest.fail('An unsupported provider reached the network.')
    monkeypatch.setattr(agent.httpx, 'AsyncClient', unexpected_client)
    with pytest.raises(ProviderError, match='Configure'):
        asyncio.run(Planner('unsupported-provider').generate({}))


def typed_response():
    proposal = {'action':'inspect_payment','explanation':'Inspect.','evidence_ids':[],'expected_version':None}
    return httpx.Response(200, json={'candidates':[{'finishReason':'STOP', 'content':{'parts':[{'text':json.dumps(proposal)}]}}]})


def test_gemini_shares_spacing_between_planners(monkeypatch, isolated_quota_clock):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only')
    mock_http(monkeypatch, typed_response())
    waits = []
    async def run():
        await Planner('gemini').generate({})
        second = Planner('gemini', on_wait=waits.append)
        await second.generate({})
        return second
    planner = asyncio.run(run())
    assert isolated_quota_clock[0] == 15
    assert waits == [15, 0]
    assert planner.metrics['quota_wait_ms'] == 15000


def test_gemini_retries_rejected_generation_with_same_payload(monkeypatch, isolated_quota_clock):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only')
    bodies = []
    responses = iter([httpx.Response(429, headers={'Retry-After':'70'}, json={'error':{}}),
                      httpx.Response(503, json={'error':{}}), typed_response()])
    def respond(request):
        bodies.append(request.content)
        return next(responses)
    original = httpx.AsyncClient
    monkeypatch.setattr(agent.httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(respond), **kw))
    planner = Planner('gemini')
    assert asyncio.run(planner.generate({})).action == 'inspect_payment'
    assert planner.metrics['calls'] == len(agent.BUDGET.calls) == 3
    assert planner.metrics['retries'] == 2
    assert isolated_quota_clock[0] == 86
    assert bodies[0] == bodies[1] == bodies[2]


@pytest.mark.parametrize('quota', ['GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'generate_requests_per_day'])
def test_gemini_daily_quota_stops_without_retry(monkeypatch, quota):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only')
    mock_http(monkeypatch, httpx.Response(429, json={'error':{'details':[
        {'@type':'type.googleapis.com/google.rpc.QuotaFailure', 'violations':[{'quotaId':quota}]}]}}))
    planner = Planner('gemini')
    with pytest.raises(ProviderError, match='quota'):
        asyncio.run(planner.generate({}))
    assert planner.metrics['calls'] == 1


def test_gemini_persistent_unavailability_is_bounded(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only')
    mock_http(monkeypatch, httpx.Response(503, json={'error':{'message':'test-only'}}))
    planner = Planner('gemini')
    with pytest.raises(ProviderError) as caught:
        asyncio.run(planner.generate({}))
    assert caught.value.code == 'HTTP_503'
    assert planner.metrics['calls'] == 3
    assert 'test-only' not in str(caught.value)


def test_gemini_retries_cannot_bypass_local_budget(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only')
    monkeypatch.setenv('MAX_MODEL_CALLS_PER_HOUR', '1')
    mock_http(monkeypatch, httpx.Response(429, json={'error':{}}))
    planner = Planner('gemini')
    with pytest.raises(ProviderError) as caught:
        asyncio.run(planner.generate({}))
    assert caught.value.code == 'MODEL_BUDGET'
    assert planner.metrics['calls'] == 1


def test_google_long_retry_hint_is_not_shortened():
    response = httpx.Response(429, json={'error':{'details':[
        {'@type':'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay':'3600s'}]}})
    assert agent.gemini_retry_delay(response, 0) is None
