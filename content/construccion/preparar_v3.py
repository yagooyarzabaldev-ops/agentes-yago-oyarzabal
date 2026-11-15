"""V3: remove voiced fillers and false starts, not only silence. Keep mic/camera aligned."""
from pathlib import Path
import json,re,subprocess
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'runtime/construccion-v3';D.mkdir(parents=True,exist_ok=True)
M=ROOT/'runtime/construccion-material';a='C:/Users/oyarz/Desktop/IA Experiencia.wav';v='D:/PRODUCCION VIDEO/VID_20261114_190637138.mp4'
offset=json.loads((M/'sincronizacion-verificada.json').read_text())['offset_mean']
ws=[w.copy() for s in json.loads((M/'audio-transcripcion.json').read_text(encoding='utf-8'))['segments'] for w in s['words']]
ws[136]['w']='enchufes';ws[136]['end']=77.02;ws[137]['w']='';ws[141]['w']='prender'
# Local, focused ASR found retries that the full-take transcript collapsed into one word.
ws[89].update(start=51.19,end=52.02)
ws[117].update(start=67.66,end=68.09)
ws[138].update(start=77.04,end=77.18)
ws[139].update(start=78.74,end=79.33)
ws[165].update(start=90.82,end=91.00)
ws[166].update(start=92.24,end=92.64)
chapters=[('enchufe',74.18,84.79),('experiencia',2.65,9.67),('comunidad',12.30,16.42),
 ('aprendizaje',17.29,31.97),('implementar',44.15,58.49),('resultado',59.43,70.21),
 ('mejorar',86.18,104.55),('cierre',106.91,107.90)]
allowed=[set(range(132,154)),set(range(2,17)),set(range(19,28)),set(range(29,54)),set(range(76,103)),set(range(103,125)),set(range(156,190)),set(range(190,193))]
manual=[
 {'start':49.59,'end':51.13,'reason':'Quitar la vacilación antes de la toma clara de «implementar»'},
 {'start':66.80,'end':67.65,'reason':'Quitar el arranque «de la primera…», conservar «desde el primer momento»'},
 {'start':77.18,'end':78.70,'reason':'Quitar las repeticiones yyy antes de «teclas»; conservar una conjunción breve'},
 {'start':91.00,'end':92.20,'reason':'Quitar la vacilación tras «o» y antes de la toma clara de «agregar»'},
]
r=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',a,'-af','silencedetect=noise=-38dB:d=0.35','-f','null','-'],capture_output=True,text=True,encoding='utf-8',errors='replace',check=True)
sil=[];s=None
for line in r.stderr.splitlines():
 if 'silence_start:' in line:s=float(line.split('silence_start:')[1])
 if 'silence_end:' in line and s is not None:
  e=float(line.split('silence_end:')[1].split('|')[0]);sil.append((s,e));s=None
clips=[];paras=[];mapped=[];cursor=0
for ci,(label,start,end) in enumerate(chapters):
 cuts=[(max(start,x['start']),min(end,x['end'])) for x in manual if x['start']<end and x['end']>start]
 cuts += [(s+.085,e-.095) for s,e in sil if s>=start and e<=end and e-s>.38]
 merged=[]
 for s,e in sorted(cuts):
  if merged and s<=merged[-1][1]:merged[-1]=(merged[-1][0],max(e,merged[-1][1]))
  else:merged.append((s,e))
 spans=[];prev=start
 for s,e in merged:
  if s-prev>.02:spans.append((prev,s))
  prev=e
 if end-prev>.02:spans.append((prev,end))
 beginning=cursor
 for s,e in spans:
  frames=max(1,round((e-s)*30));dur=frames/30;e=s+dur
  clips.append({'index':len(clips),'chapter':ci,'label':label,'mic_start':s,'mic_end':e,'camera_start':s+offset,'camera_end':e+offset,'start':cursor,'end':cursor+dur,'frames':frames})
  for wi,w in enumerate(ws):
   if wi not in allowed[ci] or not w['w'] or w['end']<=s or w['start']>=e:continue
   mapped.append({'source_index':wi,'w':w['w'],'start':cursor+max(s,w['start'])-s,'end':cursor+min(e,w['end'])-s,'chapter':ci})
  cursor+=dur
 paras.append({'i':ci,'label':label,'start':beginning,'end':cursor,'text':' '.join(ws[i]['w'] for i in sorted(allowed[ci]) if ws[i]['w'])})
words=[]
for w in mapped:
 if words and (w['source_index'],w['chapter'])==(words[-1]['source_index'],words[-1]['chapter']):words[-1]['end']=w['end']
 else:words.append(w)
for w in words:w.update(start=round(w['start'],4),end=round(w['end'],4))
patterns={
 0:[('camera',1.15),('socket',1.5),('switch',1.3),('camera',1.15),('wires',99)],
 1:[('camera',2),('desk',1.7),('camera',99)],
 2:[('camera',1.8),('notes',99)],
 3:[('camera',2.1),('learn',1.7),('camera',2.1),('desk',1.8),('camera',2.1),('building',99)],
 4:[('idea',1.6),('camera',2.1),('oops',1.5),('camera',2.0),('agent',1.9),('camera',99)],
 5:[('camera',2),('go',1.8),('camera',2),('target',1.5),('camera',99)],
 6:[('wires',1.8),('camera',2),('agent',2),('camera',2),('desk',1.8),('camera',1.8),('target',1.8),('camera',99)],
 7:[('camera',99)]}
shots=[]
for c in paras:
 p=c['start']
 for view,dur in patterns[c['i']]:
  if p>=c['end']-.04:break
  end=min(c['end'],p+dur)
  shots.append({'index':len(shots),'start':round(p,6),'end':round(end,6),'view':view,'chapter':c['i'],'camera_mode':'close' if len(shots)%2 else 'medium'})
  p=end
voice_end=cursor;duration=round((cursor+1.8)*30)/30
shots.append({'index':len(shots),'start':cursor,'end':duration,'view':'outro','chapter':8,'camera_mode':'medium'})
captions=[]
for p in paras:
 chunk=[]
 for w in [w for w in words if w['chapter']==p['i']]:
  if len(chunk)>=3 or (sum(len(x['w'])+1 for x in chunk)+len(w['w'])>22 and chunk):captions.append(chunk);chunk=[]
  chunk.append(w)
  if re.search(r'[.!?;:]$',w['w']):captions.append(chunk);chunk=[]
 if chunk:captions.append(chunk)
params={'duration':duration,'voice_end':voice_end,'paragraphs':paras,'words':words,'captions':captions,'shots':shots,'source_audio':a,'source_video':v,'camera_offset':offset,'fps':30,'bpm':114}
for name,obj in [('params.json',params),('edl.json',{'audio':a,'video':v,'offset':offset,'speed':1,'clips':clips,'manual_removals':manual,'silence_padding_seconds':.18}),('words.json',{'source':'original microphone; corrected alignment around false starts','words':words})]:
 (D/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def ts(t):
 ms=round(t*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000);return f'{h:02}:{m:02}:{s:02},{ms:03}'
(D/'subs.srt').write_text('\n\n'.join(f'{i+1}\n{ts(c[0]["start"])} --> {ts(c[-1]["end"])}\n'+ ' '.join(w['w'] for w in c) for i,c in enumerate(captions))+'\n',encoding='utf-8')
(D/'transcripcion-editada.txt').write_text('\n\n'.join(c['text'] for c in paras)+'\n',encoding='utf-8')
print(json.dumps({'duration':duration,'voice_end':voice_end,'clips':len(clips),'shots':len(shots),'camera_seconds':sum(s['end']-s['start'] for s in shots if s['view']=='camera'),'paragraphs':paras},ensure_ascii=False,indent=2))
