"""Split-screen revision: original camera on top, technical imagery below."""
from pathlib import Path
import json, shutil, hashlib
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'runtime/construccion-v8';E=ROOT/'entregas/construccion-v8'
D.mkdir(parents=True,exist_ok=True);E.mkdir(parents=True,exist_ok=True)
P=json.loads((ROOT/'runtime/construccion-v7/params.json').read_text(encoding='utf-8'))
scenes=[
 (0,4.5,'desarrollo','CAMBIAR','BOTONES.','#ffb65f','image'),
 (4.5,7.3333333333,'neural','REDISEÑAR','EL SISTEMA.','#ffbc70','image'),
 (7.3333333333,13.2,'studio_ref','IA EN LA','PRÁCTICA.','#a3ecc3','image'),
 (13.2,17.1,'network','COMPARTIR','EXPERIENCIA.','#df9cf6','network'),
 (17.1,23.5333333333,'learn','PROBAR. REVISAR.','APRENDER.','#ffac66','learn'),
 (23.5333333333,29.4,'chip_ref','LA BASE','DEL SISTEMA.','#ffbc70','image'),
 (29.4,32.3333333333,'brief','UNA IDEA.','EL PRIMER PASO.','#dba1f1','brief'),
 (32.3333333333,35.9333333333,'infraestructura','HACERLO','FUNCIONAR.','#a3ecc3','image'),
 (35.9333333333,40,'hub_ref','ADAPTARLO','A TU NEGOCIO.','#e6a7f5','image'),
 (40,44.8666666667,'launch','EMPEZAR','Y AJUSTAR.','#ffac66','launch'),
 (44.8666666667,48.8,'produccion','DEL GUION','AL VIDEO.','#e6a7f5','image'),
 (48.8,56.5333333333,'flow_ref','PERSONA + AGENTE.','UN MISMO FLUJO.','#dcf18b','image'),
 (56.5333333333,59.6,'workflow','MEJORAR','EL PROCESO.','#a3ecc3','workflow'),
 (59.6,65.3,'tiempo','RECUPERAR','TIEMPO.','#ffbd7a','image'),
 (65.3,67.1,'outro','CAMBIAR CÓMO','TRABAJAMOS.','#ffbc70','outro'),
]
P['shots']=[dict(start=a,end=b,view=k,title=[t1,t2],accent=color,kind=kind,index=i) for i,(a,b,k,t1,t2,color,kind) in enumerate(scenes)]
P['transitions']=[dict(at=s['start'],index=i,duration=.3,mode=['push','iris','diagonal'][i%3]) for i,s in enumerate(P['shots']) if i and s['view']!='outro']
P['assets']={k:f'assets-v8/{k}.png' for k in ['desarrollo','infraestructura','produccion']}
P['assets'].update({k:f'assets-v7/{k}.png' for k in ['neural','chip_ref','studio_ref','hub_ref','flow_ref']})
P['assets']['tiempo']='assets-v5/tiempo.png'
P['bpm']=120;P['split_y']=960
(D/'params.json').write_text(json.dumps(P,ensure_ascii=False,indent=2),encoding='utf-8')
for f in ['subs.srt','transcripcion-editada.txt','revision-cortes.json']:
 shutil.copyfile(ROOT/'runtime/construccion-v7'/f,D/f)
shutil.copyfile(ROOT/'runtime/construccion-v3/voz.wav',D/'voz.wav')
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'ok':h(D/'voz.wav')==h(ROOT/'runtime/construccion-v3/voz.wav'),'source':'runtime/construccion-v3/voz.wav','sha256':h(D/'voz.wav'),'speech_speed':1,'narration_retimed':False,'camera_offset_seconds':2.3429,'music_changed':True}
(D/'revision-voz-identica.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
inventory={'duration':P['duration'],'layout':'camera upper 1080x960; visuals lower 1080x960; full bleed','image_count':len(P['assets']),'image_files':P['assets'],'bottom_scenes':len(scenes),'transitions':len(P['transitions']),'paper_cards':False,'white_camera_frame':False,'bpm':120}
(D/'revision-variedad.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(inventory,ensure_ascii=False))
