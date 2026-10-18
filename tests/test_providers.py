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

@pytest.mark.parametrize('provider,location', [('gemini','global'), ('vertex','global'), ('vertex','us-central1')])
def test_google_auth_routing_schema_and_thought_filter(monkeypatch, provider, location):
    from types import SimpleNamespace
    import google.auth
    monkeypatch.setenv('GEMINI_API_KEY', 'gemini-test-only')
    monkeypatch.setenv('GOOGLE_CLOUD_PROJECT', 'example-project')
    monkeypatch.setenv('GOOGLE_CLOUD_LOCATION', location)
    monkeypatch.setenv('GEMINI_MODEL', 'gemini-3.8-flash')
    monkeypatch.setenv('VERTEX_MODEL', 'gemini-3.8-flash')
    credentials = SimpleNamespace(token='runtime-test-token', refresh=lambda request: None)
    monkeypatch.setattr(google.auth, 'default', lambda **kw: (credentials, 'example-project'))
    proposal = {'action':'inspect_payment','explanation':'Inspect the receipt.','evidence_ids':[],'expected_version':None}
    def respond(request):
        if provider == 'gemini':
            assert request.url.host == 'generativelanguage.googleapis.com'
            assert request.headers['x-goog-api-key'] == 'gemini-test-only'
            assert 'authorization' not in request.headers
        else:
            assert request.url.host == ('aiplatform.googleapis.com' if location == 'global' else f'{location}-aiplatform.googleapis.com')
            assert f'/projects/example-project/locations/{location}/' in request.url.path
            assert request.headers['authorization'] == 'Bearer runtime-test-token'
            assert 'x-goog-api-key' not in request.headers
        assert request.url.path.endswith('/gemini-3.8-flash:generateContent')
        payload = json.loads(request.content)
        assert payload['generationConfig']['responseMimeType'] == 'application/json'
        assert 'action' in payload['generationConfig']['responseJsonSchema']['required']
        assert 'temperature' not in payload['generationConfig']  # use the model's documented default
        return httpx.Response(200, json={'candidates':[{'finishReason':'STOP','content':{'parts':[
            {'thought':True,'text':'Non-action text must never enter the action parser.'},
            {'text':json.dumps(proposal)}
        ]}}]})
    original = httpx.AsyncClient
    monkeypatch.setattr(agent.httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(respond), **kw))
    assert asyncio.run(Planner(provider).generate({'test':'request'})).action == 'inspect_payment'

def configure_azure(monkeypatch):
    monkeypatch.setenv('AZURE_OPENAI_API_KEY', 'azure-test-secret')
    monkeypatch.setenv('AZURE_OPENAI_BASE_URL', 'https://example.openai.azure.com/openai/v1/')
    monkeypatch.setenv('AZURE_OPENAI_DEPLOYMENT', 'recovery-deployment')
    monkeypatch.setenv('OPENAI_API_KEY', 'unrelated-openai-secret')

def test_azure_uses_its_own_endpoint_deployment_and_key(monkeypatch):
    configure_azure(monkeypatch)
    proposal = {'action':'inspect_payment','explanation':'Inspect the receipt.','evidence_ids':[],'expected_version':None}
    def respond(request):
        assert str(request.url) == 'https://example.openai.azure.com/openai/v1/responses'
        assert request.headers['api-key'] == 'azure-test-secret'
        assert 'authorization' not in request.headers
        payload = json.loads(request.content)
        assert payload['model'] == 'recovery-deployment' and payload['store'] is False
        schema = payload['text']['format']['schema']
        assert schema['additionalProperties'] is False
        assert set(schema['required']) == set(proposal)
        return httpx.Response(200,json={'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps(proposal)}]}],'usage':{'input_tokens':20,'output_tokens':12}})
    original = httpx.AsyncClient
    monkeypatch.setattr(agent.httpx,'AsyncClient',lambda **kw: original(transport=httpx.MockTransport(respond),**kw))
    planner=Planner('azure')
    assert asyncio.run(planner.generate({'test':'azure'})).action == 'inspect_payment'
    assert planner.metrics['calls'] == 1 and planner.metrics['input_tokens'] == 20

@pytest.mark.parametrize('body,code', [
    ({'status':'incomplete','output':[]}, 'INCOMPLETE_MODEL_OUTPUT'),
    ({'status':'completed','output':[{'content':[{'type':'refusal','refusal':'Declined'}]}]}, 'MODEL_REFUSAL'),
    ({'status':'completed','output':[{'content':[{'type':'output_text','text':'{"action":"charge_again"}'}]}]}, 'INVALID_MODEL_OUTPUT'),
])
def test_azure_does_not_execute_incomplete_refused_or_invalid_output(monkeypatch,body,code):
    configure_azure(monkeypatch)
    mock_http(monkeypatch,httpx.Response(200,json=body))
    with pytest.raises(ProviderError) as caught:
        asyncio.run(Planner('azure').generate({'test':'rejected output'}))
    assert caught.value.code == code

def test_azure_auth_failure_is_sanitized_without_fallback(monkeypatch):
    configure_azure(monkeypatch)
    mock_http(monkeypatch,httpx.Response(401,json={'error':'azure-test-secret'}))
    planner=Planner('azure')
    with pytest.raises(ProviderError) as caught:
        asyncio.run(planner.generate({'test':'auth'}))
    assert caught.value.code == 'HTTP_401'
    assert 'azure-test-secret' not in str(caught.value)
    assert planner.metrics['calls'] == 1


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
