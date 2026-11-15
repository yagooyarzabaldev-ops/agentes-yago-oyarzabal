"""Extract the final split-screen, all scene thumbnails and one transition."""
from pathlib import Path
import json,subprocess
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'runtime/construccion-v8';E=ROOT/'entregas/construccion-v8';R=D/'revision-final';R.mkdir(parents=True,exist_ok=True)
P=json.loads((D/'params.json').read_text(encoding='utf-8'));OUT=E/'Sistemas_con_IA_Yago_v8.mp4'
def frame(t,name):
 dest=R/(name+'.png');subprocess.run(['ffmpeg','-v','error','-ss',str(t),'-i',str(OUT),'-frames:v','1','-y',str(dest)],check=True);return dest
for t,name in [(1.2,'codigo'),(10.2,'equipo'),(34.2,'infraestructura'),(51.2,'flujo')]:frame(t,name)
sheet=Image.new('RGB',(5*228,3*430),'#0b0c11');draw=ImageDraw.Draw(sheet)
for i,s in enumerate(P['shots']):
 dest=frame((s['start']+s['end'])/2,f'escena-{i:02}');im=Image.open(dest).convert('RGB');im.thumbnail((216,384));x=(i%5)*228;y=(i//5)*430;sheet.paste(im,(x+6,y));draw.text((x+6,y+390),f'{i+1:02} / {s["view"]}',fill='white')
sheet.save(E/'contacto-15-escenas.jpg',quality=92)
tr=P['transitions'][0];sheet=Image.new('RGB',(5*228,410),'#0b0c11');draw=ImageDraw.Draw(sheet)
for i,p in enumerate([0,.2,.4,.7,1.05]):
 t=tr['at']+tr['duration']*p;dest=frame(t,f'transicion-{i}');im=Image.open(dest).convert('RGB');im.thumbnail((214,380));sheet.paste(im,(i*228+7,0));draw.text((i*228+7,385),f'{t:.3f}s',fill='white')
sheet.save(R/'transicion.jpg',quality=92)
print(json.dumps({'samples':4,'scenes':15,'transition_samples':5,'path':str(R)},ensure_ascii=False))
