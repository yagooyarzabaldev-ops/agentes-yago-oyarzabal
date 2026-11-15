// V9: alternate split-screen camera and full-screen visuals; camera appears half the narration.
let skipStage9=false;
function cameraVisible9(t){return P.camera_ranges.some(([a,b])=>t>=a&&t<b)}
function stage(s,u){if(!skipStage9)stageBase8(s,u)}
function photo(s,u){const im=images[s.view],p=cl(u/(s.end-s.start)),q=p*p*(3-2*p),dir=s.direction||1;
 let z=1.18,x=0,y=0,a=0;
 if(s.motion==='push'){z=lerp(1.16,1.38,q);x=dir*lerp(45,-30,q);y=lerp(22,-20,q)}
 else if(s.motion==='pull'){z=lerp(1.40,1.16,q);x=dir*lerp(-35,30,q);a=dir*lerp(-.018,.012,q)}
 else if(s.motion==='truck'){z=1.25+.035*Math.sin(p*Math.PI);x=dir*lerp(-94,94,q);y=15*Math.sin(p*Math.PI);a=dir*.018}
 else if(s.motion==='orbit'){z=lerp(1.25,1.34,q);x=dir*56*Math.sin(p*Math.PI);y=32*Math.cos(p*Math.PI);a=dir*lerp(-.035,.035,q)}
 else{z=lerp(1.24,1.29,q);x=dir*20*Math.sin(p*Math.PI);y=lerp(70,-60,q);a=dir*lerp(.018,-.015,q)}
 const focus={neural:.48,chip_ref:.50,studio_ref:.54,hub_ref:.53,flow_ref:.54,tiempo:.50}[s.view]||.5;
 const k=Math.max(W/im.width,HH/im.height)*z;c.save();c.translate(W/2,Y+HH/2);c.rotate(a);c.drawImage(im,-im.width*k/2+x,-im.height*k*(focus+(s.variant%2?-.018:0))+y,im.width*k,im.height*k);c.restore();
 const shade=c.createLinearGradient(0,Y,0,H);shade.addColorStop(0,'#09080ce8');shade.addColorStop(.27,'#09080c05');shade.addColorStop(.68,'#09080c00');shade.addColorStop(1,'#09080cc9');c.fillStyle=shade;c.fillRect(0,Y,W,HH);
 // Separate light layers travel across the lens movement; no simulated character animation.
 c.save();c.globalAlpha=.12;const xx=-270+((u*.31+s.index*.13)%1)*1640;c.translate(xx,1030);c.rotate(-.38);const g=c.createLinearGradient(0,0,130,0);g.addColorStop(0,'#fff0');g.addColorStop(.5,s.accent);g.addColorStop(1,'#fff0');c.fillStyle=g;c.fillRect(0,0,130,1300);c.restore();
 c.save();c.globalAlpha=.5;for(let i=0;i<5;i++){const px=100+((s.index*41+i*193+u*dir*48)%900+900)%900,py=1300+((i*123-u*75)%510+510)%510;glow(px,py,18,s.accent,.32);dot(px,py,1.6,s.accent)}c.restore();
}
function title9(ch,t){if(ch.kind==='outro')return;const full=!cameraVisible9(t),q=ease((t-ch.start)/.28),y=full?310:1030;c.save();c.globalAlpha=q;text(ch.title[0],65,y+14*(1-q),full?91:61,F,850,875);text(ch.title[1],65,y+(full?108:75)+14*(1-q),full?99:69,ch.accent,900,875);c.restore()}
function scene(s,t,withTitle=false){const u=t-s.start;rect(0,Y,W,HH,N);if(s.kind==='image')photo(s,u);else if(funcs[s.kind]){
 if(Y===0){stageBase8(s,u);c.save();c.translate(0,-520);skipStage9=true;funcs[s.kind](s,u*1.35);skipStage9=false;c.restore()}else funcs[s.kind](s,u*1.35)
 }else{stage(s,u);ring(540,Y+HH*.67,330,u*1.4,s.accent)}if(withTitle)title9(P.visual_chapters.find(x=>t>=x.start&&t<x.end)||P.visual_chapters.at(-1),t)}
function prevFrame(i){if(cache.has(i))return cache.get(i);const cv=document.createElement('canvas');cv.width=W;cv.height=H;const old=c,oldBoxes=boxes,oldY=Y,oldHH=HH;c=cv.getContext('2d');boxes=[];const s=P.shots[i-1],t=s.end-.01;Y=cameraVisible9(t)?960:0;HH=H-Y;scene(s,t,false);c=old;boxes=oldBoxes;Y=oldY;HH=oldHH;cache.set(i,cv);return cv}
function transition(tr,t){const p=cl((t-tr.at)/tr.duration),q=p*p*(3-2*p),im=prevFrame(tr.index),dir=tr.direction||1;c.save();c.beginPath();c.rect(0,Y,W,HH);c.clip();
 if(tr.mode==='whip'){c.filter=`blur(${Math.sin(p*Math.PI)*6}px)`;c.drawImage(im,-dir*(W+40)*q,0)}
 else if(tr.mode==='zoom'){c.globalAlpha=1-q;c.translate(540,Y+HH/2);c.scale(1+.72*q,1+.72*q);c.rotate(dir*.055*q);c.filter=`blur(${q*5}px)`;c.drawImage(im,-540,-Y-HH/2)}
 else if(tr.mode==='split'){for(let j=0;j<4;j++){const a=ease((p-j*.035)/.88);c.drawImage(im,j*270,Y,270,HH,j*270,Y+(j%2?1:-1)*(HH+10)*a,270,HH)}}
 else if(tr.mode==='iris'){c.beginPath();c.rect(0,Y,W,HH);c.arc(540,Y+HH/2,(HH>1000?1300:900)*q,0,Math.PI*2,true);c.clip('evenodd');c.drawImage(im,0,0)}
 else if(tr.mode==='lift'){c.translate(540,Y+HH/2);c.rotate(dir*.08*q);c.globalAlpha=1-.25*q;c.drawImage(im,-540,-Y-HH/2-dir*(HH+90)*q)}
 else{c.beginPath();c.moveTo(W*q,Y);c.lineTo(W,Y);c.lineTo(W,H);c.lineTo(-500+1600*q,H);c.closePath();c.clip();c.drawImage(im,0,0)}c.restore();
}
function render(t){t+=P.render_offset||0;c.setTransform(1,0,0,1,0,0);c.globalAlpha=1;c.clearRect(0,0,W,H);boxes=[];const visible=cameraVisible9(t);Y=visible?960:0;HH=H-Y;const s=P.shots.find(s=>t>=s.start&&t<s.end)||P.shots.at(-1),ch=P.visual_chapters.find(x=>t>=x.start&&t<x.end)||P.visual_chapters.at(-1);
 c.save();c.beginPath();c.rect(0,Y,W,HH);c.clip();scene(s,t,false);for(const tr of P.transitions)if(t>=tr.at&&t<tr.at+tr.duration)transition(tr,t);title9(ch,t);c.restore();
 const capY=visible?833:1415,fadeY=visible?745:1330;const g=c.createLinearGradient(0,fadeY,0,fadeY+290);g.addColorStop(0,'#0000');g.addColorStop(.60,'#07070bdd');g.addColorStop(1,'#07070b00');c.fillStyle=g;c.fillRect(0,fadeY,W,290);
 const h=c.createLinearGradient(0,0,0,220);h.addColorStop(0,'#0009');h.addColorStop(1,'#0000');c.fillStyle=h;c.fillRect(0,0,W,220);
 text('∞  INFINITE PROCESS',65,126,27,F,750,800,false);if(visible)line([[0,960],[1080,960]],ch.accent+'70',2);text('@yago.oyarzabal',65,1785,28,F,650,600,false);
 if(t>7.6&&t<10.5){c.save();c.globalAlpha=Math.min(ease((t-7.6)/.3),ease((10.5-t)/.3));text('YAGO OYARZABAL',65,742,31,F,800,800,false);c.restore()}
 const cap=P.captions.find(a=>t>=a[0].start-.025&&t<=a.at(-1).end+.025),el=document.getElementById('captions');el.style.top=capY+'px';el.style.setProperty('--accent',ch.accent);el.innerHTML=cap?'<div>'+cap.map(w=>`<span class="${t>=w.start&&t<w.end?'on':''}">${MG.esc(w.w)}</span>`).join(' ')+'</div>':'';
 if(s.kind==='outro'){const u=t-s.start,p=cl(u/(s.end-s.start)),q=ease(u/.3);c.save();c.globalAlpha=q;rect(0,0,W,H,'#090a11');glow(180+720*p,1450-530*p,900,'#9b487f',.68);glow(1000-800*p,210+420*p,680,s.accent,.32);c.save();c.globalAlpha=.26;ring(970,1430,440,u*1.8,s.accent);ring(80,320,310,-u*1.4,'#be8aff');c.restore();const dy=-40*p; text('CAMBIAR CÓMO',65,730+dy,82,F,900,875);text('TRABAJAMOS.',65,840+dy,98,s.accent,900,875);line([[65,990+dy],[65+875*ease(u/1.3),990+dy]],s.accent,5);text('@yago.oyarzabal',65,1080+dy,36,F,700);c.restore()}
 window.__drawBoxes=boxes;window.__view=s.view;window.__cameraVisible=visible;
}
