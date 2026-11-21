"""V5: narración original; transformación de sistemas con IA como historia visual."""
from pathlib import Path
from collections import Counter
import json,shutil,hashlib
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'runtime/construccion-v5';D.mkdir(parents=True,exist_ok=True)
E=ROOT/'entregas/construccion-v5';E.mkdir(parents=True,exist_ok=True)
P=json.loads((ROOT/'runtime/construccion-v4/params.json').read_text(encoding='utf-8'))
mapping={'switch':'skin','wires':'system','community':'manual','learning':'iterate','foundation':'layers','idea':'brief','fit':'context','sprint':'launch','edit':'phone','agent':'orchestrate','adjust':'unify','time':'time','outro':'outro'}
for s in P['shots']:s['view']=mapping.get(s['view'],s['view'])
modes=['split','peel','iris','strips','slide','split','iris','strips','page','slide','split','iris','strips','page','strips','split','iris','page','slide','strips']
P['transitions']=[{'at':s['start'],'index':i,'mode':modes[i-1],'duration':.44 if modes[i-1] in ['iris','page','strips'] else .36} for i,s in enumerate(P['shots']) if i>0 and i!=2]
P['sound_events']=[{'at':2.24,'kind':'click'},{'at':3.293,'kind':'click'},{'at':3.813,'kind':'click'},
 {'at':4.5,'kind':'open'},{'at':11.3,'kind':'paper'},{'at':19.75,'kind':'paper'},
 {'at':21.6256,'kind':'open'},{'at':25.36,'kind':'open'},{'at':29.9,'kind':'type'},
 {'at':31.3,'kind':'send'},{'at':36.9,'kind':'tap'},{'at':38.5,'kind':'tap'},
 {'at':41.15,'kind':'click'},{'at':45.65,'kind':'open'},{'at':48.8,'kind':'send'},
 {'at':50.3,'kind':'click'},{'at':53.05,'kind':'paper'},{'at':59.6,'kind':'open'},{'at':65.3,'kind':'resolve'}]
P['music_breaks']=[[3.813,4.45],[32.26,32.6],[38.3,39.96]]
(D/'params.json').write_text(json.dumps(P,ensure_ascii=False,indent=2),encoding='utf-8')
for f in ['subs.srt','transcripcion-editada.txt','revision-cortes.json']:
 shutil.copyfile(ROOT/'runtime/construccion-v3'/f,D/f)
voice=ROOT/'runtime/construccion-v3/voz.wav'
shutil.copyfile(voice,D/'voz.wav')
same=hashlib.sha256(voice.read_bytes()).hexdigest()==hashlib.sha256((D/'voz.wav').read_bytes()).hexdigest()
(D/'revision-voz-identica.json').write_text(json.dumps({'ok':same,'source':str(voice),'sha256':hashlib.sha256(voice.read_bytes()).hexdigest(),'speech_speed':1,'narration_retimed':False,'camera_offset_seconds':2.3429},indent=2),encoding='utf-8')
assert same
views=Counter(s['view'] for s in P['shots'] if s['view']!='camera');assert max(views.values())==1
(D/'revision-variedad.json').write_text(json.dumps({'ok':True,'visual_scenes':len(views),'repeated_scenes':[],'camera_shots':sum(s['view']=='camera' for s in P['shots']),'phone_with_original_video':True,'visual_focus':'Cambio de sistemas con IA; electricidad solamente en la analogía hablada','electricity_images_used':False,'duration':P['duration']},ensure_ascii=False,indent=2),encoding='utf-8')
# Unused concept explorations are preserved, explicitly excluded from the final video.
A=ROOT/'content/construccion/assets-v5/procedencia.json';a=json.loads(A.read_text(encoding='utf-8'))
for item in a['assets']:item['used_in_v5']=item['name']=='tiempo'
A.write_text(json.dumps(a,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'duration':P['duration'],'shots':len(P['shots']),'voice_preserved':same,'focus':'sistemas con IA'},ensure_ascii=False))
