import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';

export function createOffice(container,agents,onSelect) {
  const scene=new THREE.Scene();
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'low-power'});
  renderer.setPixelRatio(Math.min(devicePixelRatio,1.7));
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.28;
  container.prepend(renderer.domElement);renderer.domElement.setAttribute('aria-label','Oficina tridimensional con 14 puestos. También podés seleccionar los agentes desde la vista Equipo.');
  const camera=new THREE.OrthographicCamera(-14,14,11,-11,.1,100);
  const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=false;controls.enablePan=false;controls.minPolarAngle=.3;controls.maxPolarAngle=1.28;controls.minZoom=.65;controls.maxZoom=2.6;controls.rotateSpeed=.6;
  const hemi=new THREE.HemisphereLight('#ecedff','#353246',2.5);scene.add(hemi);
  const key=new THREE.DirectionalLight('#ffe5d0',4);key.position.set(-5,18,8);key.castShadow=true;key.shadow.mapSize.set(2048,2048);Object.assign(key.shadow.camera,{left:-16,right:16,top:16,bottom:-16,near:1,far:50});key.shadow.bias=-.001;key.shadow.normalBias=.04;scene.add(key);
  const fill=new THREE.DirectionalLight('#b9adff',2);fill.position.set(9,8,-9);scene.add(fill);
  const materials=new Map();
  function mat(c,rough=.65,metal=.05){const id=[c,rough,metal].join();if(!materials.has(id))materials.set(id,new THREE.MeshStandardMaterial({color:c,roughness:rough,metalness:metal}));return materials.get(id);}
  function box(w,h,d,c,x,y,z,parent=scene){const mesh=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),mat(c));mesh.position.set(x,y,z);mesh.castShadow=true;mesh.receiveShadow=true;parent.add(mesh);return mesh;}
  function cylinder(rt,rb,h,c,x,y,z,parent=scene,n=24){const m=new THREE.Mesh(new THREE.CylinderGeometry(rt,rb,h,n),mat(c));m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m;}
  function sphere(r,c,x,y,z,parent=scene,sx=1,sy=1,sz=1){const m=new THREE.Mesh(new THREE.SphereGeometry(r,20,14),mat(c));m.position.set(x,y,z);m.scale.set(sx,sy,sz);m.castShadow=true;parent.add(m);return m;}
  function textTexture(text,fg='#e8e4f5',bg=null,w=1024,h=192){const cv=document.createElement('canvas');cv.width=w;cv.height=h;const ctx=cv.getContext('2d');if(bg){ctx.fillStyle=bg;ctx.fillRect(0,0,w,h);}ctx.fillStyle=fg;ctx.font='600 76px Segoe UI, Arial';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(text,w/2,h/2,w-50);const t=new THREE.CanvasTexture(cv);t.colorSpace=THREE.SRGBColorSpace;return t;}
  function floorText(text,x,z,w,color){const m=new THREE.Mesh(new THREE.PlaneGeometry(w,w*.1875),new THREE.MeshBasicMaterial({map:textTexture(text,color),transparent:true,depthWrite:false}));m.rotation.x=-Math.PI/2;m.position.set(x,.195,z);scene.add(m);return m;}
  function panelText(text,x,y,z,w,color){const mesh=new THREE.Mesh(new THREE.PlaneGeometry(w,w*.1875),new THREE.MeshBasicMaterial({map:textTexture(text,color),transparent:true}));mesh.position.set(x,y,z);scene.add(mesh);return mesh;}
  // A single dollhouse floor: four color-coded work areas and a central meeting point.
  box(21,.45,14,'#4b4e61',0,-.2,0);
  box(21.13,.12,14.13,'#747186',0,-.4,0);
  box(20.7,.1,13.7,'#777985',0,.08,0);
  const rooms=[{x:-5.7,z:-3.4,w:8.8,d:5.7,c:'#7e719b',label:'ESTRATEGIA',tc:'#ebe3fc'},{x:5.3,z:-3.4,w:9.4,d:5.7,c:'#658c83',label:'ESTUDIO VISUAL',tc:'#d5fff0'},{x:-5.7,z:3.6,w:8.8,d:5.5,c:'#9c8270',label:'PRODUCCIÓN',tc:'#ffedcf'},{x:5.3,z:3.6,w:9.4,d:5.5,c:'#98788a',label:'ENTREGA',tc:'#ffe2eb'}];
  for(const r of rooms){box(r.w,.045,r.d,r.c,r.x,.15,r.z);floorText(r.label,r.x,r.z+r.d/2-.53,Math.min(5.7,r.w-.4),r.tc);}
  // Back and side architectural walls, with glazing and slim metal mullions.
  box(21,.95,.18,'#66637b',0,.5,-6.93);box(.18,.9,14,'#69687b',-10.43,.5,0);
  box(21,.1,.25,'#c7c5d5',0,1.03,-6.93);box(.25,.1,14,'#c7c5d5',-10.43,.98,0);
  const glass=new THREE.MeshPhysicalMaterial({color:'#a9c7dc',transparent:true,opacity:.15,roughness:.22,metalness:.08,side:THREE.DoubleSide,depthWrite:false});
  for(let i=0;i<7;i++){const pane=new THREE.Mesh(new THREE.BoxGeometry(2.88,1.5,.055),glass);pane.position.set(-8.95+i*3,1.8,-6.94);scene.add(pane);box(.045,1.6,.08,'#a8a4b9',-10.43+i*3,1.8,-6.91);}
  box(21,.06,.1,'#b6b1c5',0,2.6,-6.91);
  box(.13,1.1,4.5,'#77798a',-.75,.6,-4.55);box(.2,.08,4.5,'#cdc9d5',-.75,1.18,-4.55);
  box(5.9,.65,.1,'#858092',-7.35,.4,.05);box(6.2,.65,.1,'#858092',6.97,.4,.05);
  for(const x of [-9.7,-.8,9.6]){box(.17,2.8,.17,'#a6a1b7',x,1.4,-6.5);}
  // Recessed entrance strips and a quiet lounge in the middle of the plan.
  box(.08,.02,11.4,'#bfb1dd',-.15,.2,0);box(.08,.02,11.4,'#bfb1dd',.15,.2,0);
  box(3.8,.035,2.5,'#525763',.1,.18,.2);
  cylinder(.85,.85,.12,'#c4b0a0',.1,.88,.2);cylinder(.18,.3,.68,'#3f4351',.1,.5,.2);
  for(const [x,z] of [[-1.35,.2],[1.55,.2],[.1,-1],[.1,1.4]]){cylinder(.32,.32,.16,'#6e837a',x,.56,z);cylinder(.06,.18,.35,'#393e4a',x,.3,z);}
  cylinder(.12,.1,.16,'#e4d2be',-.2,1.02,.2);sphere(.19,'#759d7d',-.2,1.24,.2,scene,1,1.2,1);
  function plant(x,z,size=1){cylinder(.28*size,.2*size,.52*size,'#dad2c6',x,.35*size,z);for(let i=0;i<6;i++){const a=i*2.4;sphere(.3*size,i%2?'#547f69':'#75947c',x+Math.cos(a)*.18*size,.86*size+i*.07*size,z+Math.sin(a)*.18*size,scene,.8,1.6,.65);}}
  plant(-9.5,-6,1.2);plant(9.5,-5.9,1.2);plant(-9.6,6.1,1.1);plant(9.5,6.1,1.2);plant(-.8,6.1,.8);
  // Back wall display and a small material shelf.
  box(4.1,1.55,.12,'#2e303e',-5.1,1.7,-6.72);panelText('INFINITE PROCESS',-5.1,1.75,-6.64,3.7,'#d2c1f4');panelText('MARKETING STUDIO',-5.1,1.32,-6.63,2.9,'#a8a5ba');
  box(2.1,.1,.52,'#454957',7.8,.9,-6.45);box(2.1,.1,.52,'#454957',7.8,1.55,-6.45);
  for(let i=0;i<8;i++)box(.16,.4,.29,['#bca3dc','#e0b290','#8cae9e'][i%3],6.95+i*.2,1.15,-6.4);
  const positions={
    '00-orquestador':[-7.5,-4.2], '01-trend-hunter':[-3.9,-4.2], '02-guionista':[-7.5,-1.9], '07-analista':[-3.9,-1.9],
    '12-referencias':[2.4,-4.1], '04-director-visual':[6.8,-4.1], '13-motion':[4.7,-1.8],
    '05-voz':[-7.5,2.3], '09-montaje':[-3.9,2.3], '10-musica':[-5.7,4.7],
    '06-thumbnail-copy':[2.6,2.3], '11-control-calidad':[6.8,2.3], '08-publicador':[2.6,4.7], '03-roulette-master':[6.8,4.7]
  };
  const interactables=[],stations=new Map(),labelsRoot=container.querySelector('#agent-labels');let selectedId,labelsVisible=true,area='';
  const stateColors={active:'#94efc7',idle:'#989eb1',completed:'#b9d8c7',error:'#ff9e96',stale:'#efc17b'};
  const stateNames={active:'Trabajando',idle:'Sin ejecución activa',completed:'Finalizado',error:'Error',stale:'Señal interrumpida'};
  for(const agent of agents){
    const [x,z]=positions[agent.id]||[0,0], accent=agent.color;
    const group=new THREE.Group();group.position.set(x,0,z);group.userData.agent=agent.id;scene.add(group);
    // Desk, tactile accessories, monitor and task-specific visual on its screen.
    box(2.5,.13,1.05,'#d4c7bb',0,1.04,0,group);
    for(const lx of [-1.05,1.05])for(const lz of [-.37,.37])box(.08,.9,.08,'#4a4d5a',lx,.55,lz,group);
    box(.5,.05,.3,'#626475',0,1.14,-.15,group);box(.07,.25,.08,'#626475',0,1.26,-.27,group);
    box(1.1,.68,.08,'#343645',0,1.6,-.28,group);
    const monitor=box(.99,.55,.015,'#202735',0,1.6,-.23,group);
    monitor.material=mat('#202735').clone();
    const screenLines=[];
    for(let i=0;i<3;i++)screenLines.push(box(.22+i*.1,.035,.018,i===0?accent:'#83909b',-.22+i*.08,1.74-i*.12,-.217,group));
    box(.72,.025,.25,'#888592',0,1.135,.21,group);box(.12,.035,.18,'#696675',.58,1.15,.22,group);
    cylinder(.095,.08,.16,accent,-.91,1.18,.12,group);box(.25,.02,.33,accent,.96,1.13,-.12,group);
    // Idle motion is ambience. Typing, lit monitors and task badges require live activity.
    cylinder(.36,.36,.12,'#3c4352',0,.57,1,group);
    box(.72,.65,.16,accent,0,.84,1.24,group);
    cylinder(.05,.2,.35,'#353b48',0,.32,1,group);
    for(const sign of [-1,1]){box(.16,.4,.17,'#424754',sign*.19,.51,.76,group);box(.18,.12,.32,'#363b47',sign*.19,.3,.65,group);}
    const torso=sphere(.31,accent,0,.94,.9,group,1,1.24,.8);
    const head=new THREE.Group();head.position.set(0,1.45,.87);group.add(head);
    box(.53,.45,.43,'#e2dcd5',0,0,0,head);
    box(.43,.22,.018,'#353b4c',0,.03,.225,head);
    const eyes=[];
    for(const sign of [-1,1])eyes.push(sphere(.035,accent,sign*.105,.04,.243,head,1,1.2,.4));
    cylinder(.022,.022,.1,'#777789',0,.27,0,head,10);
    const antenna=sphere(.045,accent,0,.34,0,head);antenna.material=mat(accent).clone();
    const arms=[];
    for(const sign of [-1,1]){const arm=new THREE.Group();arm.position.set(sign*.36,1.05,.83);arm.rotation.y=sign*.2;group.add(arm);box(.12,.14,.45,accent,0,0,-.15,arm);sphere(.075,'#e2dcd5',0,0,-.39,arm,1,.75,1);arms.push(arm);}
    const hit=box(2.65,2.3,2.1,accent,0,1.15,.45,group);hit.material=new THREE.MeshBasicMaterial({visible:false});hit.userData.agent=agent.id;interactables.push(hit);
    const ring=new THREE.Mesh(new THREE.RingGeometry(.55,.62,48),new THREE.MeshBasicMaterial({color:accent,transparent:true,opacity:.95,side:THREE.DoubleSide}));ring.rotation.x=-Math.PI/2;ring.position.set(0,.23,.95);ring.visible=false;group.add(ring);
    const beacon=sphere(.09,stateColors.idle,.89,1.42,-.24,group);beacon.material=mat(stateColors.idle).clone();
    const activityRing=new THREE.Mesh(new THREE.RingGeometry(.67,.71,48),new THREE.MeshBasicMaterial({color:stateColors.active,transparent:true,opacity:.7,side:THREE.DoubleSide}));activityRing.rotation.x=-Math.PI/2;activityRing.position.set(0,.24,.95);activityRing.visible=false;group.add(activityRing);
    const label=document.createElement('button');label.className='agent-label';label.style.maxWidth='190px';label.style.textAlign='left';label.setAttribute('aria-label',`Ver ficha: ${agent.name}`);label.addEventListener('click',()=>onSelect(agent.id));
    const nameLabel=document.createElement('span');nameLabel.textContent=agent.short_name;label.append(nameLabel);
    const taskBadge=document.createElement('span');Object.assign(taskBadge.style,{display:'none',maxWidth:'175px',overflow:'hidden',textOverflow:'ellipsis',fontSize:'11px',lineHeight:'1.45',paddingTop:'3px',whiteSpace:'nowrap'});label.append(taskBadge);labelsRoot.append(label);
    stations.set(agent.id,{group,ring,label,nameLabel,taskBadge,agent,anchor:new THREE.Vector3(x,2.6,z+.3),head,torso,eyes,arms,antenna,monitor,screenLines,beacon,activityRing,liveStatus:'idle',phase:stations.size*.77});
  }
  const raycaster=new THREE.Raycaster(),pointer=new THREE.Vector2();let pointerStart;
  renderer.domElement.addEventListener('pointerdown',e=>pointerStart={x:e.clientX,y:e.clientY});
  renderer.domElement.addEventListener('pointerup',e=>{if(!pointerStart||Math.hypot(e.clientX-pointerStart.x,e.clientY-pointerStart.y)>5)return;const rect=renderer.domElement.getBoundingClientRect();pointer.set((e.clientX-rect.left)/rect.width*2-1,-(e.clientY-rect.top)/rect.height*2+1);raycaster.setFromCamera(pointer,camera);const hit=raycaster.intersectObjects(interactables,false)[0];if(hit)onSelect(hit.object.userData.agent);});
  let frameId=null,lastFrame=0,dirty=true,compactLabels,animationOn=true,sceneVisible=true,disposed=false;
  const reducedMotion=matchMedia('(prefers-reduced-motion: reduce)');
  function motionAllowed(){return animationOn&&!reducedMotion.matches&&!document.hidden&&sceneVisible&&container.clientWidth>0&&container.clientHeight>0;}
  function draw(){if(!container.clientWidth||!container.clientHeight)return;renderer.render(scene,camera);const w=container.clientWidth,h=container.clientHeight;for(const s of stations.values()){const p=s.anchor.clone().project(camera);s.label.style.left=`${(p.x*.5+.5)*w}px`;s.label.style.top=`${(-p.y*.5+.5)*h}px`;const show=labelsVisible||s.liveStatus==='active'||s.liveStatus==='error'||s.liveStatus==='stale';s.label.style.display=show&&p.z<1&&Math.abs(p.x)<.95&&Math.abs(p.y)<.95?'block':'none';}}
  function pose(time,animate){
    for(const s of stations.values()){
      const t=time+s.phase,active=s.liveStatus==='active',quiet=s.liveStatus==='error'||s.liveStatus==='stale';
      const moving=animate&&!quiet;
      const breath=moving?Math.sin(t*1.65)*.05:0;
      s.torso.scale.y=1.24+(moving?Math.sin(t*1.65)*.035:0);
      s.torso.rotation.x=active?.12:0;
      s.head.position.y=1.45+breath;
      const targetYaw=active?Math.PI+(moving?Math.sin(t*2)*.055:0):(moving?Math.sin(t*.55)*.4:0);
      s.head.rotation.y=animate?THREE.MathUtils.lerp(s.head.rotation.y,targetYaw,.18):targetYaw;
      s.head.rotation.z=moving?(active?Math.sin(t*3)*.025:Math.sin(t*.8)*.045):0;
      s.head.rotation.x=active?.12:(moving?Math.sin(t*.85)*.035:0);
      const blink=moving&&(t%5.7<.12||t%5.7>5.45&&t%5.7<5.54);
      for(const eye of s.eyes)eye.scale.y=blink?.16:1.2;
      s.arms.forEach((arm,index)=>{const sign=index?1:-1;arm.position.y=1.05+(active&&moving?Math.sin(t*12+index*Math.PI)*.055:breath*.45);arm.rotation.x=active&&moving?Math.sin(t*12+index*Math.PI)*.13:(quiet?.22:.08);arm.rotation.z=active?sign*.08:sign*.06;});
      s.screenLines.forEach((line,index)=>{line.scale.x=active&&moving?.62+.36*(1+Math.sin(t*3.2+index)):1;});
      const pulse=active&&moving?.5+.5*Math.sin(t*4):0;
      s.monitor.material.emissiveIntensity=active?.18+pulse*.12:0;
      s.beacon.material.emissiveIntensity=active?.55+pulse*.7:0;
      s.antenna.material.emissiveIntensity=active?.35+pulse*.35:0;
      s.activityRing.scale.setScalar(1+(active&&moving?((t*.7)%1)*.3:0));
      s.activityRing.material.opacity=active?.8-(active&&moving?((t*.7)%1)*.55:0):0;
    }
  }
  function frame(now){
    frameId=null;if(disposed||document.hidden)return;
    const animate=motionAllowed();
    if(dirty||(animate&&now-lastFrame>=1000/30)){pose(now/1000,animate);draw();dirty=false;lastFrame=now;}
    if(animate)frameId=requestAnimationFrame(frame);
  }
  function requestRender(){dirty=true;if(!disposed&&!document.hidden&&frameId===null)frameId=requestAnimationFrame(frame);}
  function updateAgents(nextAgents){
    for(const agent of nextAgents){const s=stations.get(agent.id);if(!s)continue;s.agent=agent;s.liveStatus=Object.hasOwn(stateColors,agent.live_status)?agent.live_status:'idle';
      const active=s.liveStatus==='active',statusColor=stateColors[s.liveStatus];
      const currentSkill=typeof agent.current_skill==='string'?agent.current_skill:agent.current_skill?.name||agent.current_skill?.id||'';
      const currentTask=typeof agent.current_task==='string'?agent.current_task:agent.current_task?.title||'';
      const runs=Array.isArray(agent.live_runs)?agent.live_runs.filter(run=>run.status==='active'||run.live_status==='active'):[];
      s.nameLabel.textContent=(active?'● ':s.liveStatus==='error'?'! ':s.liveStatus==='stale'?'◌ ':'')+agent.short_name;
      s.taskBadge.textContent=active?`${currentSkill?(agent.skill_evidence==='instructions_read_in_turn'?'Consulta: ':'Skill: ')+currentSkill:'Contrato propio'}${runs.length>1?` · ${runs.length} tareas`:''}`:s.liveStatus==='error'?'Error registrado':s.liveStatus==='stale'?'Sin señal reciente':'';
      s.taskBadge.style.display=s.taskBadge.textContent?'block':'none';s.taskBadge.style.color=agent.id===selectedId?'#30233f':statusColor;
      s.label.dataset.liveStatus=s.liveStatus;s.label.title=`${agent.name} · ${stateNames[s.liveStatus]}${currentTask?' · '+currentTask:''}${currentSkill?' · Skill: '+currentSkill:''}`;
      s.label.style.borderColor=active||s.liveStatus==='error'||s.liveStatus==='stale'?statusColor:'';
      s.label.style.boxShadow=active?'0 0 0 1px #8ce4bd30, 0 4px 12px #0005':'';
      s.beacon.material.color.set(statusColor);s.beacon.material.emissive.set(statusColor);s.monitor.material.emissive.set(stateColors.active);s.antenna.material.emissive.set(stateColors.active);s.activityRing.visible=active;
    }
    requestRender();
  }
  function resize(){const w=container.clientWidth,h=container.clientHeight;if(!w||!h)return;const compact=w<430;if(compact!==compactLabels){compactLabels=compact;labelsVisible=!compact;const toggle=document.getElementById('labels-toggle');toggle.setAttribute('aria-pressed',String(labelsVisible));toggle.classList.toggle('active',labelsVisible);container.querySelector('.scene-help').textContent=compact?'Tocá un puesto · Pellizcá para acercarte':'Arrastrá para girar · Scroll para acercarte';}renderer.setSize(w,h);const aspect=w/h,frustum=aspect<1.2?29/aspect:24;camera.left=-frustum*aspect/2;camera.right=frustum*aspect/2;camera.top=frustum/2;camera.bottom=-frustum/2;camera.updateProjectionMatrix();requestRender();}
  function reset(){camera.position.set(20,23,28);camera.zoom=1;controls.target.set(0,.35,0);camera.updateProjectionMatrix();controls.update();resize();}
  controls.addEventListener('change',requestRender);
  const observer=new ResizeObserver(resize);observer.observe(container);
  const visibilityObserver=new IntersectionObserver(entries=>{sceneVisible=entries[0]?.isIntersecting??true;if(sceneVisible)requestRender();},{threshold:0});visibilityObserver.observe(container);
  const onVisibility=()=>{if(document.hidden&&frameId!==null){cancelAnimationFrame(frameId);frameId=null;}else requestRender();};
  document.addEventListener('visibilitychange',onVisibility);reducedMotion.addEventListener('change',requestRender);
  container.querySelector('#scene-loading')?.remove();updateAgents(agents);reset();
  return {resize,reset,updateAgents,setAnimation(enabled){animationOn=Boolean(enabled);requestRender();},animationEnabled(){return animationOn&&!reducedMotion.matches;},select(id){selectedId=id;for(const [key,s]of stations){s.ring.visible=key===id;s.label.classList.toggle('selected',key===id);s.label.setAttribute('aria-pressed',String(key===id));s.taskBadge.style.color=key===id?'#30233f':stateColors[s.liveStatus];}requestRender();},filter(value){area=value;for(const s of stations.values())s.label.classList.toggle('dimmed',!!area&&s.agent.department!==area);requestRender();},zoom(multiplier){camera.zoom=Math.min(2.6,Math.max(.65,camera.zoom*multiplier));camera.updateProjectionMatrix();controls.update();requestRender();},labels(visible){labelsVisible=visible;requestRender();},dispose(){disposed=true;if(frameId!==null)cancelAnimationFrame(frameId);observer.disconnect();visibilityObserver.disconnect();document.removeEventListener('visibilitychange',onVisibility);reducedMotion.removeEventListener('change',requestRender);controls.dispose();scene.traverse(object=>{object.geometry?.dispose();if(object.material){for(const material of Array.isArray(object.material)?object.material:[object.material]){material.map?.dispose();material.dispose();}}});renderer.dispose();renderer.domElement.remove();for(const s of stations.values())s.label.remove();}};
}
