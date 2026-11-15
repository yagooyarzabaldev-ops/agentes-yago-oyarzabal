"""Extract final-composite samples, including a transition back to the real camera."""
from pathlib import Path
import json,subprocess
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2]
D=ROOT/'runtime/construccion-v6'
E=ROOT/'entregas/construccion-v6'
OUT=E/'Sistemas_con_IA_Yago_v6.mp4'
R=D/'revision-final'
R.mkdir(parents=True,exist_ok=True)
P=json.loads((D/'params.json').read_text(encoding='utf-8'))

def frame(t,name):
    dest=R/(name+'.png')
    subprocess.run(['ffmpeg','-v','error','-ss',str(t),'-i',str(OUT),'-frames:v','1','-y',str(dest)],check=True)
    return dest

for t,name in [(0.8,'camara'),(30.1,'coral'),(46.5,'telefono'),(50.5,'flujo')]:
    frame(t,name)
tr=next(tr for tr in P['transitions'] if P['shots'][tr['index']]['view']=='camera')
times=[tr['at']+tr['duration']*p for p in [0,.2,.4,.7,1.05]]
sheet=Image.new('RGB',(5*228,410),'#fff0d2')
draw=ImageDraw.Draw(sheet)
for i,t in enumerate(times):
    path=frame(t,f'transicion-{i}')
    im=Image.open(path).convert('RGB');im.thumbnail((214,380))
    sheet.paste(im,(i*228+7,0));draw.text((i*228+7,385),f'{t:.3f}s',fill='#292123')
sheet.save(R/'transicion.jpg',quality=92)
print(json.dumps({'samples':4,'transition':tr,'transition_samples':5,'path':str(R)},ensure_ascii=False))
