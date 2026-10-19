import {createServer} from 'node:http';
import {randomBytes,timingSafeEqual} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {gzipSync} from 'node:zlib';
import {clone,now} from './domain.mjs';
import {contracts,providerOptions,validateIncident,incidentFixture,publicIncident,Planner,ProviderError,runRecovery,fixedBaseline} from './runtime.mjs';
import * as audit from './audit-store.mjs';
// Retain only this app's model credentials in the process.
for (const name of Object.keys(process.env)) {
  if (!['GEMINI_API_KEY','GEMINI_MODEL','DEMO_ACCESS_TOKEN'].includes(name)
      && (/API_?KEY|ACCESS_?TOKEN|AUTH_?TOKEN|PASSWORD|SECRET|PRIVATE_KEY/i.test(name)
          || /_(BASE_URL|ENDPOINT|DEPLOYMENT|MODEL|API_VERSION)$/.test(name))) delete process.env[name];
}
const HERE=path.dirname(fileURLToPath(import.meta.url));
// Standalone packaging puts web/ beside this file; repository execution uses ../web.
const WEB=existsSync(path.join(HERE,'web','index.html'))?path.join(HERE,'web'):path.resolve(HERE,'../web');
class HttpError extends Error{constructor(status,message){super(message);this.status=status;}}
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml','.woff2':'font/woff2','.png':'image/png','.jpg':'image/jpeg','.json':'application/json'};
export function createApp({stepDelay=250,saveAudit=audit.saveAudit,loadAudit=audit.loadAudit}={}){
  const runs=new Map();let active=0;
  const maxActive=()=>Math.max(1,Math.min(4,Number(process.env.MAX_ACTIVE_RUNS||2)));
  const getRun=async id=>{if(runs.has(id))return runs.get(id);const stored=await loadAudit(id);if(stored)return stored;throw new HttpError(404,'Run not found or expired. Start a new run.');};
  function access(req,provider){
    if(provider==='rehearsal')return;const token=process.env.DEMO_ACCESS_TOKEN;
    if(token){const a=Buffer.from(String(req.headers['x-demo-token']||'')),b=Buffer.from(token);if(a.length!==b.length||!timingSafeEqual(a,b))throw new HttpError(403,'The configured demo access token is required for live model calls.');}
    if(!providerOptions().find(p=>p.id===provider)?.configured)throw new HttpError(409,'This provider is not configured on the server.');
  }
  async function body(req){
    let size=0;const pieces=[];for await(const piece of req){size+=piece.length;if(size>16384)throw new HttpError(413,'The request body is too large.');pieces.push(piece);}
    try{const value=JSON.parse(Buffer.concat(pieces).toString('utf8'));if(!value||typeof value!=='object'||Array.isArray(value))throw new Error();return value;}
    catch{throw new HttpError(422,'Provide a valid JSON object.');}
  }
  function runRequest(value){
    if(Object.keys(value).some(k=>!['scenario_id','provider','custom_incident'].includes(k)))throw new HttpError(422,'Unexpected request fields.');
    const result={scenario_id:'stock-race',provider:'rehearsal',custom_incident:null,...value};
    if(typeof result.scenario_id!=='string'||!['rehearsal','gemini'].includes(result.provider))throw new HttpError(422,'Invalid scenario or provider.');
    if(result.custom_incident!==null){try{result.custom_incident=validateIncident(result.custom_incident);}catch{throw new HttpError(422,'Invalid custom incident.');}}
    return result;
  }
  return createServer(async(req,res)=>{
    const pathname=new URL(req.url,'http://localhost').pathname;
    res.setHeader('X-Content-Type-Options','nosniff');res.setHeader('Referrer-Policy','same-origin');
    res.setHeader('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'");
    res.setHeader('Cache-Control',pathname.startsWith('/api')?'no-store':pathname.startsWith('/assets/bundle/')?'public, max-age=31536000, immutable':'no-cache');
    function send(status,value,headers={}){res.writeHead(status,{'Content-Type':'application/json; charset=utf-8',...headers});res.end(JSON.stringify(value));}
    try{
      if(req.method==='GET'&&pathname==='/healthz')return send(200,{status:'ok',service:'workflow-rescue',version:'0.1.0'});
      if(req.method==='GET'&&pathname==='/api/config'){
        const providers=providerOptions(),preferred=process.env.DEFAULT_PROVIDER||'rehearsal';
        return send(200,{providers,default_provider:providers.find(p=>p.id===preferred&&p.configured)?.id||'rehearsal',simulated_services:true,run_transport:'stream',live_token_required:Boolean(process.env.DEMO_ACCESS_TOKEN),max_steps:12,storage:audit.configured()?'Firestore stores completed audits; active runs remain in one process.':'Ephemeral single-process demo; reports can be exported.',audit_persistence:audit.configured()});
      }
      if(req.method==='GET'&&pathname==='/api/scenarios')return send(200,contracts.public_scenarios);
      if(req.method==='GET'&&pathname==='/api/incidents/template')return send(200,contracts.incident_template);
      if(req.method==='POST'&&pathname==='/api/incidents/preview'){
        let input;try{input=validateIncident(await body(req));}catch(e){if(e instanceof HttpError)throw e;throw new HttpError(422,'Invalid custom incident.');}
        return send(200,{scenario:publicIncident(incidentFixture(input)),input,simulated_services:true});
      }
      if(req.method==='POST'&&pathname==='/api/provider-check'){
        const input=runRequest(await body(req));access(req,input.provider);
        if(input.provider==='rehearsal')return send(200,{ok:true,provider:'rehearsal',message:'Rehearsal is available. It uses no AI model.'});
        if(active>=maxActive())throw new HttpError(429,'The demo is busy. Try again after an active run finishes.');
        active++;try{const planner=new Planner(input.provider);await planner.generate({task:'Connectivity check only. Return action verify, a brief greeting, empty evidence_ids and expected_version null. There is no business transaction to execute.'});return send(200,{ok:true,provider:input.provider,message:'Live structured model response received and validated.',metrics:planner.metrics});}
        catch(e){if(e instanceof ProviderError)return send(502,{ok:false,error:{code:e.code,message:e.message}});throw e;}finally{active--;}
      }
      if(req.method==='POST'&&pathname==='/api/runs'){
        const input=runRequest(await body(req));
        if(input.scenario_id==='custom'&&!input.custom_incident)throw new HttpError(422,'Provide a validated custom incident before starting.');
        if(input.scenario_id!=='custom'&&input.custom_incident)throw new HttpError(422,'Custom incident data requires scenario_id custom.');
        if(input.scenario_id!=='custom'&&!Object.hasOwn(contracts.scenarios,input.scenario_id))throw new HttpError(404,'Scenario not found.');
        access(req,input.provider);if(active>=maxActive())throw new HttpError(429,'The demo is busy. Try again after an active run finishes.');
        while(runs.size>=100){const id=[...runs].find(([,r])=>!['queued','running'].includes(r.status))?.[0];if(!id)throw new HttpError(429,"The demo's run capacity has been reached.");runs.delete(id);}
        const id=randomBytes(18).toString('base64url');const record={id,provider:input.provider,scenario_id:input.scenario_id,created_at:now(),status:'queued',events:[],checks:[],metrics:{},model:providerOptions().find(p=>p.id===input.provider).model};
        const fixture=input.custom_incident?incidentFixture(input.custom_incident):clone(contracts.scenarios[input.scenario_id]);
        if(input.custom_incident){record.custom_incident=input.custom_incident;record.incident=publicIncident(fixture);}
        runs.set(id,record);active++;
        const streaming=String(req.headers.accept||'').includes('text/event-stream');
        const controller=streaming?new AbortController():null;
        const work=async()=>{try{record.baseline=await fixedBaseline(fixture);await runRecovery(record,fixture,{delay:stepDelay,signal:controller?.signal});controller?.signal.throwIfAborted();const terminal=record.status,stored=clone(record);record.status='running';record.phase='Saving audit';try{record.persistence=await saveAudit(stored);}finally{record.status=terminal;record.phase='Finished';}}
          catch{record.status='error';record.error={code:controller?.signal.aborted?'RUN_INTERRUPTED':'INTERNAL_ERROR',message:controller?.signal.aborted?'The connection closed before recovery finished. Review the recorded actions before starting again.':'The run stopped on an internal error. Review the audit trail before retrying.'};}};
        if(streaming){
          res.writeHead(200,{'Content-Type':'text/event-stream; charset=utf-8','Cache-Control':'no-store','X-Accel-Buffering':'no'});
          const closed=()=>controller.abort();res.once('close',closed);
          let previous='';
          const frame=()=>{if(res.destroyed)return;const data=JSON.stringify(record);res.write(data===previous?': waiting\n\n':`data: ${data}\n\n`);previous=data;};
          frame();const timer=setInterval(frame,400);
          try{await work();frame();}finally{clearInterval(timer);res.removeListener('close',closed);active--;if(!res.destroyed)res.end();}
          return;
        }
        // Retain the polling API for older clients and offline evaluators.
        void work().finally(()=>{active--;});
        return send(202,{id,status:'queued'});
      }
      const match=pathname.match(/^\/api\/runs\/([A-Za-z0-9_-]{1,100})(\/export)?$/);
      if(req.method==='GET'&&match){const record=await getRun(match[1]);return match[2]?send(200,{application:'Workflow Rescue',team:'sustAInX',services:'synthetic simulation',report:record},{'Content-Disposition':'attachment; filename="workflow-rescue-audit.json"'}):send(200,record);}
      if(req.method==='GET'&&(pathname==='/'||pathname.startsWith('/assets/'))){
        const relative=pathname==='/'?'index.html':decodeURIComponent(pathname.slice('/assets/'.length)),target=path.resolve(WEB,relative);
        if(target!==WEB&&!target.startsWith(WEB+path.sep))throw new HttpError(404,'File not found.');
        let data;try{data=await readFile(target);}catch{throw new HttpError(404,'File not found.');}
        const headers={'Content-Type':mime[path.extname(target)]||'application/octet-stream'};
        if(data.length>=1000&&/\bgzip\b/.test(req.headers['accept-encoding']||'')){data=gzipSync(data);headers['Content-Encoding']='gzip';headers.Vary='Accept-Encoding';}
        res.writeHead(200,headers);return res.end(data);
      }
      throw new HttpError(404,'Not found.');
    }catch(e){if(e instanceof HttpError)return send(e.status,{detail:e.message});if(e instanceof audit.AuditStoreError)return send(503,{detail:e.message});return send(500,{detail:'The server could not complete this request.'});}
  });
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const port=Number(process.env.PORT||8080);createApp().listen(port,'0.0.0.0',()=>console.log(`Workflow Rescue listening on port ${port}`));
}
