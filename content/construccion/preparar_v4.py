"""V4: visual revision only; retain the V3 audio, sync and captions exactly."""
from pathlib import Path
from collections import Counter
import json, shutil, subprocess, hashlib
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
D=ROOT/'runtime/construccion-v4'; D.mkdir(parents=True,exist_ok=True)
E=ROOT/'entregas/construccion-v4'; E.mkdir(parents=True,exist_ok=True)
P=json.loads((ROOT/'runtime/construccion-v3/params.json').read_text(encoding='utf-8'))
# A resource never returns after its scene. Camera remains the original speaking take.
sequence=[
 (0,'camera','close'),(2.2,'switch',''),(4.5,'wires',''),
 (7.333333333,'camera','medium'),(11.3,'community',''),
 (15.066666667,'camera','close'),(19.3,'learning',''),
 (23.533333333,'camera','medium'),(25.333333333,'foundation',''),
 (29.4,'idea',''),(32.333333333,'camera','close'),
 (35.933333333,'fit',''),(40,'sprint',''),
 (42.733333333,'camera','medium'),(44.866666667,'edit',''),
 (48.8,'agent',''),(53,'adjust',''),
 (56.533333333,'camera','close'),(59.6,'time',''),
 (62.4,'camera','medium'),(65.3,'outro','')
]
shots=[]
for i,(start,view,mode) in enumerate(sequence):
 start=round(start*30)/30
 end=round(sequence[i+1][0]*30)/30 if i+1<len(sequence) else P['duration']
 chapter=next((p['i'] for p in P['paragraphs'] if p['start']<=start+.001<p['end']),7)
 shots.append(dict(start=start,end=end,view=view,camera_mode=mode,chapter=chapter))
P['shots']=shots
# Deterministic waveform from the real microphone audio for the editing scene.
pcm=subprocess.run(['ffmpeg','-v','error','-i',str(ROOT/'runtime/construccion-v3/microfono-editado.wav'),'-f','f32le','-ac','1','-ar','8000','-'],capture_output=True,check=True).stdout
y=np.frombuffer(pcm,dtype=np.float32); bins=np.array_split(y,84)
waveform=[float(np.sqrt(np.mean(b*b))) for b in bins]
m=max(waveform) or 1
P['waveform']=[round(max(.06,x/m),3) for x in waveform]
(D/'params.json').write_text(json.dumps(P,ensure_ascii=False,indent=2),encoding='utf-8')
for name in ['subs.srt','transcripcion-editada.txt','audio-procedencia.json','revision-cortes.json']:
 shutil.copyfile(ROOT/'runtime/construccion-v3'/name,D/name)
views=Counter(s['view'] for s in shots if s['view']!='camera')
assert max(views.values())==1
assert all(abs(a['end']-b['start'])<1e-6 for a,b in zip(shots,shots[1:]))
stats={'duration':P['duration'],'shots':len(shots),'camera_seconds':round(sum(s['end']-s['start'] for s in shots if s['view']=='camera'),2),'distinct_visual_scenes':len(views),'repeated_visual_scenes':[],'background_images':7,'new_generated_images':5,'audio':'V3 AAC track copied without re-encoding','subtitles_sha256':hashlib.sha256((D/'subs.srt').read_bytes()).hexdigest()}
(D/'revision-variedad.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(stats,ensure_ascii=False))
