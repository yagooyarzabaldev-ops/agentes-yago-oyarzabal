import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..'),d=path.join(root,'runtime/construccion-v4');
const p=JSON.parse(fs.readFileSync(path.join(d,'params.json'),'utf8'));
const {chromium}=createRequire('D:/Antigravity/Infinite Process/contenido/build/cine3d_reels/web_deps/package.json')('playwright-core');
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
fs.mkdirSync(path.join(d,'revision'),{recursive:true});
try{
 const page=await browser.newPage({viewport:{width:1080,height:1920}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto(pathToFileURL(path.join(root,'content/construccion/escena_v4.html')).href+'#p='+encodeURIComponent(JSON.stringify(p)));
 await page.waitForFunction(()=>window.__mgReady);
 await page.evaluate(()=>Promise.all([...document.images].map(x=>x.decode())));
 const textIssues=[],times=[...p.captions.map(c=>(c[0].start+c.at(-1).end)/2),...p.shots.map(s=>(s.start+s.end)/2)];
 for(const t of times){
  await page.evaluate(t=>MG.seek(t),t);
  const issues=await page.evaluate(()=>{
   const bad=[];
   for(const el of document.querySelectorAll('.type,.tag,.under,.eyebrow,#captions')){
    if(!el.getClientRects().length||Number(getComputedStyle(el).opacity)<.5)continue;
    const r=el.getBoundingClientRect();
    if(el.scrollWidth>el.clientWidth+3)bad.push({text:el.textContent.trim().slice(0,85),reason:'horizontal overflow'});
    if(r.right>965||r.left<55)bad.push({text:el.textContent.trim().slice(0,85),reason:'horizontal safe area',left:r.left,right:r.right});
    if(el.id==='captions'&&el.textContent.trim()){
     const cr=el.firstElementChild.getBoundingClientRect();
     if(cr.height>145||cr.bottom>1570)bad.push({text:el.textContent.trim(),reason:'caption height',height:cr.height,bottom:cr.bottom});
    }
   }
   return bad;
  });
  textIssues.push(...issues.map(x=>({time:t,...x})));
 }
 for(let i=0;i<p.shots.length;i++){
  const s=p.shots[i];if(s.view==='camera')continue;
  await page.evaluate(t=>MG.seek(t),(s.start+s.end)/2);
  await page.screenshot({path:path.join(d,'revision',`${String(i).padStart(2,'0')}-${s.view}.png`)});
 }
 const report={ok:!errors.length&&!textIssues.length,samples:times.length,visual_scenes:p.shots.filter(s=>s.view!=='camera').length,captions:p.captions.length,errors,textIssues};
 fs.writeFileSync(path.join(d,'revision-layout.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 if(!report.ok)process.exitCode=1;
}finally{await browser.close();}
