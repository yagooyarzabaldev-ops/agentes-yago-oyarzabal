from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];B=ROOT/'content/construccion'
s=(B/'escena_v6.html').read_text(encoding='utf-8')
a=s.index('for(const [key,url]');b=s.index('const cameraThemes',a)
keys=['neural','manual_ref','chip_ref','hub_ref','launch','studio_ref','flow_ref','time']
s=s[:a]+"for(const key of "+repr(keys)+"){const im=new Image();im.src='assets-v7/'+key+'.png';images[key]=im}\n"+s[b:]
# Later function declarations replace the V6 scene implementations, sharing drawing utilities.
a=s.index('const funcs=')
s=s[:a]+(B/'v7-motion.js').read_text(encoding='utf-8')+'\n'+s[a:]
# Remove the old transition declaration so the new five transition styles are authoritative.
a=s.index('function transition(tr,t){',s.index('const transitionCache='));b=s.index('function render(t)',a)
s=s[:a]+s[b:]
s=s.replace("text('IA EN LA PRÁCTICA',925,1712,19,'#6b5d55'", "text('IA EN LA PRÁCTICA',925,1712,19,paper?'#6b5d55':'#c7bfc6'")
s=s.replace("el.style.setProperty('--active',B);", "el.style.setProperty('--active',B);el.style.setProperty('--active-ink',inkFor(B));")
s=s.replace('color:#fff8ed;text-shadow:none;transform','color:var(--active-ink,#fff8ed);text-shadow:none;transform')
s=s.replace('background:var(--active,#a92e4d);color:#fff8ed}', 'background:var(--active,#a92e4d);color:var(--active-ink,#fff8ed)}')
(B/'escena_v7.html').write_text(s,encoding='utf-8')
print('V7 dimensional motion template created.')
