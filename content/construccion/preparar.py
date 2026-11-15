"""Build deterministic scene parameters from the actual narration alignment."""
from pathlib import Path
import json, re

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'runtime/construccion-v1'
voice=json.loads((OUT/'voz.json').read_text(encoding='utf-8'))
words=json.loads((OUT/'words.json').read_text(encoding='utf-8'))['words']
duration=voice['duration']+.7
params={'duration':duration,'paragraphs':voice['paragraphs'],'words':words}
def stamp(t):
 ms=round(t*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
 return f'{h:02}:{m:02}:{s:02},{ms:03}'
cues=[]
for p in voice['paragraphs']:
 ws=[w for w in words if p['start']-.01<=w['start']<p['end']]
 chunk=[]
 for w in ws:
  if len(chunk)>=4 or (sum(len(x['w'])+1 for x in chunk)+len(w['w'])>26 and chunk):
   cues.append(chunk);chunk=[]
  chunk.append(w)
  if re.search(r'[.!?;:]$',w['w']):
   cues.append(chunk);chunk=[]
 if chunk:cues.append(chunk)
params['captions']=cues
(OUT/'params.json').write_text(json.dumps(params,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'subs.srt').write_text('\n\n'.join(f'{i+1}\n{stamp(c[0]["start"])} --> {stamp(c[-1]["end"])}\n'+ ' '.join(w['w'] for w in c) for i,c in enumerate(cues))+'\n',encoding='utf-8')
print(json.dumps({'duration':duration,'paragraphs':len(voice['paragraphs']),'words':len(words),'captions':len(cues)}))
