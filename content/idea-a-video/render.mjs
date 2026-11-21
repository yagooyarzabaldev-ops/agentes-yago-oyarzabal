import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {spawn} from 'node:child_process';
const version=process.argv.includes('--v3')?3:process.argv.includes('--v2')?2:1,v2=version>=2;
const dir=path.dirname(fileURLToPath(import.meta.url)),root=path.resolve(dir,'../..'),work=path.join(root,`runtime/idea-a-video-v${version}`);
const params=JSON.parse(fs.readFileSync(path.join(dir,v2?`params-v${version}.json`:'params.json'),'utf8'));
const {chromium}=createRequire(process.env.PLAYWRIGHT_MODULE||'D:/Antigravity/Infinite Process/contenido/build/cine3d_reels/web_deps/package.json')('playwright-core');
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--force-color-profile=srgb','--font-render-hinting=none']});
fs.mkdirSync(work,{recursive:true});const errors=[];
async function page(){const p=await browser.newPage({viewport:{width:1080,height:1920}});p.on('pageerror',e=>errors.push(e.message));await p.goto(pathToFileURL(path.join(dir,v2?'escena-v2.html':'escena.html')).href+'#p='+encodeURIComponent(JSON.stringify(params)));await p.waitForFunction(()=>window.__mgReady,null,{timeout:30000});return p}
try{
 const p=await page();
 if(process.argv.includes('--review')){
  const out=path.join(work,'review');fs.mkdirSync(out,{recursive:true});const issues=[];
  const times=[...params.shots.flatMap(s=>[s.start+.4,s.start+1,s.end-.08]),...params.captions.map(a=>(a[0].start+a.at(-1).end)/2)];
  for(const t of times){await p.evaluate(t=>MG.seek(t),t);const bad=await p.evaluate(()=>{const boxes=(window.__drawBoxes||[]).filter(b=>b.x<50||b.x+b.w>1000||b.y+b.h>1730);const el=document.getElementById('captions');if(el.textContent.trim()){const r=el.firstElementChild.getBoundingClientRect();if(r.height>210||r.right>970||r.left<60||r.bottom>1715)boxes.push({text:el.textContent,caption:true,rect:{h:r.height,b:r.bottom,l:r.left,r:r.right}})}return boxes});issues.push(...bad.map(x=>({t,...x})))}
  const imageSamples=[];
  for(const s of params.shots){await p.evaluate(t=>MG.seek(t),s.start+1);await p.screenshot({path:path.join(out,`${String(s.index).padStart(2,'0')}-${s.view}.jpg`),type:'jpeg',quality:85});if(v2)imageSamples.push({scene:s.index,image_id:await p.evaluate(()=>window.__imageId)})}
  const distinctImages=new Set(imageSamples.map(s=>s.image_id).filter(Boolean)).size;if(v2&&distinctImages<10)issues.push({minimum_images:10,observed_ids:distinctImages});
  const report={ok:!issues.length&&!errors.length,samples:times.length,scenes:params.shots.length,errors,issues,...(v2?{distinct_images:distinctImages,image_samples:imageSamples}:{}),scope:'visual preview; no recorded voice or camera yet'};fs.writeFileSync(path.join(work,'review.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));if(!report.ok)process.exitCode=1;
 }else{
  const output=path.join(work,'imagen.mp4'),fps=30,total=Math.round(params.duration*fps);
  const ff=spawn('ffmpeg',['-hide_banner','-loglevel','error','-f','image2pipe','-framerate',String(fps),'-c:v','mjpeg','-i','-','-an','-vf','scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','20','-threads','3','-pix_fmt','yuv420p','-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-movflags','+faststart','-y',output],{stdio:['pipe','inherit','inherit']});
  const done=new Promise((res,rej)=>{ff.on('close',code=>code===0?res():rej(new Error('ffmpeg '+code)));ff.on('error',rej)});
  const pages=[p,await page(),await page()];let next=0,written=0,wake=null;const ready=new Map();
  async function writer(){while(written<total){if(!ready.has(written)){await new Promise(r=>wake=r);continue}const buf=ready.get(written);ready.delete(written);if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));written++;if(written%150===0)console.log(JSON.stringify({frames:written,total}))}}
  async function worker(p){const cdp=await p.context().newCDPSession(p);while(true){while(next-written>12)await new Promise(r=>setTimeout(r,5));const i=next++;if(i>=total)return;await p.evaluate(t=>MG.seek(t),i/fps);const shot=await cdp.send('Page.captureScreenshot',{format:'jpeg',quality:90,optimizeForSpeed:true,fromSurface:true});ready.set(i,Buffer.from(shot.data,'base64'));if(wake){const w=wake;wake=null;w()}}}
  await Promise.all([writer(),...pages.map(worker)]);ff.stdin.end();await done;if(errors.length)throw new Error(errors.join('\n'));console.log(JSON.stringify({output,duration:params.duration,frames:total,bytes:fs.statSync(output).size}));
 }
}finally{await browser.close()}
