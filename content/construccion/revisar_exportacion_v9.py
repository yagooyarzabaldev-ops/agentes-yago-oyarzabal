"""Extract the final split-screen, all scene thumbnails and one transition."""
from pathlib import Path
import json,subprocess,math,concurrent.futures
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'runtime/construccion-v9';E=ROOT/'entregas/construccion-v9';R=D/'revision-final';R.mkdir(parents=True,exist_ok=True)
P=json.loads((D/'params.json').read_text(encoding='utf-8'));OUT=E/'Sistemas_con_IA_Yago_v9.mp4'
def frame(t,name):
 dest=R/(name+'.png');subprocess.run(['ffmpeg','-v','error','-ss',str(t),'-i',str(OUT),'-frames:v','1','-y',str(dest)],check=True);return dest
full=[(1.2,'codigo'),(10.2,'equipo'),(35.1,'infraestructura'),(52.5,'flujo')]
transition_sets={label:[P['transitions'][j]['at']+P['transitions'][j]['duration']*p for p in [0,.2,.4,.7,1.05]] for label,j in [('barrido',0),('a-pantalla-completa',1),('regreso-camara',3)]}
jobs=full+[((s['start']+s['end'])/2,f'escena-{i:02}') for i,s in enumerate(P['shots'])]+[(t,f'{label}-{i}') for label,times in transition_sets.items() for i,t in enumerate(times)]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 list(pool.map(lambda x:frame(*x),jobs))
sheet=Image.new('RGB',(5*228,math.ceil(len(P['shots'])/5)*430),'#0b0c11');draw=ImageDraw.Draw(sheet)
for i,s in enumerate(P['shots']):
 dest=R/f'escena-{i:02}.png';im=Image.open(dest).convert('RGB');im.thumbnail((216,384));x=(i%5)*228;y=(i//5)*430;sheet.paste(im,(x+6,y));draw.text((x+6,y+390),f'{i+1:02} / {s["view"]}',fill='white')
sheet.save(E/'contacto-31-planos.jpg',quality=92)
for label,times in transition_sets.items():
 sheet=Image.new('RGB',(5*228,410),'#0b0c11');draw=ImageDraw.Draw(sheet)
 for i,t in enumerate(times):
  dest=R/f'{label}-{i}.png';im=Image.open(dest).convert('RGB');im.thumbnail((214,380));sheet.paste(im,(i*228+7,0));draw.text((i*228+7,385),f'{t:.3f}s',fill='white')
 sheet.save(R/(label+'.jpg'),quality=92)
print(json.dumps({'samples':4,'scenes':len(P['shots']),'transition_samples':15,'path':str(R)},ensure_ascii=False))
