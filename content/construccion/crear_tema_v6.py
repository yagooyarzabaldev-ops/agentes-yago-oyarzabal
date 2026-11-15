"""Build the warm editorial V6 while retaining the reviewed V5 animation timing."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'content/construccion'
s=(BASE/'escena_v5.html').read_text(encoding='utf-8')
s=s.replace("const N='#091326',B='#295bff',O='#ffb46c',F='#fff4df',L='#e5ff64',G='#7b91ae',cl=x=>", "let N='#292123',B='#a92e4d',O='#f1ae7b',F='#fff7e8',L='#c3de9b',G='#706158';let T;\nconst cl=x=>")
s=s.replace("let boxes=[],paper=false;", "let boxes=[],paper=true;")
s=s.replace("const img=new Image();img.src='assets-v5/tiempo.png';", '''const images={};
for(const [key,url] of Object.entries({manual:'assets-v6/manual.png',flow:'assets-v6/flujo.png',time:'assets-v4/tiempo.png'})){const im=new Image();im.src=url;images[key]=im}
const cameraThemes=[['#fff0d2','#a92e4d','#f6b58e'],['#ffd4b7','#8b3c2b','#d7e7a9'],['#dcedce','#256446','#ffb17c'],['#e9dced','#75416f','#f3b48f'],['#ffedbf','#944b21','#e3c1dd'],['#fff0ca','#6d386b','#e8b08c'],['#fbd8cf','#9c3548','#d5e3b4'],['#dcedce','#256446','#ffb17c']];
const sceneThemes={skin:['#ffe071','#a42f4b','#f3a888'],system:['#d9eccb','#286346','#ed9873'],manual:['#f4ddbe','#903c3a','#e5be81'],iterate:['#e7d9ed','#6e3b75','#f3a178'],layers:['#f8eed7','#315c43','#e6a375'],brief:['#fb967f','#6f3045','#ffe4ac'],context:['#d9e79b','#563954','#efb58e'],launch:['#f9d5d7','#873f63','#ffe696'],phone:['#ffcfb0','#94442d','#c4dc9b'],orchestrate:['#f7c8ae','#684670','#9ac6a5'],unify:['#e6d9ec','#74415f','#e7b386'],time:['#f7e5c7','#8b4b24','#c3d6a9'],outro:['#f4d75a','#993d53','#f7ad83']};
function themeFor(shot){const a=shot.view==='camera'?cameraThemes[shot.start>62?7:Math.min(7,shot.chapter)]:sceneThemes[shot.view];return{bg:a[0],accent:a[1],secondary:a[2],name:shot.view}}
function useTheme(theme){T=theme;B=T.accent;O=T.secondary;paper=true}
function inkFor(hex){const a=hex.replace('#','');const v=[0,2,4].map(i=>parseInt(a.slice(i,i+2),16));return v[0]*.299+v[1]*.587+v[2]*.114>155?N:F}
function shadeColor(hex,f=-.2){return '#'+[0,2,4].map(i=>{const value=Math.max(0,Math.min(255,Math.round(parseInt(hex.slice(i+1,i+3),16)*(1+f))));return value.toString(16).padStart(2,'0')}).join('')}
const grain=document.createElement('canvas');grain.width=128;grain.height=128;const gc=grain.getContext('2d');let seed=14116;
for(let i=0;i<1900;i++){seed=(seed*1664525+1013904223)>>>0;const x=seed%128;seed=(seed*1664525+1013904223)>>>0;const y=seed%128;gc.fillStyle=i%3?'rgba(65,37,22,.065)':'rgba(255,255,250,.22)';gc.fillRect(x,y,1,i%7===0?3:1)}
function texture(){c.save();c.globalAlpha=.7;c.fillStyle=c.createPattern(grain,'repeat');c.fillRect(0,0,W,H);c.restore()}
function tape(x,y,w=185,h=55,angle=-.07){c.save();c.translate(x,y);c.rotate(angle);rect(0,0,w,h,'#f7da9dcc',1);for(let i=0;i<14;i++)line([[i*13,0],[i*13+8,h]],'#b4935c16',1);c.restore()}
function warmPhoto(im,u,zoom=1.04){cover(im,zoom+.012*u,Math.sin(u*.45)*13,-10*u);const g=c.createLinearGradient(0,0,0,H);g.addColorStop(0,'#fff0d233');g.addColorStop(.55,'#fff0d200');g.addColorStop(.72,'#fff0d2df');g.addColorStop(.85,'#fff0d2');c.fillStyle=g;c.fillRect(0,0,W,H);paper=true}
''')
s=s.replace("function bg(color=N){rect(0,0,W,H,color)}", "function bg(color=T.bg){rect(0,0,W,H,color);texture()}")
start=s.index('function grid(');end=s.index('function gradient(',start)
s=s[:start]+"function grid(){/* Paper grain replaces the technical grid. */}\n"+s[end:]
start=s.index('function gradient(');end=s.index('function arrow(',start)
s=s[:start]+"function gradient(){const g=c.createLinearGradient(0,1000,0,H);g.addColorStop(0,'#fff0d200');g.addColorStop(.52,'#fff0d2');g.addColorStop(1,'#fff0d2');c.fillStyle=g;c.fillRect(0,1000,W,H-1000)}\n"+s[end:]
s=s.replace('text(title,70,15,27,F,','text(title,70,15,27,inkFor(accent),')
s=s.replace("col===B?'#16389c':col===O?'#bf7543':'#c4bcae'","shadeColor(col)")
s=s.replace("c.strokeStyle='#fff5';c.lineWidth=3", "c.strokeStyle='#40322633';c.lineWidth=3")
s=s.replace("'#a8b3c533'","'#aa948433'").replace("paper?'#4e5a6e':'#adc0d6'","'#6b5d55'")
def function(name,nextname,code):
 global s
 a=s.index('function '+name+'(');b=s.index('function '+nextname+'(',a);s=s[:a]+code+'\n'+s[b:]
function('camera','skin',r'''function camera(t,shot,u){
bg();rect(42,290,996,1050,'#4a2d2526',1);rect(35,281,1010,1060,F,2);c.clearRect(54,300,972,1024);
// Torn paper edges frame the synchronized camera without altering its timing.
c.beginPath();c.moveTo(54,300);for(let x=54;x<=1026;x+=18)c.lineTo(x,300+3*Math.sin(x*.19));c.lineTo(1026,287);c.lineTo(54,287);c.closePath();c.fillStyle=F;c.fill();
tape(37,264,200,58,-.055);tape(852,1292,173,53,.05);
if(t<2.2){rect(70,1090,870,241,T.bg,2);words('EL CAMBIO',88,1115,84,N,u);words('ESTÁ ADENTRO.',88,1210,84,B,u,.2)}
else if(t<11.3){pill('YAGO OYARZABAL',75,1232,B,F,27);rect(75,1296,780,55,T.bg,0);text('Lo que voy aprendiendo con IA',90,1300,35,N,{weight:650})}
else if(t>=15&&t<19.3){rect(75,1205,850,115,F,1);line([[86,1292],[320+515*cl(u/3),1292]],B,7);text('EXPERIENCIA + PRUEBA',90,1220,48,N)}
else if(t>=32.33&&t<35.94){rect(75,1210,850,110,F,1);words('HACERLO FUNCIONAR.',90,1234,56,N,u,.12)}
else if(t>=56.53&&t<59.6){rect(75,1197,850,125,T.bg,0);text('QUE TE SIRVA.',90,1210,80,B,{rotate:-.02})}
else if(t>=62.4){rect(75,1135,850,190,T.bg,0);text('CAMBIAR CÓMO',90,1150,63,N);text('TRABAJAMOS.',90,1225,80,B)}
}''')
function('manual','iterate',r'''function manual(u){bg();warmPhoto(images.manual,u,1.035);
pill('TRABAJO MANUAL',75,300,B,F,29);
const notes=[['BRIEF',135,680,-.09],['GUION',660,920,.06],['VERSIONES',150,1060,-.04]];
notes.forEach(([label,x,y,rot],i)=>{const q=ease((u-.1-i*.16)/.4);c.save();c.globalAlpha=q;c.translate(x,y+60*(1-q));c.rotate(rot);rect(-15,-10,label.length*24+45,67,F,3);text(label,0,0,34,N,{safe:false});c.restore()});
rect(60,1175,895,170,'#fff4dfed',1);text('TODO POR',78,1188,67,N);text('SEPARADO.',78,1260,81,B);
photoNote('Escena ilustrativa creada con IA');
}''')
function('launch','phone',r'''function launch(u){bg();const p=ease((u-.8)/.35);text('PRIMERA',75,1165,89,N);text('VERSIÓN.',75,1260,100,B);
c.save();c.globalAlpha=.38;circle(515,875,345,O);c.restore();
const y=730+25*p;rect(165,y+28,690,290,'#6b4a5666',35);
const metal=c.createLinearGradient(165,y,855,y+290);metal.addColorStop(0,'#fffdf5');metal.addColorStop(.35,'#e0d4c5');metal.addColorStop(.52,'#fffdf4');metal.addColorStop(1,'#c1ada5');rect(165,y,690,290,metal,35,N,3);
text('EMPEZAR',510,y+75,91,N,{align:'center',max:650});arrow(790,y+185,0,B);cursor(720,900+20*p,1.6);pill('ALGO ÚTIL PARA PROBAR',95,340,B,F,29);
}''')
function('orchestrate','unify',r'''function orchestrate(u){bg();warmPhoto(images.flow,u,1.035);text('ASÍ LO',75,295,103,N);text('CONECTAMOS.',75,410,103,B);
const tags=[['IDEA',80,1190],['GUION',385,720],['VIDEO',755,1160]];
tags.forEach(([label,x,y],i)=>{const q=ease((u-.2-i*.18)/.4);c.save();c.globalAlpha=q;const w=label.length*24+38;rect(x,y+50*(1-q),w,67,F,8);text(label,x+18,y+10+50*(1-q),30,N,{safe:q>.98});c.restore()});
const p=ease((u-1)/.5);c.save();c.globalAlpha=p;pill('VOS REVISÁS ✓',335,1290,B,F,28);c.restore();photoNote('Agente de marketing · metáfora visual creada con IA');
}''')
function('timeScene','outro',r'''function timeScene(u){bg();warmPhoto(images.time,u,1.15);text('EL OBJETIVO:',75,310,53,N,{weight:750});rect(60,1180,900,177,'#fff4dfeb',1);text('RECUPERAR',78,1192,75,N);text('TIEMPO.',78,1278,85,B);photoNote('Metáfora visual creada con IA; sin ahorro medido');}''')
start=s.index('function outro(');end=s.index('const funcs=',start)
s=s[:start]+r'''function outro(u){bg();const p=ease(u/1.1);c.save();c.globalAlpha=.55;c.translate(540,850);c.rotate(-.13+u*.08);for(let i=0;i<4;i++)rect(-420+i*35,-450+i*70,840,850,null,10,O,12);c.restore();
text('CAMBIAR',75,575,132,N);text('CÓMO',75,725,132,B);text('TRABAJAMOS.',75,875,114,N,{max:850});progressLine(75,1115,850,p,B);text('@yago.oyarzabal',75,1200,46,N,{weight:750});}

'''+s[end:]
# Each scene receives a deliberate light palette; blue is not replaced by one other dominant color.
for a,b in [
 ('function skin(u,t){bg(F);paper=true;','function skin(u,t){bg();paper=true;'),
 ('function system(u){bg(N);grid();','function system(u){bg();grid();'),
 ("text('REDISEÑAR',75,295,60,O);text('EL SISTEMA.',75,385,116,F)","text('REDISEÑAR',75,295,60,B);text('EL SISTEMA.',75,385,116,N)"),
 ('function iterate(u,t){bg(F);paper=true;','function iterate(u,t){bg();paper=true;'),
 ("function layers(u){bg(N);grid('#8ca9d215');text('LA BASE',75,300,103,F);text('DEL SISTEMA.',75,415,103,O);","function layers(u){bg();text('LA BASE',75,300,103,N);text('DEL SISTEMA.',75,415,103,B);"),
 ('function brief(u){bg(B);','function brief(u){bg();'),
 ("text('UNA IDEA.',75,325,136,F)","text('UNA IDEA.',75,325,136,N)"),
 ('function context(u){bg(O);paper=true;','function context(u){bg();paper=true;'),
 ("function phone(u){bg(N);grid('#8ca9d213');title2('DEL GUION','AL VIDEO.',280,102);","function phone(u){bg();title2('DEL GUION','AL VIDEO.',280,102,N);"),
 ('rect(284,555,472,823,B,52)','rect(284,555,472,823,N,52)'),
 ('rgba(9,19,38,${1-p})','rgba(41,33,35,${1-p})'),
 ('function unify(u){bg(F);paper=true;','function unify(u){bg();paper=true;'),
 ("'#314b70'","'#7b886c'"),("'#dae1ec'","'#eadbc5'"),("'#d5dcea'","'#e4d1bc'"),("'#e1e6ef'","'#ece4d6'"),("'#dce3ef'","'#dac9da'")]:s=s.replace(a,b)
# The cached outgoing scene must keep its own palette when composed over the incoming one.
s=s.replace('const oldC=c,oldBoxes=boxes,oldPaper=paper;', 'const oldC=c,oldBoxes=boxes,oldPaper=paper,oldTheme=T;')
s=s.replace('const prev=P.shots[index-1];','const prev=P.shots[index-1];useTheme(themeFor(prev));')
s=s.replace('bg(B);c.save();c.globalAlpha=.19;', 'bg();c.save();c.globalAlpha=.35;')
s=s.replace('c=oldC;boxes=oldBoxes;paper=oldPaper;transitionCache', 'c=oldC;boxes=oldBoxes;useTheme(oldTheme);paper=oldPaper;transitionCache')
s=s.replace("u=t-s.start;\nif(s.view", "u=t-s.start;useTheme(themeFor(s));\nif(s.view")
s=s.replace("text('∞',74,157,38,O", "text('∞',74,157,38,B")
s=s.replace("paper?'#536078':'#a8bed5'", "'#6b5d55'")
s=s.replace("el.className=paper?'paper':'';el.innerHTML", "el.className=paper?'paper':'';el.style.setProperty('--active',B);el.innerHTML")
s=s.replace("img.decode().then(()=>{MG.onFrame(render);MG.ready()})", "Promise.all(Object.values(images).map(im=>im.decode())).then(()=>{MG.onFrame(render);MG.ready()})")
s=s.replace('color:#111c30','color:#292123').replace('background:#295bff;color:#fff8ed','background:var(--active,#a92e4d);color:#fff8ed')
s=s.replace('background:#ffb46c;color:#091326','background:var(--active,#a92e4d);color:#fff8ed')
s=s.replace('0 3px 0 #071020,0 5px 14px #07102099','0 3px 0 #292123,0 5px 14px #29212399')
(BASE/'escena_v6.html').write_text(s,encoding='utf-8')
# Reuse the complete timing/geometry review against the new composition.
qa=(BASE/'revisar_v5.mjs').read_text(encoding='utf-8').replace('construccion-v5','construccion-v6').replace('escena_v5.html','escena_v6.html')
(BASE/'revisar_v6.mjs').write_text(qa,encoding='utf-8')
print('V6 theme, camera frame, texture, illustrations and review script written.')
