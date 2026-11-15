"""Review the exported scenes, transition frames and actual grayscale camera pixels."""
from pathlib import Path
import json,subprocess,math,concurrent.futures,sys
from PIL import Image,ImageDraw
import numpy as np
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'runtime/construccion-v10';E=ROOT/'entregas/construccion-v10';R=D/'revision-final';R.mkdir(parents=True,exist_ok=True)
P=json.loads((D/'params.json').read_text(encoding='utf-8'));OUT=E/'Sistemas_con_IA_Yago_v10.mp4'
def frame(t,name):
 dest=R/(name+'.png');subprocess.run(['ffmpeg','-v','error','-ss',str(t),'-i',str(OUT),'-frames:v','1','-y',str(dest)],check=True);return dest
full=[(1.1,'camara-color'),(19.6,'aclaracion-1'),(38.4,'aclaracion-2'),(48.2,'aclaracion-3'),(24.6,'base-completa'),(34.5,'negocio-completo')]
selected=[next(tr for tr in P['transitions'] if tr['mode']==m and tr['duration']>0) for m in ['fold','particles','match']]
sets={tr['mode']:[tr['at']+tr['duration']*p for p in [0,.2,.4,.7,1.05]] for tr in selected}
jobs=full+[((s['start']+s['end'])/2,f'escena-{i:02}') for i,s in enumerate(P['shots'])]+[(t,f'{k}-{i}') for k,ts in sets.items() for i,t in enumerate(ts)]
if '--reuse-frames' not in sys.argv:
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(lambda x:frame(*x),jobs))
sheet=Image.new('RGB',(5*228,math.ceil(len(P['shots'])/5)*430),'#0b0c11');draw=ImageDraw.Draw(sheet)
for i,s in enumerate(P['shots']):
 im=Image.open(R/f'escena-{i:02}.png').convert('RGB');im.thumbnail((216,384));x=(i%5)*228;y=(i//5)*430;sheet.paste(im,(x+6,y));draw.text((x+6,y+390),f'{i+1:02} / {s["view"]}',fill='white')
sheet.save(E/'contacto-35-planos.jpg',quality=92)
for k,ts in sets.items():
 sh=Image.new('RGB',(5*228,410),'#0b0c11');dr=ImageDraw.Draw(sh)
 for i,t in enumerate(ts):
  im=Image.open(R/f'{k}-{i}.png').convert('RGB');im.thumbnail((214,380));sh.paste(im,(i*228+7,0));dr.text((i*228+7,385),f'{t:.3f}s',fill='white')
 sh.save(R/(k+'.jpg'),quality=92)
checks=[]
for name in ['camara-color','aclaracion-1','aclaracion-2','aclaracion-3']:
 a=np.array(Image.open(R/(name+'.png')).convert('RGB').crop((100,200,950,680))).astype(float)
 chroma=float(np.mean(a.max(axis=2)-a.min(axis=2)));expected=name!='camara-color';checks.append({'sample':name,'mean_channel_spread':round(chroma,3),'grayscale_expected':expected,'ok':chroma<4 if expected else chroma>8})
report={'ok':all(x['ok'] for x in checks),'grayscale_checks':checks,'scene_samples':len(P['shots']),'transition_samples':15,'full_frames':len(full),'camera_seconds':P['camera_visible_seconds'],'bw_seconds':P['bw_seconds']}
(E/'revision-exportacion.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
if not report['ok']:raise SystemExit(1)
