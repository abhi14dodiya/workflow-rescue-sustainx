// Server-only Firestore REST transport. Uses the deployment identity from the
// Google metadata server; no Gemini key, user token or browser credentials.
export class AuditStoreError extends Error{constructor(code){super(`Audit persistence unavailable (${code}). Export this report locally.`);this.code=code;}}
export const configured=()=>Boolean(process.env.FIRESTORE_PROJECT_ID?.trim());
function documentUrl(id){const project=process.env.FIRESTORE_PROJECT_ID?.trim()||'';
  if(!/^[a-z][a-z0-9-]{4,61}[a-z0-9]$/.test(project))throw new AuditStoreError('INVALID_PROJECT');
  if(typeof id!=='string'||!/^[A-Za-z0-9_-]{1,100}$/.test(id))throw new AuditStoreError('INVALID_REPORT_ID');
  return `https://firestore.googleapis.com/v1/projects/${project}/databases/(default)/documents/workflow_rescue_audits/${id}`;
}
async function request(method,url,body){
  let token;
  try{const r=await fetch('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token',{headers:{'Metadata-Flavor':'Google'},signal:AbortSignal.timeout(5000)});if(!r.ok)throw new Error();const data=await r.json();token=data.access_token;if(typeof token!=='string'||!token)throw new Error();}
  catch{throw new AuditStoreError('ADC_UNAVAILABLE');}
  try{return await fetch(url,{method,headers:{Authorization:`Bearer ${token}`,...(body?{'Content-Type':'application/json'}:{})},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(20000)});}
  catch{throw new AuditStoreError('NETWORK');}
}
export async function saveAudit(record){
  if(!configured())return {saved:false,backend:'disabled'};
  try{
    const url=documentUrl(record.id),serialized=JSON.stringify(record);
    if(Buffer.byteLength(serialized)>800000)throw new AuditStoreError('REPORT_TOO_LARGE');
    const response=await request('PATCH',url,{fields:{run_id:{stringValue:record.id},provider:{stringValue:record.provider||'unknown'},created_at:{stringValue:record.created_at||''},report_json:{stringValue:serialized},synthetic_services:{booleanValue:true}}});
    if(![200,201].includes(response.status))throw new AuditStoreError(`HTTP_${response.status}`);
    return {saved:true,backend:'firestore'};
  }catch(e){return {saved:false,backend:'firestore',code:e instanceof AuditStoreError?e.code:'INVALID_REPORT'};}
}
export async function loadAudit(id){
  if(!configured())return null;const response=await request('GET',documentUrl(id));if(response.status===404)return null;
  if(response.status!==200)throw new AuditStoreError(`HTTP_${response.status}`);
  try{const json=await response.json(),text=json.fields.report_json.stringValue;if(typeof text!=='string'||Buffer.byteLength(text)>800000)throw new Error();const record=JSON.parse(text);if(!record||record.id!==id)throw new Error();record.persistence={saved:true,backend:'firestore',restored:true};return record;}
  catch{throw new AuditStoreError('INVALID_STORED_REPORT');}
}
