import fs from 'node:fs';import path from 'node:path';import{createRequire}from'node:module';import{fileURLToPath,pathToFileURL}from'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..'),d=path.join(root,'runtime/construccion-v9'),P=JSON.parse(fs.readFileSync(path.join(d,'params.json'),'utf8'));
const{chromium}=createRequire('D:/Antigravity/Infinite Process/contenido/build/cine3d_reels/web_deps/package.json')('playwright-core');
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});fs.mkdirSync(path.join(d,'revision'),{recursive:true});
try{const page=await browser.newPage({viewport:{width:1080,height:1920}}),errors=[],issues=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto(pathToFileURL(path.join(root,'content/construccion/escena_v9.html')).href+'#p='+encodeURIComponent(JSON.stringify(P)));await page.waitForFunction(()=>window.__mgReady);
const samples=[...P.captions.map(c=>(c[0].start+c.at(-1).end)/2),...P.shots.flatMap(s=>[s.start+.25,(s.start+s.end)/2,s.end-.05]),...P.transitions.map(tr=>tr.at+tr.duration*.5)];
for(const t of samples){await page.evaluate(t=>MG.seek(t),t);const bad=await page.evaluate(()=>{const arr=[];for(const b of window.__drawBoxes||[]){if(b.x<60||b.x+b.w>965)arr.push({...b,reason:'horizontal safe bounds'});}
const el=document.getElementById('captions');if(el.textContent.trim()){const r=el.firstElementChild.getBoundingClientRect();if(r.height>150||r.bottom>(window.__cameraVisible?984:1566)||r.left<60||r.right>945)arr.push({text:el.textContent,reason:'caption bounds',rect:{left:r.left,right:r.right,bottom:r.bottom,height:r.height}})}
return arr});issues.push(...bad.map(x=>({time:t,...x})))}
for(let i=0;i<P.shots.length;i++){const s=P.shots[i];await page.evaluate(t=>MG.seek(t),(s.start+s.end)/2);await page.screenshot({path:path.join(d,'revision',`${String(i).padStart(2,'0')}-${s.view}.png`),omitBackground:true})}
for(const [label,start,end] of [['movimiento',.3,1.9],['barrido',2,2.32],['zoom',4.5,4.80],['bandas',7.333,7.70]]){for(let i=0;i<5;i++){const t=start+(end-start)*i/4;await page.evaluate(t=>MG.seek(t),t);await page.screenshot({path:path.join(d,'revision',`${label}-${i}.png`),omitBackground:true})}}
const report={ok:!errors.length&&!issues.length,samples:samples.length,errors,textIssues:issues};fs.writeFileSync(path.join(d,'revision-layout.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));if(!report.ok)process.exitCode=1;
}finally{await browser.close()}
