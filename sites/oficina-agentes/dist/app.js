const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const color = value => /^#[0-9a-f]{6}$/i.test(value || '') ? value : '#b9a4f4';
const date = value => { if (!value) return 'Sin fecha registrada'; const d = new Date(value); return Number.isNaN(d.getTime()) ? 'Sin fecha válida' : d.toLocaleString('es-AR', {timeZone:'America/Argentina/Buenos_Aires',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}); };
let data, selected, office, activeView = 'oficina', activeArea = '', sourceMode = '', refreshing = false;
let imported = false, disconnected = false;
let renderedSignature = '';
let eventStream, lastSignalAt=0;
const isLocal=['127.0.0.1','localhost','[::1]'].includes(location.hostname);
const liveStateLabels={active:'Trabajando ahora',idle:'En espera',completed:'Trabajo terminado',error:'Error de ejecución',stale:'Sin señal reciente',interrupted:'Interrumpido'};
function stateLabel(a){return a.live_status_label||liveStateLabels[a.live_status]||a.status_label;}
function skillDescription(a){if(!a.current_skill)return 'Contrato propio · sin skill externa registrada';if(a.skill_evidence==='instructions_read_in_turn')return `${a.current_skill} · instrucciones leídas en este turno`;if(a.skill_evidence==='declared_by_operator')return `${a.current_skill} · declarada por el ejecutor`;return `${a.current_skill} · herramienta ejecutándose`;}
function signatureOf(value){return JSON.stringify(value,(k,v)=>['generated_at','heartbeat_at','heartbeat_age_seconds','remote_received_at'].includes(k)?undefined:v);}
function acceptState(next,mode){data=next;sourceMode=mode;lastSignalAt=Date.now();disconnected=next.source.remote_connected===false;const signature=signatureOf(data);if(signature!==renderedSignature){renderAll();renderedSignature=signature;}else renderSource();}
function loseSignal(){if(!data||imported||sourceMode==='snapshot')return;disconnected=true;for(const a of data.agents){if(a.live_status==='active'){a.live_status='stale';a.live_status_label='Sin señal reciente';}a.live_runs=[];}data.summary.active_verified=0;data.summary.active_runs=0;renderedSignature='';renderAll();showNotice('Se perdió la señal del proyecto. Los puestos dejaron de mostrar trabajo en curso hasta reconectar.');}
function connectEvents(){if(!isLocal||eventStream||imported)return;eventStream=new EventSource('/api/events');eventStream.addEventListener('office',e=>{try{acceptState(checkSnapshot(JSON.parse(e.data)),'local');}catch{loseSignal();}});eventStream.addEventListener('heartbeat',()=>{lastSignalAt=Date.now();if(disconnected)refresh();});eventStream.onerror=()=>loseSignal();}
const viewTitles = {oficina:['El equipo, en un mismo lugar.','Recorré la oficina. Conocé a cada agente y seguí lo que ya está registrado.','Oficina 3D'],equipo:['Personas detrás del proceso.','Los 14 roles del proyecto, con sus responsabilidades y últimas evidencias.','Equipo'],skills:['Cada rol, con sus herramientas.','Explorá las skills disponibles y su relación con el trabajo del equipo.','Skills'],actividad:['El proceso deja huella.','Trabajos, etapas guardadas y próximos pasos. Cada avance tiene una fuente.','Actividad']};
function toast(message) { const el=$('#toast'); el.textContent=message; el.classList.add('visible'); clearTimeout(toast.timer); toast.timer=setTimeout(()=>el.classList.remove('visible'),4000); }
function showNotice(message='') { $('#notice').textContent=message; $('#notice').classList.toggle('visible',!!message); }
function avatar(agent) { return `<div class="agent-avatar" style="--agent-color:${color(agent.color)}"><span class="robot-antenna"></span><span class="robot-face"></span></div>`; }
function empty(title,body) { return `<div class="empty"><strong>${esc(title)}</strong>${esc(body)}</div>`; }
function checkSnapshot(value) {
  if (!value || value.schema_version !== 1 || !value.source || !Array.isArray(value.agents) || !Array.isArray(value.jobs) || !Array.isArray(value.skills) || !Array.isArray(value.activity) || !Array.isArray(value.evidence)) throw new Error('El archivo no es un estado compatible de Infinite Office.');
  if(value.agents.length>100 || value.jobs.length>1000) throw new Error('El estado supera el tamaño admitido.');
  const ids = new Set();
  for(const a of value.agents) { if(typeof a.id!=='string'||ids.has(a.id)||!Array.isArray(a.skills)||!Array.isArray(a.inputs)||!Array.isArray(a.outputs)||typeof a.short_name!=='string'||typeof a.name!=='string'||typeof a.department!=='string'||!a.skills.every(s=>s&&typeof s.id==='string'&&typeof s.name==='string')) throw new Error('Hay una ficha de agente inválida.'); ids.add(a.id); }
  if(!value.jobs.every(j=>j&&typeof j.id==='string'&&Array.isArray(j.completed_agents)&&Array.isArray(j.pending_agents))||!value.skills.every(s=>s&&typeof s.id==='string'&&Array.isArray(s.agent_ids))||!value.activity.every(e=>e&&typeof e.title==='string')||!value.evidence.every(e=>e&&typeof e.title==='string')) throw new Error('El estado contiene registros incompletos.');
  return value;
}
async function getJSON(url) {
  const response=await fetch(url,{cache:'no-store',signal:AbortSignal.timeout(9000)});
  if(!response.ok) throw new Error('No se pudo leer el estado del proyecto.');
  return checkSnapshot(await response.json());
}
async function refresh(manual=false) {
  if(refreshing || (imported && !manual)) return;
  refreshing=true; $('#refresh').disabled=true;
  try {
    let next;
    if(isLocal) {
      try { next=await getJSON('/api/office'); sourceMode='local'; disconnected=false; }
      catch(error) {
        if(data && sourceMode==='local') { loseSignal(); return; }
        next=await getJSON('./snapshot.json'); sourceMode='snapshot'; disconnected=true;
      }
    } else {try{next=await getJSON('/api/office');sourceMode='remote';}catch(error){if(data&&sourceMode==='remote'){loseSignal();return;}next=await getJSON('./snapshot.json');sourceMode='snapshot';}}
    imported=false;acceptState(next,sourceMode);if(sourceMode==='local')connectEvents();
    if(manual) toast(['local','remote'].includes(sourceMode)?'Actividad real actualizada.':'Copia guardada recargada.');
  } catch(error) {if(data)loseSignal();else showNotice(error.message);if(!data&&$('#scene-loading'))$('#scene-loading').textContent='No pudimos leer los datos. Usá “Importar estado” para cargar una copia local.';}
  finally {refreshing=false; $('#refresh').disabled=false;}
}
function renderSource() {
  const live=['local','remote'].includes(sourceMode)&&!disconnected;
  $('#source-tag').textContent=disconnected?'Señal perdida':live?'En vivo':imported?'Copia importada':'Copia guardada';
  $('#source-tag').classList.toggle('live-connected',live);
  $('.mode-card strong').textContent=live?'Actividad real conectada':disconnected?'Esperando reconexión':'Una vista del proyecto';
  $('#source-detail').textContent=live?(sourceMode==='local'?'Eventos del proyecto y de Codex. Actualización automática en aproximadamente un segundo.':'Eventos enviados por tu PC al sitio privado. Actualización automática cada pocos segundos.'):'La conexión en vivo requiere el monitor del proyecto encendido. Las copias conservan su fecha.';
  $('#updated-at').textContent=`${live?'En vivo':disconnected?'Sin señal':'Copia'} · ${date(data.generated_at)}`;
  $('#data-footer').textContent=live?'Fuentes: CLI instrumentada + sesiones Codex del proyecto':`Última lectura · ${date(data.generated_at)}`;
  showNotice([disconnected?'El monitor del proyecto no está conectado. No se muestran puestos trabajando.':live?'':`Copia del ${date(data.generated_at)}. La actividad en vivo no está conectada.`,...(data.warnings||[])].filter(Boolean).join(' '));
}
function renderAll() {
  selected=data.agents.some(a=>a.id===selected)?selected:data.agents[0]?.id;
  const active=data.agents.filter(a=>a.live_status==='active'&&!disconnected).length;
  $('#summary').innerHTML=`<div><strong>${data.agents.length}</strong><span>agentes en el equipo</span></div><div><strong>${active}</strong><span>trabajando ahora</span></div><div><strong>${data.skills.filter(s=>s.available).length}</strong><span>skills disponibles</span></div><div class="telemetry-info"><span class="${!disconnected&&sourceMode!=='snapshot'?'live-dot':'hollow-dot'}"></span><span>${disconnected?'Señal perdida':sourceMode==='snapshot'?'Copia sin conexión':'Actividad real conectada'}</span></div>`;
  $('.nav-badge').textContent=data.agents.length;
  renderSource(); renderAreas(); renderDetail(); renderTeam(); renderSkills(); renderRecords();
  if(!office && !window.officeLoading) { window.officeLoading=true; import('./office-scene.js').then(({createOffice})=>{office=createOffice($('#office-scene'),data.agents,selectAgent);office.updateAgents(data.agents);office.select(selected);office.filter(activeArea);const toggle=$('#animation-toggle');toggle.setAttribute('aria-pressed',String(office.animationEnabled()));toggle.classList.toggle('active',office.animationEnabled());}).catch(error=>{console.error('No se pudo iniciar la vista 3D:',error);$('#scene-loading').innerHTML='<div class="scene-fallback">La vista 3D necesita WebGL habilitado.<br>Podés consultar todos los agentes y sus tareas en la vista Equipo.<button data-view="equipo">Ver equipo</button></div>';}); }
  if(office) {office.updateAgents(data.agents);office.select(selected);office.filter(activeArea);}
}
function renderAreas() {
  const areas=[...new Set(data.agents.map(a=>a.department))];
  $('#area-nav').innerHTML=areas.map(area=>`<button class="area-button ${area===activeArea?'active':''}" data-area="${esc(area)}" style="--area:${color(data.agents.find(a=>a.department===area).color)}"><span class="area-dot"></span>${esc(area)}<span class="area-count">${data.agents.filter(a=>a.department===area).length}</span></button>`).join('');
}
function selectAgent(id, navigate=false) { if(!data.agents.some(a=>a.id===id))return; selected=id; renderDetail(); office?.select(id); if(navigate) {showView('oficina');setTimeout(()=>$('#agent-detail').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'nearest'}),50);} }
function renderDetail() {
  const a=data.agents.find(a=>a.id===selected); if(!a)return;
  const el=$('#agent-detail'); el.style.setProperty('--agent-color',color(a.color));
  el.innerHTML=`<div class="detail-top"><span>FICHA DEL AGENTE</span><span class="detail-department">${esc(a.department)}</span></div>${avatar(a)}<h2>${esc(a.name)}</h2><p class="detail-role">${esc(a.role)}</p><span class="state-pill"><span class="hollow-dot"></span> ${esc(a.status_label)}</span><div class="detail-section"><h3>ÚLTIMA EVIDENCIA</h3><p>${esc(a.activity_summary)}</p>${a.last_record_at?`<p class="detail-footnote">Trabajo actualizado: ${esc(date(a.last_record_at))}</p>`:''}</div><div class="detail-section"><h3>QUÉ ENTREGA</h3><ul>${a.outputs.map(v=>`<li>${esc(v)}</li>`).join('')}</ul></div><div class="detail-section"><h3>SKILLS DISPONIBLES PARA ESTE ROL</h3><div class="skill-tags">${a.skills.length?a.skills.map(s=>`<button class="skill-tag" data-skill="${esc(s.id)}">✧ ${esc(s.name)}</button>`).join(''):'<span class="detail-footnote">Sin skill específica identificada.</span>'}</div>${a.skills.length?'<p class="detail-footnote">Afinidad con el rol; uso automático no configurado.</p>':''}</div><button class="contract-button" id="contract-toggle" aria-expanded="false">Ver entradas y contrato</button><div class="contract-panel hidden" id="contract-info">${esc(a.inputs.join(' · '))}\n\nFuente: ${esc(a.contract)}\n\nUn contrato define el rol. La actividad se acredita con registros del proyecto.</div>`;
  const pill=el.querySelector('.state-pill');pill.className=`state-pill status-${a.live_status||'idle'}`;pill.textContent=stateLabel(a);
  if(a.live_status){const run=a.last_run;const card=document.createElement('div');card.className=`live-work status-${a.live_status}`;card.innerHTML=`<h3>${a.live_status==='active'?'EN ESTE MOMENTO':a.live_status==='idle'?'DISPONIBLE':'ÚLTIMA EJECUCIÓN'}</h3><p class="current-task">${esc(a.current_task||(a.live_status==='idle'?'Sin ejecución observada. Listo para recibir trabajo.':'Sin tarea registrada.'))}</p><p class="current-skill">✧ ${esc(skillDescription(a))}</p>${run?`<p class="detail-footnote">${esc(run.source==='codex'?'Sesión Codex observada':run.source==='local_command'?'Proceso local instrumentado':run.source==='injected_client'?'Comprobación con cliente de prueba':'CLI de marketing')} · ${esc(date(run.started_at))}</p>`:''}${a.live_runs?.length>1?`<p class="detail-footnote">${a.live_runs.length} ejecuciones en paralelo en este rol.</p>`:''}`;pill.after(card);}
}
function renderTeam() {
  const q=($('#agent-search').value||'').toLocaleLowerCase('es');
  const agents=data.agents.filter(a=>(!activeArea||a.department===activeArea)&&`${a.name} ${a.role} ${a.skills.map(s=>s.name).join(' ')}`.toLocaleLowerCase('es').includes(q));
  $('#team-count').textContent=`${agents.length} de ${data.agents.length} agentes${activeArea?' · '+activeArea:''}`;
  $('#team-grid').innerHTML=agents.length?agents.map(a=>`<button class="team-card" data-agent="${esc(a.id)}" style="--agent-color:${color(a.color)}">${avatar(a)}<span class="eyebrow">${esc(a.department)}</span><h2>${esc(a.name)}</h2><p>${esc(a.live_status==='active'?a.current_task:a.role)}</p>${a.live_status==='active'?`<p class="current-skill">✧ ${esc(skillDescription(a))}</p>`:''}<span class="state-pill status-${esc(a.live_status||'idle')}">${esc(stateLabel(a))}</span></button>`).join(''):empty('No hay coincidencias','Probá otro nombre o quitá el filtro de área.');
}
function renderSkills() {
  $('#skills-grid').innerHTML=data.skills.map(s=>`<article class="skill-card" id="skill-${esc(s.id)}"><span class="skill-availability">${s.available?'Disponible en este equipo':'No encontrada localmente'}</span><h2>✧ ${esc(s.name)}</h2><p>${esc(s.description)}</p><span class="eyebrow">AFINIDAD CON ESTOS ROLES</span><div class="skill-agent-list">${(s.agent_ids||[]).map(id=>{const a=data.agents.find(a=>a.id===id);return a?`<button data-agent="${esc(id)}">${esc(a.short_name)}</button>`:'';}).join('')}</div><p class="detail-footnote">Uso a demanda. Sin asignación automática en la CLI.</p></article>`).join('')||empty('Sin skills detectadas','El equipo conserva sus contratos de trabajo.');
}
function jobCard(j) {
  const total=(j.completed_agents?.length||0)+(j.pending_agents?.length||0), done=j.completed_agents?.length||0;
  return `<article class="job-item"><span class="job-symbol">▤</span><div class="job-body"><h3>${esc(j.title)}</h3><span class="job-state">${esc(j.is_demo?'Demo histórica · no publicable':j.state_label||j.state)}</span><p>${esc(j.next_step)}</p>${total?`${j.is_demo?'':`<div class="job-meter" title="Etapas guardadas; no es un porcentaje de video terminado"><span style="width:${Math.min(100,done/total*100)}%"></span></div>`}<p>${j.is_demo?`${done} etapas de demostración`:`${done} de ${total} etapas guardadas`}${j.video_attached?' · Video adjunto':''}</p>`:''}<p class="detail-footnote">${esc(j.id)} · ${esc(date(j.updated_at||j.created_at))}</p></div></article>`;
}
function renderRecords() {
  $('#jobs-preview').innerHTML=data.jobs.length?data.jobs.slice(0,2).map(jobCard).join(''):empty('Aún no hay trabajos','Los próximos briefs aparecerán acá cuando se guarden.');
  $('#all-jobs').innerHTML=data.jobs.map(jobCard).join('')||empty('Aún no hay trabajos','No se encontraron registros en la base local.');
  $('#evidence-preview').innerHTML=data.evidence.slice(0,3).map(e=>`<article class="evidence-item"><span class="evidence-symbol">◇</span><div class="job-body"><h3>${esc(e.title)}</h3><p>${esc(e.detail)}</p><p class="detail-footnote">${esc(e.source)}</p></div></article>`).join('')||empty('Sin evidencias adicionales','Las entregas documentadas se muestran acá.');
  $('#activity-list').innerHTML=(data.activity.length?data.activity.map(e=>`<article class="activity-row"><h3>${esc(data.agents.find(a=>a.id===e.agent_id)?.short_name||e.agent_id)}</h3><p>${esc(e.title)}</p><time>Fecha del trabajo: ${esc(date(e.at))}</time></article>`).join(''):empty('Sin etapas guardadas','El historial aparecerá a medida que se registren entregas.'))+'<p class="activity-note">Las fechas corresponden a la actualización del trabajo. No prueban la hora exacta de ejecución de cada etapa ni actividad en curso.</p>';
  const live=(data.runs||[]).slice(0,15);
  if(live.length){const real=live.map(r=>`<article class="activity-row"><h3>${esc(data.agents.find(a=>a.id===r.agent_id)?.short_name||r.agent_id)} <span class="state-pill status-${esc(r.status)}">${esc(liveStateLabels[r.status]||r.status)}</span></h3><p>${esc(r.task)}</p><p>${esc(r.skill_id||'Contrato propio')} · ${esc(r.source)}</p><time>${esc(date(r.started_at))}${r.finished_at?' · Fin '+esc(date(r.finished_at)):''}</time></article>`).join('');$('#activity-list').innerHTML='<h3 class="live-section-title">Ejecuciones observadas</h3>'+real+'<h3 class="live-section-title">Etapas guardadas anteriormente</h3>'+$('#activity-list').innerHTML;}
}
function showView(view) {
  if(!viewTitles[view]) return; activeView=view;
  $$('.view').forEach(el=>el.classList.toggle('active',el.id===`view-${view}`));
  $$('.nav-item').forEach(el=>el.classList.toggle('active',el.dataset.view===view));
  const [title,subtitle,crumb]=viewTitles[view];$('#page-title').textContent=title;$('#page-subtitle').textContent=subtitle;$('#crumb').textContent=crumb;
  if(view==='oficina')office?.resize();
  history.replaceState(null,'',`#${view}`);
}
document.addEventListener('click',event=>{
  const viewButton=event.target.closest('[data-view]'); if(viewButton){showView(viewButton.dataset.view);return;}
  const agentButton=event.target.closest('[data-agent]'); if(agentButton){selectAgent(agentButton.dataset.agent,true);return;}
  const areaButton=event.target.closest('[data-area]'); if(areaButton){activeArea=activeArea===areaButton.dataset.area?'':areaButton.dataset.area;renderAreas();renderTeam();office?.filter(activeArea);if(activeView!=='equipo')showView('oficina');return;}
  const skillButton=event.target.closest('[data-skill]'); if(skillButton){showView('skills');document.getElementById(`skill-${skillButton.dataset.skill}`)?.scrollIntoView({block:'center'});return;}
  if(event.target.closest('#contract-toggle')){const expanded=$('#contract-toggle').getAttribute('aria-expanded')==='true';$('#contract-toggle').setAttribute('aria-expanded',String(!expanded));$('#contract-info').classList.toggle('hidden',expanded);}
});
$('#refresh').addEventListener('click',()=>refresh(true));
$('#agent-search').addEventListener('input',()=>data&&renderTeam());
$('#reset-camera').addEventListener('click',()=>office?.reset());
$('#animation-toggle').addEventListener('click',()=>{if(!office)return;const enabled=!office.animationEnabled();office.setAnimation(enabled);$('#animation-toggle').setAttribute('aria-pressed',String(enabled));$('#animation-toggle').classList.toggle('active',enabled);});
$('#zoom-in').addEventListener('click',()=>office?.zoom(1.18));
$('#zoom-out').addEventListener('click',()=>office?.zoom(1/1.18));
$('#labels-toggle').addEventListener('click',()=>{const b=$('#labels-toggle');const state=b.getAttribute('aria-pressed')!=='true';b.setAttribute('aria-pressed',String(state));b.classList.toggle('active',state);office?.labels(state);});
$('#import-button').addEventListener('click',()=>$('#snapshot-file').click());
$('#snapshot-file').addEventListener('change',async event=>{const file=event.target.files[0];if(!file)return;try{if(file.size>5_000_000)throw new Error('El estado debe pesar menos de 5 MB.');const next=checkSnapshot(JSON.parse(await file.text()));if(data&&next.agents.map(a=>a.id).sort().join()!==data.agents.map(a=>a.id).sort().join())throw new Error('Esta copia pertenece a otro equipo. Importá un estado de este proyecto.');eventStream?.close();eventStream=null;data=next;for(const a of data.agents){if(a.live_status==='active'){a.live_status='stale';a.live_status_label='Copia sin señal en vivo';}a.live_runs=[];}if(data.summary)data.summary.active_verified=0;sourceMode='snapshot';imported=true;disconnected=false;renderedSignature='';renderAll();toast('Estado importado en esta pestaña.');}catch(error){toast(error.message||'No pudimos abrir ese archivo.');}event.target.value='';});
setInterval(()=>{if(document.hidden||imported)return;if(!isLocal)refresh();else if(lastSignalAt&&Date.now()-lastSignalAt>6500){loseSignal();refresh();}},2000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&!imported)refresh();});
showView(location.hash.slice(1)||'oficina');
refresh();
