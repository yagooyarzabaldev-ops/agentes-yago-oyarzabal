"""V10: unique visual scenes, timed monochrome asides and an arranged house score."""
from pathlib import Path
import hashlib,json,shutil,statistics
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'runtime/construccion-v10';E=ROOT/'entregas/construccion-v10'
D.mkdir(parents=True,exist_ok=True);E.mkdir(parents=True,exist_ok=True)
P=json.loads((ROOT/'runtime/construccion-v9/params.json').read_text(encoding='utf-8'))
new=['silos','architecture','community','learning','foundation','idea','fit','bottleneck','production','review','automation','time']
P['assets']={k:f'assets-v10/{k}.png' for k in new}
P['assets'].update(neural='assets-v7/neural.png',infraestructura='assets-v8/infraestructura.png')
edits=[(0,'toggle'),(1.5,'silos'),(3,'rewire'),(4.5,'architecture'),(6,'neural'),
 (7.333333333,'community'),(9.5,'stream'),(11.5,'learning'),(13.2,'mesh'),(15.5,'exchange'),
 (17.1,'identity'),(18.5,'aside_know'),(21.2,'experiments'),(23.5,'foundation'),(25.5,'stack'),
 (27.5,'infraestructura'),(29.4,'idea'),(31.5,'blueprint'),(33.5,'fit'),(35.5,'adapt'),
 (37.5,'aside_fit'),(40,'bottleneck'),(42,'fastlane'),(44,'production'),(46,'review'),
 (47.8,'aside_ideal'),(49,'automation'),(51,'orchestration'),(53,'routing'),(55,'loop'),
 (57,'result'),(59.5,'time'),(61.5,'benefits'),(63.5,'humanclose'),(65.3,'outro')]
P['camera_ranges']=[[0,4.5],[7.333333333,13.2],[17.1,23.5],[29.4,33.5],[37.5,42],[47.8,49],[59.5,65.3]]
P['bw_ranges']=[[18.5,21.2],[37.5,39.733333333],[47.8,48.733333333]]
for field in ['camera_ranges','bw_ranges']:P[field]=[[round(a*30)/30,round(b*30)/30] for a,b in P[field]]
P['camera_visible_seconds']=sum(b-a for a,b in P['camera_ranges'])
P['bw_seconds']=sum(b-a for a,b in P['bw_ranges'])
palette=['#ffb35e','#d8ec85','#c99bff','#91e2c0','#ff937e']
titles={
 'toggle':['CAMBIAR','UN BOTÓN.'],'silos':['TODO','SEPARADO.'],'rewire':['CONECTAR','EL SISTEMA.'],
 'architecture':['REDISEÑAR','CÓMO FUNCIONA.'],'neural':['IA CON','CONTEXTO.'],
 'community':['COMPARTIR','EXPERIENCIA.'],'stream':['LO QUE APRENDO,','LO COMPARTO.'],'learning':['IA EN','LA PRÁCTICA.'],
 'mesh':['PERSONAS.','CONOCIMIENTO.'],'exchange':['APRENDER','ENTRE TODOS.'],'identity':['VOLVER','A APRENDER.'],
 'aside_know':['CREER QUE','YA SABÉS…'],'experiments':['PROBAR.','REVISAR. AJUSTAR.'],
 'foundation':['BASES','SÓLIDAS.'],'stack':['DATOS.','HERRAMIENTAS.'], 'infraestructura':['LA BASE','DEL SISTEMA.'],
 'idea':['LA IDEA','LLEGA RÁPIDO.'],'blueprint':['IMPLEMENTAR','ES OTRO PASO.'],'fit':['ADAPTARLO','A TU NEGOCIO.'],
 'adapt':['CADA NEGOCIO,','SU ESTRUCTURA.'],'aside_fit':['NO TODO','ENCAJA IGUAL.'],
 'bottleneck':['ENCONTRAR','EL BLOQUEO.'],'fastlane':['EMPEZAR','CON ALGO ÚTIL.'],
 'production':['DE LA IDEA','AL VIDEO.'],'review':['PROBAR','EL RESULTADO.'],'aside_ideal':['ESO SERÍA','LO IDEAL.'],
 'automation':['CONECTAR','LAS TAREAS.'],'orchestration':['PERSONA','+ AGENTE.'],'routing':['MENOS PASOS','MANUALES.'],
 'loop':['REVISAR','Y MEJORAR.'],'result':['RESOLVER','UN PROBLEMA.'],'time':['RECUPERAR','TIEMPO.'],
 'benefits':['MENOS FRICCIÓN.','MÁS FOCO.'],'humanclose':['CAMBIAR CÓMO','TRABAJAMOS.'],'outro':['CAMBIAR CÓMO','TRABAJAMOS.']}
shots=[]
for i,(a,view) in enumerate(edits):
 a=round(a*30)/30;b=round((edits[i+1][0] if i+1<len(edits) else P['duration'])*30)/30
 shots.append(dict(start=a,end=b,view=view,kind='image' if view in P['assets'] else view,index=i,title=titles[view],accent='#e7e7e7' if view.startswith('aside') else palette[i%5],motion=['push','truck','orbit','pull','lift'][i%5],direction=(-1)**i,variant=0))
P['shots']=shots;P['visual_chapters']=shots;P['bpm']=120
modes=['cut','portal','fold','match','particles','slit','trace']
P['transitions']=[dict(at=s['start'],index=i,duration=0 if s['view'].startswith('aside') or s['view'] in ['experiments','bottleneck','automation'] else [.0,.33,.37,.30,.4,.3,.37][(i-1)%7],mode='cut' if s['view'].startswith('aside') else modes[(i-1)%7],direction=s['direction']) for i,s in enumerate(shots) if i]
P['music_sections']=[dict(start=a,end=b,kind='aside') for a,b in P['bw_ranges']]
P['major_accents']=[4.5,7.333333333,13.2,17.1,21.2,23.5,29.4,33.5,40,44,49,59.5,65.3]
(D/'params.json').write_text(json.dumps(P,ensure_ascii=False,indent=2),encoding='utf-8')
for name in ['camara.mp4','voz.wav','subs.srt','transcripcion-editada.txt','revision-cortes.json','revision-voz-identica.json','revision-sincronizacion.json']:
 shutil.copyfile(ROOT/'runtime/construccion-v9'/name,D/name)
report={'duration':P['duration'],'camera_seconds':P['camera_visible_seconds'],'camera_percent':100*P['camera_visible_seconds']/P['duration'],'bw_ranges':P['bw_ranges'],'bw_seconds':P['bw_seconds'],'new_images':len(new),'reused_images':2,'unique_image_scenes':len(P['assets']),'animated_scenes':len(shots)-len(P['assets']),'total_scenes':len(shots),'duplicate_views':len(shots)-len(set(s['view'] for s in shots)),'mean_narration_shot_seconds':statistics.mean(s['end']-s['start'] for s in shots[:-1]),'transition_modes':modes,'bpm':120,'voice_sha256':hashlib.sha256((D/'voz.wav').read_bytes()).hexdigest()}
(D/'direccion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report))
