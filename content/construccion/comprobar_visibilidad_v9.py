"""Inspect PNG alpha to verify camera is hidden throughout full-screen scene samples."""
from pathlib import Path
from PIL import Image,ImageDraw
import json,math
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'runtime/construccion-v9';P=json.loads((D/'params.json').read_text(encoding='utf-8'))
out=Image.new('RGB',(6*186,math.ceil(len(P['shots'])/6)*350),'#0b0c11');draw=ImageDraw.Draw(out);checks=[]
for i,s in enumerate(P['shots']):
 t=(s['start']+s['end'])/2;show=any(a<=t<b for a,b in P['camera_ranges'])
 f=D/'revision'/f'{i:02}-{s["view"]}.png';im=Image.open(f).convert('RGBA')
 alpha=im.getpixel((540,500))[3];ok=alpha==(0 if show else 255)
 checks.append({'time':t,'view':s['view'],'camera_visible':show,'overlay_alpha':alpha,'ok':ok})
 thumb=Image.new('RGB',im.size,'#26232c');thumb.paste(im,mask=im.getchannel('A'));thumb.thumbnail((180,320));x=(i%6)*186;y=(i//6)*350;out.paste(thumb,(x+3,y));draw.text((x+3,y+324),f'{i:02} '+('CARA' if show else 'VISUAL'),fill='white')
out.save(D/'contacto-modos.jpg',quality=92)
r={'ok':all(x['ok'] for x in checks),'camera_seconds':P['camera_visible_seconds'],'camera_percent':100*P['camera_visible_seconds']/P['duration'],'checks':checks}
(D/'revision-visibilidad.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps({'ok':r['ok'],'samples':len(checks),'camera_seconds':r['camera_seconds']}));assert r['ok']
