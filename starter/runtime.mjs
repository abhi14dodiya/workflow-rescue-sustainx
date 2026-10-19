import {readFileSync} from 'node:fs';
import {setTimeout as abortableSleep} from 'node:timers/promises';
import {World, clone, now, READS, validateDecision} from './domain.mjs';
export const contracts=JSON.parse(readFileSync(new URL('./contracts.json',import.meta.url),'utf8'));
export class ProviderError extends Error {constructor(code,message){super(message);this.code=code;}}
let nextCall=0, pacerTail=Promise.resolve();
const calls=[];
export function providerOptions(){return [
  {id:'rehearsal',label:'Rehearsal · no AI',configured:true,model:'Deterministic reference planner'},
  {id:'gemini',label:'Gemini API',configured:Boolean(process.env.GEMINI_API_KEY),model:process.env.GEMINI_MODEL||'gemini-3.5-flash-lite'}
];}
export function validateIncident(input){
  if(!input||typeof input!=='object'||Array.isArray(input))throw new Error('INVALID_INCIDENT');
  const result=clone(contracts.incident_template);
  for(const [key,value] of Object.entries(input)){
    if(!Object.hasOwn(result,key))throw new Error('INVALID_INCIDENT');
    const type=typeof result[key];
    if(typeof value!==type)throw new Error('INVALID_INCIDENT');
    if(type==='number'&&(!Number.isInteger(value)||value<0||value>(key.endsWith('days')?30:100)))throw new Error('INVALID_INCIDENT');
    if(type==='string'&&(value.length<1||value.length>1000))throw new Error('INVALID_INCIDENT');
    result[key]=value;
  }
  return result;
}
export function incidentFixture(input){
  const i=validateIncident(input);
  return {id:'custom',name:'Your custom recovery incident',tag:'Editable incident lab',customer:'Demo Customer',company:'Synthetic operations workspace',summary:'A fresh simulation built from your evidence settings and explicit permissions.',message:i.customer_note,
    policy:Object.fromEntries(['allow_delay','max_delay_days','allow_substitution','cancel_requested'].map(k=>[k,i[k]])),
    ...Object.fromEntries(['available','incoming_available','alternative_available','incoming_days','payment_unknown','shipped','race'].map(k=>[k,i[k]]))};
}
export const publicIncident=fixture=>Object.fromEntries(['id','name','tag','customer','company','summary','message','policy'].map(k=>[k,clone(fixture[k])]));
export function referenceDecision(world,fixed=false){
  const ids=READS.map(t=>world.observed(t)?.id).filter(Boolean);
  const d=(action,explanation,expected_version=null)=>({action,explanation,evidence_ids:ids,expected_version});
  for(const [tool,label] of [
    ['inspect_payment','Check the payment ledger: a timeout may hide a successful charge.'],
    ['inspect_inventory','Read current stock, confirmed arrivals and the inventory version.'],
    ['inspect_dispatch','Check dispatch before changing fulfillment or issuing a refund.']])if(!world.observed(tool))return d(tool,label);
  if(world.observed('inspect_payment').data.status==='unknown')return d('escalate','The payment authority is unavailable. An operator must reconcile the payment before recovery can continue.');
  if(world.observed('inspect_dispatch').data.status!=='not_dispatched')return d('escalate','This order has shipped. An operator must arrange a return before issuing a refund.');
  const effects=new Set([...world.receipts.values()].map(v=>v.result.action));
  if(world.policy.cancel_requested){
    if(!effects.has('refund_payment'))return d('refund_payment','The customer cancelled before dispatch. Refund the existing charge exactly once.');
    return d('cancel_order','The refund is confirmed. Cancel the order and release its reservation.');
  }
  if(['reserve_original','reserve_incoming','reserve_alternative'].some(a=>effects.has(a)))return d('commit_order','The permitted reservation succeeded. Confirm the order against the original payment.');
  if(world.blocked.at(-1)?.code==='STALE_STOCK'){
    if(fixed)return d('escalate','The fixed workflow encountered a stock-version conflict and stopped for an operator, without performing an unsafe retry.');
    if(world.observed('inspect_inventory').data.version===world.blocked.at(-1).invalidated_version)return d('inspect_inventory','The stock changed after the first read. Fetch fresh evidence before selecting another recovery.');
  }
  const inv=world.observed('inspect_inventory').data, version=inv.version;
  if(inv.available>=2)return d('reserve_original','The original model is available. Reserve two units using this exact inventory version.',version);
  if(world.policy.allow_delay&&inv.incoming_days<=world.policy.max_delay_days&&inv.incoming_available>=2)return d('reserve_incoming',`Original stock is unavailable, but confirmed stock arrives in ${inv.incoming_days} day. This meets the customer's approved delay and preserves the exact model.`,version);
  if(world.policy.allow_substitution&&inv.alternative_available>=2)return d('reserve_alternative','The customer explicitly approved Field Kit Plus at the original total. Reserve that alternative without an additional charge.',version);
  return d('escalate','No available recovery meets the approved item and delivery constraints. Ask the customer before changing the promise.');
}
export function retryDelay(status,body,header,attempt){
  if(![429,503].includes(status)||attempt>=2)return null;
  let delay=status===429?60:2**(attempt+1);const hints=[header||''];
  for(const d of body?.error?.details||[]){
    if(d['@type']?.endsWith('QuotaFailure'))for(const v of d.violations||[]){const quota=((v.quotaId||'')+(v.quotaMetric||'')).toLowerCase();if(quota.includes('perday')||quota.includes('per_day')||String(v.quotaValue)==='0')return null;}
    if(d['@type']?.endsWith('RetryInfo'))hints.push(d.retryDelay||'');
  }
  for(const h of hints)if(typeof h==='string'&&/^\d+(?:\.\d+)?s?$/.test(h)){const v=Number(h.replace(/s$/,''));if(!Number.isFinite(v)||v>90)return null;delay=Math.max(delay,v+1);}
  return delay;
}
export class Planner {
  constructor(provider,onWait=null,signal=null){this.provider=provider;this.onWait=onWait;this.signal=signal;this.metrics={calls:0,input_tokens:0,output_tokens:0,model_latency_ms:0,quota_wait_ms:0,retries:0};}
  async next(world){return ['baseline','rehearsal'].includes(this.provider)?referenceDecision(world,this.provider==='baseline'):this.generate(world.agentContext());}
  async pace(){
    const wait=pacerTail.then(async()=>{this.signal?.throwIfAborted();const delay=Math.max(0,nextCall-Date.now());if(delay){this.onWait?.(delay/1000);await abortableSleep(delay,undefined,{signal:this.signal||undefined});this.onWait?.(0);}this.signal?.throwIfAborted();nextCall=Date.now()+15000;this.metrics.quota_wait_ms+=Math.round(delay);});
    pacerTail=wait.catch(()=>{});return wait;
  }
  async generate(context){
    const option=providerOptions().find(p=>p.id===this.provider);
    if(this.provider!=='gemini'||!option?.configured)throw new ProviderError('NOT_CONFIGURED','Configure this provider on the server before starting a live run.');
    if(!/^[a-zA-Z0-9._-]+$/.test(option.model))throw new ProviderError('INVALID_MODEL','The configured model name is invalid.');
    const payload={systemInstruction:{parts:[{text:contracts.system}]},contents:[{role:'user',parts:[{text:JSON.stringify(context)}]}],generationConfig:{maxOutputTokens:4096,responseMimeType:'application/json',responseJsonSchema:contracts.decision_schema}};
    let response,body;
    for(let attempt=0;attempt<3;attempt++){
      await this.pace();
      const current=Date.now();while(calls.length&&current-calls[0]>3600000)calls.shift();
      if(calls.length>=Number(process.env.MAX_MODEL_CALLS_PER_HOUR||120))throw new ProviderError('MODEL_BUDGET',"The demo's hourly model-call budget is exhausted. Use rehearsal mode or try later.");
      calls.push(current);this.metrics.calls++;if(attempt)this.metrics.retries++;
      try{
        response=await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${option.model}:generateContent`,{method:'POST',headers:{'content-type':'application/json','x-goog-api-key':process.env.GEMINI_API_KEY},body:JSON.stringify(payload),signal:this.signal?AbortSignal.any([this.signal,AbortSignal.timeout(40000)]):AbortSignal.timeout(40000)});
        body=await response.json().catch(()=>null);
      }catch(e){throw new ProviderError(e.name==='TimeoutError'?'MODEL_TIMEOUT':'MODEL_CONNECTION',e.name==='TimeoutError'?'The model did not respond within 40 seconds. No proposal from this call was executed.':'The server could not reach the model. Check network, proxy and certificate configuration.');}
      finally{this.metrics.model_latency_ms+=Date.now()-current;}
      const delay=retryDelay(response.status,body,response.headers.get('retry-after'),attempt);if(delay===null)break;nextCall=Math.max(nextCall,Date.now()+delay*1000);
    }
    if(response.status!==200){
      const messages={400:'The provider rejected the request or model configuration. Check the model name and supported structured-output schema.',401:'The provider rejected the credential. Check that the key belongs to this provider and has not expired.',403:'The provider denied access. Check project permissions, model access and API enablement.',404:'The model or endpoint was not found. Choose an available model for this account and region.',429:"The provider's quota or rate limit was reached. Wait for quota to reset or use rehearsal; no paid fallback is enabled.",503:'The model is temporarily unavailable. Try again later; no proposal from this call was executed.'};
      if(!response.headers.get('content-type')?.includes('json'))throw new ProviderError(`GATEWAY_${response.status}`,`A non-JSON network gateway returned HTTP ${response.status}; this does not establish whether the API key is valid.`);
      throw new ProviderError(`HTTP_${response.status}`,messages[response.status]||'The model provider returned an error. No proposal from this call was executed.');
    }
    try{
      const candidate=body.candidates[0];
      if(candidate.finishReason&&!['STOP'].includes(candidate.finishReason))throw new ProviderError('INCOMPLETE_MODEL_OUTPUT','Google did not complete an action response. Check output limits or safety feedback; no proposal from this call was executed.');
      const raw=candidate.content.parts.filter(p=>!p.thought).map(p=>p.text||'').join('');
      this.metrics.input_tokens+=body.usageMetadata?.promptTokenCount||0;this.metrics.output_tokens+=body.usageMetadata?.candidatesTokenCount||0;
      return validateDecision(JSON.parse(raw));
    }catch(e){if(e instanceof ProviderError)throw e;throw new ProviderError('INVALID_MODEL_OUTPUT','The model response did not match the permitted action schema. It was not executed.');}
  }
}
export function observationSummary(obs){const d=obs.data;
  if(obs.tool==='inspect_payment')return d.status==='unknown'?'No authoritative receipt. Payment is unknown, not failed.':`${d.charge_count} charge · $${(d.captured_cents/100).toFixed(2)} captured · $${(d.refunded_cents/100).toFixed(2)} refunded · ${d.receipt}`;
  if(obs.tool==='inspect_inventory')return `Version ${d.version} · ${d.available} original units now · next stock in ${d.incoming_days} day(s) · ${d.reserved_quantity} reserved`;
  return 'Dispatch status: '+d.status.replaceAll('_',' ');
}
export async function runRecovery(record,fixture,{delay=250,signal=null,planner=new Planner(record.provider,null,signal)}={}){
  const world=new World(fixture),started=Date.now();Object.assign(record,{status:'running',events:[],state:world.snapshot(),checks:[],metrics:{}});
  const event=(kind,title,detail,extra={})=>record.events.push({id:record.events.length+1,at:now(),kind,title,detail,...extra});
  planner.onWait=seconds=>{record.phase=seconds?'Waiting for Gemini quota':world.evidence.length<3?'Investigating':'Recovering';if(seconds)event('wait','Respecting Gemini free-tier limits',`Waiting about ${Math.max(1,Math.round(seconds))} seconds before the next model request. No business action is executed during this wait.`);};
  event('incident','Payment timed out. The order stopped.','The original stock reservation expired. Recovery starts by checking what actually happened.');
  try{
    if(!['rehearsal','baseline'].includes(record.provider)){
      event('preflight','Gathering the required service evidence','The controller reads payment, inventory and dispatch. Gemini will choose the recovery action from these observations.');
      for(const tool of READS){const obs=world.observe(tool);event('evidence',obs.source,observationSummary(obs),{evidence_id:obs.id,data:obs.data});}
      record.state=world.snapshot();planner.metrics.preflight_reads=3;
    }
    for(let step=0;step<12;step++){
      signal?.throwIfAborted();
      record.phase=world.evidence.length<3?'Investigating':'Recovering';const d=await planner.next(world);
      event('decision',d.action.replaceAll('_',' ').replace(/^./,c=>c.toUpperCase()),d.explanation,{evidence_ids:d.evidence_ids,action:d.action});if(delay)await abortableSleep(delay,undefined,{signal:signal||undefined});
      signal?.throwIfAborted();
      const result=world.execute(d,`${record.id}:${step}:${d.action}`);
      if(result.observation){const obs=result.observation;event('evidence',obs.source,observationSummary(obs),{evidence_id:obs.id,data:obs.data});}
      else if(!result.ok){event('guard','Plan paused · '+result.code.replaceAll('_',' ').toLowerCase(),result.detail,{code:result.code});if(result.external_change)event('change','Another order took the remaining stock','Inventory moved from version 7 to 8 between observation and reservation. This run must obtain a new snapshot.');}
      else if(d.action==='escalate')event('review','Handed to an operator',result.detail);
      else if(d.action==='verify')event('verification','Intermediate state inspected','Independent checks ran; an unfinished business operation still requires recovery or escalation.');
      else event('action','Executed · '+d.action.replaceAll('_',' '),result.detail,{receipt:result.receipt});
      record.state=world.snapshot();record.metrics={...planner.metrics,steps:step+1,elapsed_ms:Date.now()-started};if(world.outcome)break;
    }
    if(!world.outcome){world.outcome='escalated';world.escalation_reason='The bounded planner reached its 12-step limit. An operator must review the unresolved state.';event('review','Step limit reached',world.escalation_reason);}
    record.phase='Verifying';for(const tool of READS)world.observe(tool);record.checks=world.verify();
    const failures=record.checks.filter(c=>c.status==='fail'),safety=failures.filter(c=>c.category==='safety');
    record.status=failures.length?'failed':world.outcome==='escalated'?'review':'completed';
    event('verification','Independent verification complete',`${record.checks.filter(c=>c.status==='pass').length} passed · ${record.checks.filter(c=>c.status==='review').length} need review · ${safety.length} safety issues.`);
  }catch(e){
    const known=e instanceof ProviderError;record.status='error';record.error={code:known?e.code:'INTERNAL_ERROR',message:known?e.message:'The run stopped on an internal error. Review the audit trail before retrying.'};
    event('error',known?'Model connection stopped':'Recovery stopped',record.error.message,{code:record.error.code});world.outcome='escalated';world.escalation_reason=known?'Live planner stopped. Review any completed actions before retrying.':'Internal execution error; operator review required.';record.checks=world.verify();
  }finally{record.state=world.snapshot();record.metrics={...planner.metrics,steps:record.events.filter(e=>e.kind==='decision').length,elapsed_ms:Date.now()-started,blocked_proposals:world.blocked.length};record.phase='Finished';record.finished_at=now();}
  return record;
}
export async function fixedBaseline(fixture){const record=await runRecovery({id:'baseline',provider:'baseline'},fixture,{delay:0});return {label:'Fixed workflow with guards',scope:'Reads all authorities and uses the same permitted actions. Stops for review after a stock-version conflict; has no adaptive replanning branch.',status:record.status,outcome:record.state.outcome,steps:record.metrics.steps,safety_issues:record.checks.filter(c=>c.status==='fail'&&c.category==='safety').length,note:'A broader rules engine can also solve these fixtures. This comparison alone does not establish AI superiority.'};}
