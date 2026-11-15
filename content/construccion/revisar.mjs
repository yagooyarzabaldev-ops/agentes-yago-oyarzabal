import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const v2=process.argv.includes('--v2'),v3=process.argv.includes('--v3');
const d=path.join(root,'runtime/construccion-'+(v3?'v3':v2?'v2':'v1'));
const p=JSON.parse(fs.readFileSync(path.join(d,'params.json'),'utf8'));
const {chromium}=createRequire('D:/Antigravity/Infinite Process/contenido/build/cine3d_reels/web_deps/package.json')('playwright-core');
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
try{
 const page=await browser.newPage({viewport:{width:1080,height:1920}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(pathToFileURL(path.join(root,'content/construccion/'+(v3?'escena_v3.html':v2?'escena_v2.html':'escena.html'))).href+'#p='+encodeURIComponent(JSON.stringify(p)));
 await page.waitForFunction(()=>window.__mgReady);
 const textIssues=[];
 // Check each subtitle at its midpoint, plus all chapter endings after every reveal.
 const times=[...p.captions.map(c=>(c[0].start+c.at(-1).end)/2),...p.paragraphs.map(x=>x.end-.12)];
 for(const t of times){
  await page.evaluate(t=>MG.seek(t),t);
  const issues=await page.evaluate(()=>{
   const bad=[];
   for(const el of document.querySelectorAll('h1,.chapter,.label,.big,.small,.pill,.tag,.code,.type,.sticker,#subs,#subtitles,#captions,.footer')){
    if(!el.getClientRects().length)continue;
    if(Number(getComputedStyle(el).opacity)<.5)continue;
    const r=el.getBoundingClientRect();
    if(el.scrollWidth>el.clientWidth+3)bad.push({text:el.textContent.trim().slice(0,85),reason:'horizontal overflow'});
    if(r.right>965||r.left<55)bad.push({text:el.textContent.trim().slice(0,85),reason:'horizontal safe area',left:r.left,right:r.right});
    if(['subs','subtitles','captions'].includes(el.id)&&el.textContent.trim()){
     const cr=el.firstElementChild.getBoundingClientRect();
     if(cr.height>145||cr.bottom>1570)bad.push({text:el.textContent.trim(),reason:'caption height',height:cr.height,bottom:cr.bottom});
    }
   }
   return bad;
  });
  textIssues.push(...issues.map(x=>({time:t,...x})));
 }
 const report={ok:!errors.length&&!textIssues.length,samples:times.length,chapters:p.paragraphs.length,captions:p.captions.length,errors,textIssues};
 fs.writeFileSync(path.join(d,'revision-layout.json'),JSON.stringify(report,null,2));
 console.log(JSON.stringify(report));
 if(!report.ok)process.exitCode=1;
}finally{await browser.close();}
