import test from 'node:test';
import assert from 'node:assert/strict';
import {createApp} from './server.mjs';

test('managed-host stream carries live progress and waits for persistence', async()=>{
  const app=createApp({stepDelay:80,saveAudit:async()=>{await new Promise(r=>setTimeout(r,450));return {saved:true,backend:'firestore'};},loadAudit:async()=>null});
  await new Promise(resolve=>app.listen(0,'127.0.0.1',resolve));
  try{
    const response=await fetch(`http://127.0.0.1:${app.address().port}/api/runs`,{method:'POST',headers:{'content-type':'application/json',accept:'text/event-stream'},body:JSON.stringify({scenario_id:'straight-recovery',provider:'rehearsal'})});
    const frames=(await response.text()).split('\n').filter(line=>line.startsWith('data: ')).map(line=>JSON.parse(line.slice(6)));
    assert.equal(frames[0].status,'queued');
    assert.ok(frames.some(r=>r.status==='running'));
    assert.ok(frames.some(r=>r.phase==='Saving audit'&&r.status==='running'));
    assert.equal(frames.at(-1).status,'completed');
    assert.equal(frames.at(-1).persistence.saved,true);
  }finally{app.closeAllConnections();await new Promise(resolve=>app.close(resolve));}
});

test('client disconnection frees capacity and prevents further recovery actions',async()=>{
  const previous=process.env.MAX_ACTIVE_RUNS;process.env.MAX_ACTIVE_RUNS='1';
  const app=createApp({stepDelay:1000,saveAudit:async()=>({saved:false,backend:'disabled'}),loadAudit:async()=>null});
  await new Promise(resolve=>app.listen(0,'127.0.0.1',resolve));const base=`http://127.0.0.1:${app.address().port}`;
  try{
    const abort=new AbortController();
    const response=await fetch(base+'/api/runs',{method:'POST',headers:{'content-type':'application/json',accept:'text/event-stream'},body:'{"provider":"rehearsal"}',signal:abort.signal});
    const reader=response.body.getReader();const first=await reader.read();const id=JSON.parse(new TextDecoder().decode(first.value).split('data: ')[1].split('\n')[0]).id;
    abort.abort();await reader.cancel().catch(()=>{});
    let record;
    for(let i=0;i<30;i++){record=await (await fetch(base+'/api/runs/'+id)).json();if(record.status==='error')break;await new Promise(r=>setTimeout(r,20));}
    assert.equal(record.error.code,'RUN_INTERRUPTED');
    assert.equal(record.state.effects.length,0);
    const secondAbort=new AbortController();
    const next=await fetch(base+'/api/runs',{method:'POST',headers:{'content-type':'application/json',accept:'text/event-stream'},body:'{"provider":"rehearsal"}',signal:secondAbort.signal});
    assert.equal(next.status,200);secondAbort.abort();await next.body.cancel().catch(()=>{});
  }finally{if(previous===undefined)delete process.env.MAX_ACTIVE_RUNS;else process.env.MAX_ACTIVE_RUNS=previous;app.closeAllConnections();await new Promise(resolve=>app.close(resolve));}
});
