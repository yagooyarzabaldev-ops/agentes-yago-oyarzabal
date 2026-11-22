import {readFile,readdir,mkdir,writeFile} from 'node:fs/promises';
import {resolve,join,extname} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=resolve(fileURLToPath(new URL('..',import.meta.url)));
const assets={};
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml'};
async function collect(dir,prefix='') {for(const entry of await readdir(dir,{withFileTypes:true})){if(entry.name==='server'||entry.name.startsWith('.'))continue;const key=prefix+'/'+entry.name,file=join(dir,entry.name);if(entry.isDirectory())await collect(file,key);else assets[key]={body:await readFile(file,'utf8'),type:types[extname(file)]||'text/plain; charset=utf-8'};}}
await collect(join(root,'dist'));
const source=await readFile(join(root,'worker/index.mjs'),'utf8');
const output=source.replace('/*__ASSET_MAP__*/ {}',JSON.stringify(assets));
if(output===source)throw new Error('Missing asset marker');
await mkdir(join(root,'dist/server'),{recursive:true});
await writeFile(join(root,'dist/server/index.js'),output);
console.log(`Worker built: ${Object.keys(assets).length} assets, ${Buffer.byteLength(output)} bytes.`);
