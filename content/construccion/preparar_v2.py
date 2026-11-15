"""Edit the user's original microphone take and align every cut to camera time."""
from pathlib import Path
import json,re,subprocess,math
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
D=ROOT/'runtime/construccion-v2';D.mkdir(parents=True,exist_ok=True)
M=ROOT/'runtime/construccion-material'
audio='C:/Users/oyarz/Desktop/IA Experiencia.wav'
video='D:/PRODUCCION VIDEO/VID_20261114_190637138.mp4'
offset=json.loads((M/'sincronizacion-verificada.json').read_text())['offset_mean']
source=json.loads((M/'audio-transcripcion.json').read_text(encoding='utf-8'))
ws=[w.copy() for s in source['segments'] for w in s['words']]
# Correct clear ASR spelling, never synthesize or replace speech.
ws[136]['w']='enchufes';ws[136]['end']=ws[137]['end'];ws[137]['w']=''
ws[141]['w']='prender'
# Reordered hook; all content remains the original microphone recording.
chapters=[
 ('analogía',74.18,84.79),
 ('experiencia',2.65,9.79),
 ('comunidad',12.30,16.55),
 ('aprender',17.28,31.97),
 ('implementar',44.15,58.49),
 ('objetivo',59.43,70.21),
 ('sistema',86.18,104.55),
 ('cierre',106.91,107.90),
]
p=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',audio,'-af','silencedetect=noise=-38dB:d=0.45','-f','null','-'],capture_output=True,text=True,encoding='utf-8',errors='replace',check=True)
silences=[];start=None
for line in p.stderr.splitlines():
 if 'silence_start:' in line:start=float(line.split('silence_start:')[1])
 if 'silence_end:' in line and start is not None:
  end=float(line.split('silence_end:')[1].split('|')[0]);silences.append((start,end));start=None
# Keep ~280ms of each long pause; 140ms either side avoids clipping soft consonants.
clips=[];timeline=[];cursor=0;mapped=[]
allowed=[range(132,154),range(2,18),range(19,29),range(29,54),range(76,103),range(103,125),range(156,190),range(190,193)]
for ci,(label,begin,end) in enumerate(chapters):
 spans=[];s=begin
 for a,b in silences:
  if a>=begin and b<=end and b-a>.48:
   spans.append((s,a+.14));s=b-.14
 spans.append((s,end))
 chapter_start=cursor
 for a,b in spans:
  frames=max(1,round((b-a)*30));dur=frames/30;b=a+dur
  clips.append({'index':len(clips),'chapter':ci,'label':label,'mic_start':a,'mic_end':b,
    'camera_start':a+offset,'camera_end':b+offset,'start':cursor,'end':cursor+dur,'frames':frames})
  # A word may span a trimmed pause; retain its voiced intersection, then merge later.
  for wi,w in enumerate(ws):
   if wi not in allowed[ci] or not w['w'] or w['end']<=a or w['start']>=b:continue
   mapped.append({'source_index':wi,'w':w['w'],'start':cursor+max(a,w['start'])-a,
    'end':cursor+min(b,w['end'])-a,'chapter':ci})
  cursor+=dur
 timeline.append({'i':ci,'label':label,'start':chapter_start,'end':cursor,
  'text':' '.join(ws[k]['w'] for k in allowed[ci] if ws[k]['w'])})
# Merge duplicate fragments from a single word around pause compression.
words=[]
for w in mapped:
 if words and words[-1]['source_index']==w['source_index'] and words[-1]['chapter']==w['chapter']:
  words[-1]['end']=w['end']
 else:words.append(w)
for w in words:
 w['start']=round(w['start'],4);w['end']=round(w['end'],4)
# Deliberate camera / graphic cuts within each thought; cut points are independent of silence trims.
patterns={0:[('camera',2.0),('switch',3.4),('camera',1.4),('wire',99)],
 1:[('camera',2.6),('identity',2.1),('camera',99)],
 2:[('camera',99)],
 3:[('camera',3.0),('learn',2.8),('camera',2.8),('stack',99)],
 4:[('idea',2.6),('camera',2.7),('pipeline',3.0),('camera',99)],
 5:[('camera',2.7),('result',2.9),('camera',99)],
 6:[('wire',2.2),('pipeline',2.8),('camera',3.0),('code',2.6),('camera',99)],
 7:[('camera',99)]}
shots=[]
for c in timeline:
 pos=c['start']
 for view,length in patterns[c['i']]:
  if pos>=c['end']-.03:break
  end=min(c['end'],pos+length)
  shots.append({'index':len(shots),'start':round(pos,6),'end':round(end,6),'view':view,'chapter':c['i'],
   'camera_mode':'medium' if len(shots)%3 else 'close'})
  pos=end
voice_end=cursor
shots.append({'index':len(shots),'start':cursor,'end':cursor+2.2,'view':'outro','chapter':8,'camera_mode':'medium'})
duration=round((cursor+2.2)*30)/30
cues=[]
for c in timeline:
 chunk=[]
 for w in [x for x in words if x['chapter']==c['i']]:
  if len(chunk)>=4 or (sum(len(x['w'])+1 for x in chunk)+len(w['w'])>25 and chunk):cues.append(chunk);chunk=[]
  chunk.append(w)
  if re.search(r'[.!?;:]$',w['w']):cues.append(chunk);chunk=[]
 if chunk:cues.append(chunk)
params={'duration':duration,'voice_end':voice_end,'paragraphs':timeline,'shots':shots,'words':words,'captions':cues,
 'source_audio':audio,'source_video':video,'camera_offset':offset,'source_kind':'real_microphone_recording'}
for name,data in [('params.json',params),('edl.json',{'audio':audio,'video':video,'offset':offset,'speed':1,'clips':clips}),('words.json',{'source':'original microphone; local ASR with spelling corrections','words':words})]:
 (D/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def ts(t):
 m=round(t*1000);h,m=divmod(m,3600000);mi,m=divmod(m,60000);s,m=divmod(m,1000);return f'{h:02}:{mi:02}:{s:02},{m:03}'
(D/'subs.srt').write_text('\n\n'.join(f'{i+1}\n{ts(c[0]["start"])} --> {ts(c[-1]["end"])}\n'+ ' '.join(w['w'] for w in c) for i,c in enumerate(cues))+'\n',encoding='utf-8')
(D/'transcripcion-editada.txt').write_text('\n\n'.join(c['text'] for c in timeline)+'\n',encoding='utf-8')
print(json.dumps({'duration':duration,'voice_end':voice_end,'clips':len(clips),'shots':len(shots),'camera_seconds':sum(s['end']-s['start'] for s in shots if s['view']=='camera'),'chapters':timeline},ensure_ascii=False,indent=2))
