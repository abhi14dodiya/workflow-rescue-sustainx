import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {World,READS,validateDecision} from './domain.mjs';
import {contracts,runRecovery,fixedBaseline,validateIncident,incidentFixture,Planner,ProviderError,retryDelay} from './runtime.mjs';
import {createApp} from './server.mjs';
const parity=JSON.parse(readFileSync(new URL('./parity-fixtures.json',import.meta.url),'utf8'));
function normalize(value){if(Array.isArray(value))return value.map(normalize);if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).filter(([k])=>!['at','finished_at','elapsed_ms'].includes(k)).map(([k,v])=>[k,normalize(v)]));return value;}
for(const [index,c] of parity.cases.entries())test(`Python equivalence ${index}: ${c.fixture.id} ${c.provider}`,async()=>{
  const actual=await runRecovery({id:c.id,provider:c.provider},c.fixture,{delay:0});assert.deepEqual(normalize(actual),c.expected);
});
for(const c of parity.guards)test(`Python guard equivalence: ${c.label}`,()=>{
  const w=new World(c.fixture);for(const t of READS.slice(0,c.reads))w.observe(t);for(const [container,key,value] of c.changes)w[container][key]=value;
  for(const step of c.steps)assert.deepEqual(normalize(w.execute(step.decision,step.key)),step.result);
  assert.deepEqual(normalize(w.snapshot()),c.state);assert.deepEqual(w.verify(),c.checks);
});
test('same guarded baseline',async()=>assert.deepEqual(await fixedBaseline(contracts.scenarios['stock-race']),parity.baseline));
test('incident strict bounds and unknown keys',()=>{
  for(const bad of [{available:true},{available:'2'},{available:-1},{available:101},{incoming_days:31},{available:1.5},{allow_delay:1},{customer_note:''},{customer_note:'x'.repeat(1001)},{shell:'arbitrary'}])assert.throws(()=>validateIncident(bad));
  assert.equal(incidentFixture({cancel_requested:true}).policy.cancel_requested,true);
});
test('decision schema rejects unauthorized actions and extras',()=>{
  const base={action:'verify',explanation:'Check',evidence_ids:[],expected_version:null};assert.deepEqual(validateDecision(base),base);
  for(const bad of [{...base,action:'charge_customer'},{...base,shell:'arbitrary'},{...base,expected_version:true},{...base,evidence_ids:['EV-1',123]}])assert.throws(()=>validateDecision(bad));
});
test('live failure never falls back and 12-step limit stops',async()=>{
  const metrics={calls:0};const failure={metrics,next:async()=>{throw new ProviderError('HTTP_401','Credential rejected');}};
  const failed=await runRecovery({id:'failure',provider:'gemini'},contracts.scenarios['stock-race'],{delay:0,planner:failure});assert.equal(failed.status,'error');assert.equal(failed.error.code,'HTTP_401');assert.deepEqual(failed.state.effects,[]);
  const looping={metrics:{calls:0},next:async()=>({action:'inspect_payment',explanation:'Read again',evidence_ids:[],expected_version:null})};
  const limited=await runRecovery({id:'limit',provider:'gemini'},contracts.scenarios['stock-race'],{delay:0,planner:looping});assert.equal(limited.status,'review');assert.equal(limited.metrics.steps,12);assert.deepEqual(limited.state.effects,[]);
});
test('daily quota exhaustion stops; short transient delay is bounded',()=>{
  assert.equal(retryDelay(429,{error:{details:[{'@type':'google.rpc.QuotaFailure',violations:[{quotaId:'GenerateRequestsPerDay'}]}]}},'',0),null);
  assert.equal(retryDelay(429,{},'120',0),null);assert.equal(retryDelay(503,{},'',0),2);assert.equal(retryDelay(429,{},'12s',0),60);assert.equal(retryDelay(503,{},'',2),null);
});
test('Gemini transport uses a server header and validates fresh structured output (mock only)',async()=>{
  const original=global.fetch,old=process.env.GEMINI_API_KEY;process.env.GEMINI_API_KEY='test-only';let requests=0;
  try{global.fetch=async(url,options)=>{requests++;assert.match(url,/generativelanguage\.googleapis\.com/);assert.equal(options.headers['x-goog-api-key'],'test-only');assert.equal(url.includes('test-only'),false);const payload=JSON.parse(options.body);assert.equal(payload.generationConfig.responseMimeType,'application/json');return new Response(JSON.stringify({candidates:[{finishReason:'STOP',content:{parts:[{text:JSON.stringify({action:'verify',explanation:'Hello',evidence_ids:[],expected_version:null})}]}}],usageMetadata:{promptTokenCount:2,candidatesTokenCount:3}}),{status:200,headers:{'content-type':'application/json'}});};
    const planner=new Planner('gemini');assert.equal((await planner.generate({task:'test'})).action,'verify');assert.equal(planner.metrics.calls,1);assert.equal(requests,1);
  }finally{global.fetch=original;if(old===undefined)delete process.env.GEMINI_API_KEY;else process.env.GEMINI_API_KEY=old;}
});
test('HTTP custom run, static assets, strict validation, saved audit and export',async()=>{
  const app=createApp({stepDelay:0,saveAudit:async record=>{assert.equal(record.status,'completed');return {saved:true,backend:'firestore'};},loadAudit:async()=>null});
  await new Promise(resolve=>app.listen(0,'127.0.0.1',resolve));const base=`http://127.0.0.1:${app.address().port}`;
  const post=(route,value)=>fetch(base+route,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(value)});
  try{
    const home=await fetch(base+'/');assert.equal(home.status,200);assert.match(home.headers.get('content-security-policy'),/frame-ancestors/);const html=await home.text();const script=html.match(/<script[^>]+src="([^"]+)"/)[1];const asset=await fetch(base+script);assert.equal(asset.status,200);assert.match(asset.headers.get('cache-control'),/immutable/);
    assert.equal((await post('/api/runs',{provider:'unsupported'})).status,422);assert.equal((await post('/api/runs',{scenario_id:'missing'})).status,404);assert.equal((await post('/api/incidents/preview',{available:true})).status,422);
    const request={scenario_id:'custom',provider:'rehearsal',custom_incident:{...contracts.incident_template,cancel_requested:true,race:false}};
    const response=await post('/api/runs',request);assert.equal(response.status,202);const start=await response.json();let record;
    for(let i=0;i<40;i++){record=await (await fetch(base+'/api/runs/'+start.id)).json();if(!['running','queued'].includes(record.status))break;await new Promise(r=>setTimeout(r,5));}
    assert.equal(record.state.outcome,'cancelled');assert.equal(record.persistence.saved,true);assert.equal(record.metrics.calls,0);
    const exported=await (await fetch(base+'/api/runs/'+start.id+'/export')).json();assert.equal(exported.services,'synthetic simulation');assert.equal(exported.report.provider,'rehearsal');
  }finally{await new Promise(resolve=>app.close(resolve));}
});
