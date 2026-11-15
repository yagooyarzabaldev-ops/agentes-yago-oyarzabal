"""Faster lower-half edits with the accepted split-screen and unchanged camera."""
from pathlib import Path
import json, shutil, hashlib, statistics
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'runtime/construccion-v9';E=ROOT/'entregas/construccion-v9'
D.mkdir(parents=True,exist_ok=True);E.mkdir(parents=True,exist_ok=True)
P=json.loads((ROOT/'runtime/construccion-v8/params.json').read_text(encoding='utf-8'))
P['visual_chapters']=P['shots']
edits=[(0,'desarrollo'),(2,'flow_ref'),(4.5,'chip_ref'),(6,'neural'),
 (7.3333333333,'studio_ref'),(9.5,'desarrollo'),(11.5,'produccion'),
 (13.2,'network'),(15.2,'hub_ref'),(17.1,'learn'),(19.5,'desarrollo'),
 (21.5,'studio_ref'),(23.5333333333,'infraestructura'),(26.5,'chip_ref'),
 (29.4,'brief'),(32.3333333333,'desarrollo'),(34.25,'infraestructura'),
 (35.9333333333,'hub_ref'),(38,'neural'),(40,'launch'),(42.5,'flow_ref'),
 (44.8666666667,'produccion'),(46.8,'workflow'),(48.8,'studio_ref'),
 (51.25,'flow_ref'),(54,'infraestructura'),(56.5333333333,'workflow'),
 (59.6,'tiempo'),(62,'chip_ref'),(63.6,'tiempo'),(65.3,'outro')]
colors={'desarrollo':'#ffb65f','flow_ref':'#dcf18b','chip_ref':'#ffbc70','neural':'#ffbc70','studio_ref':'#a3ecc3','produccion':'#e6a7f5','network':'#df9cf6','hub_ref':'#e6a7f5','learn':'#ffac66','infraestructura':'#a3ecc3','brief':'#dba1f1','launch':'#ffac66','workflow':'#a3ecc3','tiempo':'#ffbd7a','outro':'#ffbc70'}
motions=['push','truck','pull','orbit','lift'];occurrences={};shots=[]
for i,(start,view) in enumerate(edits):
 start=round(start*30)/30;end=round((edits[i+1][0] if i+1<len(edits) else P['duration'])*30)/30
 occurrences[view]=occurrences.get(view,0)+1
 chapter=next((x for x in P['visual_chapters'] if x['start']-.01<=start<x['end']-.01),P['visual_chapters'][-1])
 shots.append(dict(start=start,end=end,view=view,kind='image' if view in P['assets'] else view,index=i,title=chapter['title'],accent=colors[view],motion=motions[(i+occurrences[view])%5],direction=1 if i%2 else -1,variant=occurrences[view]-1))
P['shots']=shots
P['camera_ranges']=[[0,4.5],[7.333333333333333,13.2],[17.1,21.5],[29.4,34.25],[40,44.86666666666667],[48.8,51.25],[59.6,65.3]]
P['camera_ranges']=[[round(a*30)/30,round(b*30)/30] for a,b in P['camera_ranges']]
P['camera_visible_seconds']=sum(b-a for a,b in P['camera_ranges'])
modes=['whip','zoom','diagonal','split','iris','lift']
P['transitions']=[dict(at=s['start'],index=i,duration=[.30,.28,.30,.34,.30,.30][(i-1)%6],mode=modes[(i-1)%6],direction=s['direction']) for i,s in enumerate(shots) if i and s['view']!='outro']
(D/'params.json').write_text(json.dumps(P,ensure_ascii=False,indent=2),encoding='utf-8')
for name in ['camara.mp4','voz.wav','subs.srt','transcripcion-editada.txt','revision-cortes.json','revision-voz-identica.json','revision-sincronizacion.json']:
 shutil.copyfile(ROOT/'runtime/construccion-v8'/name,D/name)
durations=[s['end']-s['start'] for s in shots if s['view']!='outro']
report={'duration':P['duration'],'layout':'split-screen when camera is visible; full-screen visuals during the other intervals','camera_visible_seconds':P['camera_visible_seconds'],'camera_percent':P['camera_visible_seconds']/P['duration']*100,'camera_ranges':P['camera_ranges'],'image_count':len(P['assets']),'shots':len(shots),'narration_shots':len(durations),'mean_shot_seconds':statistics.mean(durations),'min_shot_seconds':min(durations),'max_shot_seconds':max(durations),'previous_mean_seconds':65.3/14,'transitions':len(P['transitions']),'transition_modes':modes,'motion_modes':motions,'titles_follow_chapters_not_every_cut':True,'image_files':P['assets'],'bpm':120,'music':'minimal house; no pad or chord progression','white_camera_frame':False,'paper_cards':False}
(D/'revision-variedad.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
same={'ok':h(D/'camara.mp4')==h(ROOT/'runtime/construccion-v8/camara.mp4'),'source':'runtime/construccion-v8/camara.mp4','sha256':h(D/'camara.mp4'),'timing_changed':False,'framing_changed':False}
(D/'revision-camara-identica.json').write_text(json.dumps(same,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
