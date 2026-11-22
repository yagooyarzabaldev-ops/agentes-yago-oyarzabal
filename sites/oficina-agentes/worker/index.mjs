// The private Site gateway authenticates visitors and the existing service token.
// No raw Codex session, prompt, tool arguments, or credentials are accepted here.
const ASSETS = /*__ASSET_MAP__*/ {};
const KEY = 'office/live-state.json';
const json = (body, status=200) => new Response(JSON.stringify(body), {status, headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});

function cleanRun(r) {
  const text = (x,n=200) => typeof x==='string'?x.slice(0,n):null;
  return {run_id:text(r.run_id,100),agent_id:text(r.agent_id,60),job_id:text(r.job_id,80),task:text(r.task),
    skill_id:text(r.skill_id,80),skill_evidence:text(r.skill_evidence,80),source:text(r.source,50),
    started_at:text(r.started_at,50),heartbeat_at:text(r.heartbeat_at,50),finished_at:text(r.finished_at,50),
    status:text(r.status,30),verified_active:r.verified_active===true,exit_code:Number.isInteger(r.exit_code)?r.exit_code:null};
}
function normalizeSnapshot(s) {
  if(s?.schema_version!==1||!Array.isArray(s.agents)||s.agents.length>100||!Array.isArray(s.jobs)||!Array.isArray(s.skills))throw new Error('Invalid snapshot');
  // The local exporter has already minimized historical metadata. Live runs use an additional whitelist.
  return {...s,runs:(s.runs||[]).slice(0,100).map(cleanRun),agents:s.agents.map(a=>({...a,live_runs:(a.live_runs||[]).map(cleanRun),last_run:a.last_run?cleanRun(a.last_run):null}))};
}
export default {
  async fetch(request,env) {
    const url=new URL(request.url),path=url.pathname;
    if(path==='/api/ingest') {
      if(request.method!=='POST')return json({error:'Method not allowed'},405);
      const origin=request.headers.get('Origin');
      if(origin&&origin!==url.origin)return json({error:'Origin not allowed'},403);
      if(!(request.headers.get('Content-Type')||'').includes('application/json'))return json({error:'JSON required'},415);
      if(Number(request.headers.get('Content-Length')||0)>1_000_000)return json({error:'Too large'},413);
      if(!env.BUCKET)return json({error:'Storage unavailable'},503);
      try {
        const raw=await request.text();if(raw.length>1_000_000)return json({error:'Too large'},413);
        const snapshot=normalizeSnapshot(JSON.parse(raw)),received_at=new Date().toISOString();
        await env.BUCKET.put(KEY,JSON.stringify({snapshot,received_at}),{httpMetadata:{contentType:'application/json'}});
        return json({ok:true,received_at});
      } catch {return json({error:'Invalid state'},400);}
    }
    if(path==='/api/office') {
      if(request.method!=='GET')return json({error:'Method not allowed'},405);
      const stored=await env.BUCKET?.get(KEY);
      if(!stored)return json({error:'El monitor local todavía no envió actividad.'},503);
      const {snapshot,received_at}=await stored.json();
      const age=Date.now()-Date.parse(received_at),connected=Number.isFinite(age)&&age>=0&&age<20000;
      snapshot.source={...snapshot.source,mode:'remote',stream_available:false,remote_received_at:received_at,remote_connected:connected,notice:connected?'Actividad enviada desde tu proyecto.':'El monitor local perdió conexión; se conserva la última lectura.'};
      if(!connected){snapshot.summary.active_verified=0;snapshot.summary.active_runs=0;for(const a of snapshot.agents){if(a.live_status==='active'){a.live_status='stale';a.live_status_label='Sin señal del proyecto';}a.live_runs=[];}snapshot.runs=(snapshot.runs||[]).map(r=>({...r,status:r.status==='active'?'stale':r.status,verified_active:false}));}
      return json(snapshot);
    }
    if(request.method!=='GET'&&request.method!=='HEAD')return json({error:'Method not allowed'},405);
    const asset=ASSETS[path==='/'?'/index.html':path];
    if(!asset)return new Response('Not found',{status:404});
    return new Response(request.method==='HEAD'?null:asset.body,{headers:{'Content-Type':asset.type,'Cache-Control':'no-cache','X-Content-Type-Options':'nosniff','Referrer-Policy':'same-origin'}});
  }
};
